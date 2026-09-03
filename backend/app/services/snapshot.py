from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.database.models import (
    Vehicle, VehicleTelemetry, Component, Failure, PartUsage,
    MaintenancePlan, Part, InventoryLedger, PurchaseOrder, MaintenanceTemplate
)
from datetime import datetime, timedelta

def parse_date(date_str: str) -> datetime.date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def add_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return (dt + timedelta(days=days)).strftime("%Y-%m-%d")

def get_feature_snapshot(db: Session, prediction_timestamp: str) -> dict:
    """
    Generates a historical snapshot of the fleet status as of prediction_timestamp (YYYY-MM-DD).
    Ensures zero temporal leakage by filtering out all events and telemetry after prediction_timestamp.
    """
    snapshot = {}

    # 1. Reconstruct Vehicles with hours as of prediction_timestamp
    vehicles_data = []
    vehicles = db.query(Vehicle).all()
    for v in vehicles:
        # Find latest telemetry on or before prediction_timestamp
        telemetry = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == v.id, VehicleTelemetry.date <= prediction_timestamp)\
            .order_by(VehicleTelemetry.date.desc())\
            .first()
        
        hours = telemetry.operating_hours if telemetry else 0.0
        
        # Determine status at T. If down due to unresolved failure at T, status = DOWN.
        # Find if there are any failures on or before T where resolved = False or resolution date > T
        # (resolution date is the date of part usage associated with the failure)
        unresolved_failure = db.query(Failure)\
            .filter(
                Failure.vehicle_id == v.id,
                Failure.failure_date <= prediction_timestamp,
                Failure.resolved == False
            ).first()
            
        # Also check if any resolved failure has a resolution usage date > prediction_timestamp
        if not unresolved_failure:
            unresolved_failure = db.query(Failure).join(PartUsage, Failure.id == PartUsage.failure_id)\
                .filter(
                    Failure.vehicle_id == v.id,
                    Failure.failure_date <= prediction_timestamp,
                    PartUsage.usage_date > prediction_timestamp
                ).first()
                
        status = 'DOWN' if unresolved_failure else 'ACTIVE'
        
        vehicles_data.append({
            "id": v.id,
            "name": v.name,
            "model": v.model,
            "age_years": v.age_years,
            "operating_hours": hours,
            "status": status
        })
    snapshot["vehicles"] = vehicles_data

    # 2. Reconstruct Components active at prediction_timestamp with correct hours
    components_data = []
    for v in vehicles_data:
        v_id = v["id"]
        v_hours = v["operating_hours"]
        
        # Query all components installed on or before prediction_timestamp
        comps = db.query(Component)\
            .filter(Component.vehicle_id == v_id, Component.installed_date <= prediction_timestamp)\
            .all()
            
        # Group by type and select the most recently installed component of each type
        active_comps = {}
        for c in comps:
            if c.type not in active_comps or c.installed_date > active_comps[c.type].installed_date:
                active_comps[c.type] = c
                
        for c_type, c in active_comps.items():
            # Comp hours at T is: vehicle_hours_at_T - vehicle_hours_at_install
            comp_hours = max(0.0, v_hours - c.operating_hours_at_install)
            
            components_data.append({
                "id": c.id,
                "vehicle_id": c.vehicle_id,
                "type": c.type,
                "installed_date": c.installed_date,
                "operating_hours_at_install": c.operating_hours_at_install,
                "current_hours": comp_hours
            })
    snapshot["components"] = components_data

    # 3. Filter Failures
    failures = db.query(Failure).filter(Failure.failure_date <= prediction_timestamp).all()
    snapshot["failures"] = [
        {
            "id": f.id,
            "vehicle_id": f.vehicle_id,
            "component_id": f.component_id,
            "part_id": f.part_id,
            "failure_date": f.failure_date,
            "operating_hours": f.operating_hours,
            "downtime_hours": f.downtime_hours,
            "severity": f.severity,
            "resolved": f.resolved if db.query(PartUsage).filter(PartUsage.failure_id == f.id, PartUsage.usage_date <= prediction_timestamp).first() is not None else False,
            "scenario_id": f.scenario_id
        }
        for f in failures
    ]

    # 4. Filter Part Usage
    usage = db.query(PartUsage).filter(PartUsage.usage_date <= prediction_timestamp).all()
    snapshot["part_usage"] = [
        {
            "id": u.id,
            "vehicle_id": u.vehicle_id,
            "part_id": u.part_id,
            "maintenance_plan_id": u.maintenance_plan_id,
            "failure_id": u.failure_id,
            "quantity": u.quantity,
            "usage_date": u.usage_date
        }
        for u in usage
    ]

    # 5. Reconstruct Maintenance Plans as of prediction_timestamp
    # If a plan is completed after prediction_timestamp, it must be presented as PENDING at prediction_timestamp.
    plans = db.query(MaintenancePlan)\
        .filter(
            (MaintenancePlan.scheduled_date <= prediction_timestamp) | 
            (MaintenancePlan.original_scheduled_date <= prediction_timestamp) |
            (MaintenancePlan.status == 'PENDING')
        ).all()
        
    plans_data = []
    for p in plans:
        # Check if completed on or before prediction_timestamp
        usage_records = db.query(PartUsage).filter(PartUsage.maintenance_plan_id == p.id).all()
        is_completed_before_T = len(usage_records) > 0 and all(u.usage_date <= prediction_timestamp for u in usage_records)
        
        status = 'COMPLETED' if is_completed_before_T else 'PENDING'
        
        # If rescheduled after T, show original schedule at T
        # We assume reschedule timestamp is stored. If rescheduled_timestamp > T, revert scheduled_date to original.
        scheduled_date = p.scheduled_date
        if p.original_scheduled_date and p.rescheduled_timestamp and p.rescheduled_timestamp > prediction_timestamp:
            scheduled_date = p.original_scheduled_date
            status = 'PENDING'
            
        plans_data.append({
            "id": p.id,
            "vehicle_id": p.vehicle_id,
            "component_id": p.component_id,
            "description": p.description,
            "scheduled_date": scheduled_date,
            "scheduled_hours": p.scheduled_hours,
            "original_scheduled_date": p.original_scheduled_date,
            "status": status
        })
    snapshot["maintenance_plans"] = plans_data

    # 6. Reconstruct Inventory levels as of prediction_timestamp
    parts = db.query(Part).all()
    inventory_data = []
    
    for p in parts:
        # Sum ledger entries <= prediction_timestamp
        stock_on_hand = db.query(func.sum(InventoryLedger.quantity))\
            .filter(InventoryLedger.part_id == p.id, InventoryLedger.date <= prediction_timestamp)\
            .scalar() or 0
            
        # Sum active orders: ordered <= prediction_timestamp, but arrived > prediction_timestamp (or not yet)
        stock_on_order = db.query(func.sum(PurchaseOrder.quantity))\
            .filter(
                PurchaseOrder.part_id == p.id,
                PurchaseOrder.order_date <= prediction_timestamp,
                (PurchaseOrder.actual_delivery_date > prediction_timestamp) | (PurchaseOrder.actual_delivery_date == None)
            ).scalar() or 0
            
        # Sum allocated: pending maintenance plans scheduled in [T, T + 3 days]
        three_days_later = add_days(prediction_timestamp, 3)
        allocated = 0
        
        pending_plans_near_T = [
            pl for pl in plans_data 
            if pl["status"] == 'PENDING' and prediction_timestamp <= pl["scheduled_date"] <= three_days_later
        ]
        
        for pl in pending_plans_near_T:
            # Query template parts for this plan's component and description
            comp_type = db.query(Component.type).filter(Component.id == pl["component_id"]).scalar()
            if comp_type:
                tmpl = db.query(MaintenanceTemplate)\
                    .filter(
                        MaintenanceTemplate.maintenance_type == pl["description"],
                        MaintenanceTemplate.component_type == comp_type,
                        MaintenanceTemplate.part_id == p.id
                    ).first()
                if tmpl:
                    allocated += tmpl.quantity
                    
        inventory_data.append({
            "part_id": p.id,
            "part_name": p.name,
            "part_number": p.part_number,
            "stock_on_hand": max(0, stock_on_hand),
            "stock_on_order": stock_on_order,
            "stock_allocated": allocated,
            "min_stock_level": p.min_stock_level,
            "min_order_qty": p.min_order_qty,
            "lead_time_days": p.lead_time_days
        })
        
    snapshot["inventory"] = inventory_data

    return snapshot
