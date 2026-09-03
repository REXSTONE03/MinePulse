import argparse
import random
import numpy as np
import json
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

# Add project root to python path to allow importing backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal, init_db, DEFAULT_DB_PATH, engine
from backend.app.database.models import (
    Base, Vehicle, VehicleTelemetry, Component, Supplier, Part,
    Inventory, InventoryLedger, MaintenanceTemplate, MaintenancePlan,
    Failure, PartUsage, PurchaseOrder, ModelGovernance
)

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Generate synthetic causal mining data for MinePulse AI.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    return parser

def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    
    # 1. Set seed
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    print(f"Initializing database at: {DEFAULT_DB_PATH}")
    # Initialize / clean database
    if os.path.exists(DEFAULT_DB_PATH):
        try:
            os.remove(DEFAULT_DB_PATH)
            # Remove WAL files if they exist
            for ext in ['-wal', '-shm']:
                if os.path.exists(DEFAULT_DB_PATH + ext):
                    os.remove(DEFAULT_DB_PATH + ext)
        except Exception as e:
            print(f"Error removing existing database: {e}")
            
    init_db()
    
    db = SessionLocal()
    try:
        generate_data(db, args.seed)
        db.commit()
        print("Data generation completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during data generation: {e}")
        raise e
    finally:
        db.close()

def generate_data(db: Session, seed: int):
    # Reset seeds inside function to ensure reproducibility across separate test invocations
    random.seed(seed)
    np.random.seed(seed)
    # 2. Insert Suppliers
    suppliers_dict = [
        {"name": "Apex Engine Solutions", "base_lead_time_days": 10, "reliability_rate": 0.95},
        {"name": "Titan Powertrain Parts", "base_lead_time_days": 14, "reliability_rate": 0.90},
        {"name": "HydraForce Hydraulics", "base_lead_time_days": 7, "reliability_rate": 0.88},
        {"name": "Heavy Undercarriage Ltd", "base_lead_time_days": 21, "reliability_rate": 0.92}
    ]
    
    suppliers = []
    for s in suppliers_dict:
        sup = Supplier(**s)
        db.add(sup)
        suppliers.append(sup)
    db.flush()
    
    # 3. Insert Parts Catalog (31 parts total)
    parts_dict = [
        # Engine parts (Supplier 0)
        {"name": "Engine Cylinder Ring", "part_number": "P-ENG-101", "unit_cost": 150.0, "supplier_idx": 0, "min_order_qty": 10, "min_stock_level": 15, "lead_time_days": 10},
        {"name": "Crankshaft Bearing", "part_number": "P-ENG-102", "unit_cost": 320.0, "supplier_idx": 0, "min_order_qty": 5, "min_stock_level": 8, "lead_time_days": 10},
        {"name": "Cylinder Head Gasket", "part_number": "P-ENG-103", "unit_cost": 85.0, "supplier_idx": 0, "min_order_qty": 12, "min_stock_level": 20, "lead_time_days": 10},
        {"name": "Engine Oil Filter", "part_number": "P-ENG-104", "unit_cost": 45.0, "supplier_idx": 0, "min_order_qty": 20, "min_stock_level": 30, "lead_time_days": 10},
        {"name": "Radiator Hose", "part_number": "P-ENG-105", "unit_cost": 60.0, "supplier_idx": 0, "min_order_qty": 15, "min_stock_level": 15, "lead_time_days": 10},
        {"name": "Thermostat Valve", "part_number": "P-ENG-106", "unit_cost": 110.0, "supplier_idx": 0, "min_order_qty": 8, "min_stock_level": 10, "lead_time_days": 10},
        {"name": "Fuel Injector Nozzle", "part_number": "P-ENG-107", "unit_cost": 210.0, "supplier_idx": 0, "min_order_qty": 6, "min_stock_level": 12, "lead_time_days": 10},
        {"name": "Exhaust Valve Gasket", "part_number": "P-ENG-108", "unit_cost": 95.0, "supplier_idx": 0, "min_order_qty": 10, "min_stock_level": 15, "lead_time_days": 10},
        
        # Transmission parts (Supplier 1)
        {"name": "Transmission Clutch Plate", "part_number": "P-TRN-201", "unit_cost": 450.0, "supplier_idx": 1, "min_order_qty": 4, "min_stock_level": 6, "lead_time_days": 14},
        {"name": "Gearbox Shaft Bearing", "part_number": "P-TRN-202", "unit_cost": 280.0, "supplier_idx": 1, "min_order_qty": 6, "min_stock_level": 8, "lead_time_days": 14},
        {"name": "Torque Converter Seal", "part_number": "P-TRN-203", "unit_cost": 75.0, "supplier_idx": 1, "min_order_qty": 15, "min_stock_level": 25, "lead_time_days": 14},
        {"name": "Transmission Oil Filter", "part_number": "P-TRN-204", "unit_cost": 50.0, "supplier_idx": 1, "min_order_qty": 20, "min_stock_level": 30, "lead_time_days": 14},
        {"name": "Control Valve Solenoid", "part_number": "P-TRN-205", "unit_cost": 180.0, "supplier_idx": 1, "min_order_qty": 8, "min_stock_level": 10, "lead_time_days": 14},
        {"name": "Drive Shaft Gasket", "part_number": "P-TRN-206", "unit_cost": 65.0, "supplier_idx": 1, "min_order_qty": 12, "min_stock_level": 18, "lead_time_days": 14},
        
        # Hydraulics parts (Supplier 2)
        {"name": "Hydraulic Cylinder Seal Kit", "part_number": "P-HYD-301", "unit_cost": 130.0, "supplier_idx": 2, "min_order_qty": 10, "min_stock_level": 15, "lead_time_days": 7},
        {"name": "High Pressure Hose", "part_number": "P-HYD-302", "unit_cost": 190.0, "supplier_idx": 2, "min_order_qty": 8, "min_stock_level": 12, "lead_time_days": 7},
        {"name": "Hydraulic Pump Valve", "part_number": "P-HYD-303", "unit_cost": 310.0, "supplier_idx": 2, "min_order_qty": 4, "min_stock_level": 6, "lead_time_days": 7},
        {"name": "Main Hydraulic Filter", "part_number": "P-HYD-304", "unit_cost": 55.0, "supplier_idx": 2, "min_order_qty": 20, "min_stock_level": 35, "lead_time_days": 7},
        {"name": "Hydraulic Accumulator Cap", "part_number": "P-HYD-305", "unit_cost": 90.0, "supplier_idx": 2, "min_order_qty": 10, "min_stock_level": 10, "lead_time_days": 7},
        {"name": "Hydraulic Control Valve Seal", "part_number": "P-HYD-306", "unit_cost": 70.0, "supplier_idx": 2, "min_order_qty": 15, "min_stock_level": 20, "lead_time_days": 7},
        
        # Undercarriage parts (Supplier 3)
        {"name": "Track Roller Bushing", "part_number": "P-UND-401", "unit_cost": 220.0, "supplier_idx": 3, "min_order_qty": 8, "min_stock_level": 10, "lead_time_days": 21},
        {"name": "Sprocket Segment Bolts", "part_number": "P-UND-402", "unit_cost": 15.0, "supplier_idx": 3, "min_order_qty": 50, "min_stock_level": 100, "lead_time_days": 21},
        {"name": "Track Shoe Bolts", "part_number": "P-UND-403", "unit_cost": 10.0, "supplier_idx": 3, "min_order_qty": 100, "min_stock_level": 150, "lead_time_days": 21},
        {"name": "Brake Pad Kit", "part_number": "P-UND-404", "unit_cost": 170.0, "supplier_idx": 3, "min_order_qty": 10, "min_stock_level": 12, "lead_time_days": 21},
        {"name": "Brake Caliper Seal Kit", "part_number": "P-UND-405", "unit_cost": 65.0, "supplier_idx": 3, "min_order_qty": 12, "min_stock_level": 15, "lead_time_days": 21},
        {"name": "Brake Disc Rotor", "part_number": "P-UND-406", "unit_cost": 380.0, "supplier_idx": 3, "min_order_qty": 4, "min_stock_level": 6, "lead_time_days": 21},
        {"name": "Wheel Rim Lockring", "part_number": "P-UND-407", "unit_cost": 120.0, "supplier_idx": 3, "min_order_qty": 6, "min_stock_level": 8, "lead_time_days": 21},
        {"name": "Hub Bearing Unit", "part_number": "P-UND-408", "unit_cost": 290.0, "supplier_idx": 3, "min_order_qty": 4, "min_stock_level": 6, "lead_time_days": 21},
        
        # Sparse history parts (Supplier 0, 1, 2)
        {"name": "Alternator Unit", "part_number": "P-ENG-901", "unit_cost": 850.0, "supplier_idx": 0, "min_order_qty": 2, "min_stock_level": 2, "lead_time_days": 10},
        {"name": "Transmission Control Module", "part_number": "P-TRN-902", "unit_cost": 1850.0, "supplier_idx": 1, "min_order_qty": 1, "min_stock_level": 1, "lead_time_days": 14},
        {"name": "Main Hydraulic Pump Block", "part_number": "P-HYD-903", "unit_cost": 3200.0, "supplier_idx": 2, "min_order_qty": 1, "min_stock_level": 1, "lead_time_days": 7}
    ]
    
    parts = []
    for p in parts_dict:
        s_id = suppliers[p["supplier_idx"]].id
        part_record = Part(
            name=p["name"],
            part_number=p["part_number"],
            unit_cost=p["unit_cost"],
            supplier_id=s_id,
            min_order_qty=p["min_order_qty"],
            min_stock_level=p["min_stock_level"],
            lead_time_days=p["lead_time_days"]
        )
        db.add(part_record)
        parts.append(part_record)
    db.flush()
    
    # 4. Insert Initial Inventory & Ledger Entries
    # Generates a randomized but stable starting inventory
    initial_stock_factors = {
        "P-ENG-101": 25, "P-ENG-102": 12, "P-ENG-103": 30, "P-ENG-104": 45,
        "P-ENG-105": 20, "P-ENG-106": 15, "P-ENG-107": 18, "P-ENG-108": 20,
        "P-TRN-201": 10, "P-TRN-202": 12, "P-TRN-203": 35, "P-TRN-204": 40,
        "P-TRN-205": 14, "P-TRN-206": 24, "P-HYD-301": 25, "P-HYD-302": 18,
        "P-HYD-303": 8,  "P-HYD-304": 50, "P-HYD-305": 15, "P-HYD-306": 28,
        "P-UND-401": 15, "P-UND-402": 120, "P-UND-403": 180, "P-UND-404": 18,
        "P-UND-405": 20, "P-UND-406": 8,  "P-UND-407": 10, "P-UND-408": 8,
        "P-ENG-901": 3,  "P-TRN-902": 2,   "P-HYD-903": 2
    }
    
    for p in parts:
        qty = initial_stock_factors.get(p.part_number, 10)
        # Create inventory state
        inv = Inventory(part_id=p.id, stock_on_hand=qty, stock_on_order=0, stock_allocated=0)
        db.add(inv)
        # Create ledger INITIAL entry
        ledger = InventoryLedger(
            part_id=p.id,
            transaction_type='INITIAL',
            quantity=qty,
            date='2025-01-01'
        )
        db.add(ledger)
    db.flush()
    
    # 5. Insert Maintenance Templates (Kits)
    # PM250 and PM500 templates mapped to components and parts
    templates_dict = [
        # PM250 Minor Service
        ("PM250", "ENGINE", "P-ENG-104", 1),       # Oil filter
        ("PM250", "ENGINE", "P-ENG-105", 1),       # Hose check
        ("PM250", "TRANSMISSION", "P-TRN-204", 1), # Filter
        ("PM250", "HYDRAULICS", "P-HYD-304", 1),   # Filter
        ("PM250", "UNDERCARRIAGE", "P-UND-402", 4), # Segment bolts
        
        # PM500 Major Service
        ("PM500", "ENGINE", "P-ENG-104", 2),       # Oil filters
        ("PM500", "ENGINE", "P-ENG-103", 1),       # Cylinder gasket
        ("PM500", "ENGINE", "P-ENG-106", 1),       # Thermostat
        ("PM500", "TRANSMISSION", "P-TRN-204", 2), # Oil filters
        ("PM500", "TRANSMISSION", "P-TRN-203", 2), # Torque converter seal
        ("PM500", "HYDRAULICS", "P-HYD-304", 2),   # Main filters
        ("PM500", "HYDRAULICS", "P-HYD-301", 1),   # Cylinder seal kit
        ("PM500", "UNDERCARRIAGE", "P-UND-404", 1), # Brake pads
        ("PM500", "UNDERCARRIAGE", "P-UND-402", 8), # Segment bolts
        ("PM500", "UNDERCARRIAGE", "P-UND-403", 8)  # Shoe bolts
    ]
    
    for maint_type, comp_type, part_num, qty in templates_dict:
        part_rec = next(p for p in parts if p.part_number == part_num)
        tmpl = MaintenanceTemplate(
            maintenance_type=maint_type,
            component_type=comp_type,
            part_id=part_rec.id,
            quantity=qty
        )
        db.add(tmpl)
    db.flush()
    
    # 6. Generate Vehicle Fleet
    # 50 Haul Trucks, 20 Excavators
    vehicles = []
    
    # 50 Haul Trucks
    for i in range(1, 51):
        age = round(random.uniform(1.0, 7.0), 1)
        initial_hours = round(age * 2200.0, 1) # ~2200 operating hours per year
        v = Vehicle(
            name=f"Haul Truck HT-{i:02d}",
            model="CAT 797F",
            age_years=age,
            operating_hours=initial_hours,
            status="ACTIVE"
        )
        db.add(v)
        vehicles.append(v)
        
    # 20 Excavators
    for i in range(1, 21):
        age = round(random.uniform(2.0, 8.0), 1)
        initial_hours = round(age * 1800.0, 1) # ~1800 operating hours per year
        v = Vehicle(
            name=f"Excavator EX-{i:02d}",
            model="Komatsu PC8000",
            age_years=age,
            operating_hours=initial_hours,
            status="ACTIVE"
        )
        db.add(v)
        vehicles.append(v)
        
    db.flush()
    
    # 7. Initialize Components
    # Connect 4 components to each vehicle
    components = []
    component_types = ["ENGINE", "TRANSMISSION", "HYDRAULICS", "UNDERCARRIAGE"]
    
    start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
    
    for v in vehicles:
        for c_type in component_types:
            # Stagger installation history to make it look realistic
            # Component age in hours is random but less than vehicle total hours
            comp_age = round(random.uniform(100.0, min(v.operating_hours, 4000.0)), 1)
            vehicle_hours_at_install = max(0.0, v.operating_hours - comp_age)
            
            # Reconstruct installation date based on vehicle hours
            days_ago = int(comp_age / 15.0) # Assume avg 15 operating hours per day
            install_date = (start_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            c = Component(
                vehicle_id=v.id,
                type=c_type,
                installed_date=install_date,
                operating_hours_at_install=vehicle_hours_at_install,
                current_hours=comp_age
            )
            db.add(c)
            components.append(c)
    db.flush()
    
    # 8. Daily Simulation Loop (Day 1 to 720)
    # Generates cumulative vehicle telemetry, scheduled PMs, failures, usages, orders
    current_sim_date = start_date
    end_sim_date = start_date + timedelta(days=719)
    
    # Maintain in-memory tracking of vehicle hours to speed up daily loops
    vehicle_hours_tracker = {v.id: v.operating_hours for v in vehicles}
    vehicle_status_tracker = {v.id: "ACTIVE" for v in vehicles}
    
    # Component tracking: maps c_id -> (v_id, type, installed_date, vehicle_hours_at_install, comp_current_hours)
    component_tracker = {}
    for c in components:
        component_tracker[c.id] = {
            "vehicle_id": c.vehicle_id,
            "type": c.type,
            "installed_date": c.installed_date,
            "operating_hours_at_install": c.operating_hours_at_install,
            "current_hours": c.current_hours
        }
        
    # Open order list: maps order_id -> (part_id, quantity, expected_delivery_date, status)
    open_orders = {}
    next_order_id = 1
    
    # Active backordered/downed vehicle queues
    # vehicle_id -> {"reason": "FAILURE"/"MAINTENANCE", "ref_id": id, "missing_parts": {part_id: quantity}}
    downed_vehicles = {}
    
    # Component Weibull wear parameters: shape (beta), scale (eta) in hours
    weibull_params = {
        "ENGINE": {"beta": 2.8, "eta": 12000.0},
        "TRANSMISSION": {"beta": 2.4, "eta": 10000.0},
        "HYDRAULICS": {"beta": 2.2, "eta": 8000.0},
        "UNDERCARRIAGE": {"beta": 2.0, "eta": 6000.0}
    }
    
    # Part failure mapping
    part_failure_map = {
        "ENGINE": ["P-ENG-101", "P-ENG-102", "P-ENG-103", "P-ENG-107", "P-ENG-108"],
        "TRANSMISSION": ["P-TRN-201", "P-TRN-202", "P-TRN-205", "P-TRN-206"],
        "HYDRAULICS": ["P-HYD-301", "P-HYD-302", "P-HYD-303", "P-HYD-305", "P-HYD-306"],
        "UNDERCARRIAGE": ["P-UND-401", "P-UND-404", "P-UND-405", "P-UND-406", "P-UND-408"]
    }
    
    # Sparse / Rare part failure mapping
    sparse_failure_map = {
        "ENGINE": "P-ENG-901",
        "TRANSMISSION": "P-TRN-902",
        "HYDRAULICS": "P-HYD-903"
    }
    
    # Track daily telemetry for batch commits
    telemetry_to_add = []
    
    # Running total of PM schedules to avoid duplicate PM generation
    # v_id -> last PM target hours
    last_pm_trigger = {v.id: int(v.operating_hours / 250.0) * 250 for v in vehicles}
    
    print("Simulating fleet wear and operations...")
    for day in range(720):
        date_str = current_sim_date.strftime("%Y-%m-%d")
        
        # A. Process Deliveries
        delivered_orders = []
        for o_id, order in list(open_orders.items()):
            if order["expected_delivery_date"] == date_str and order["status"] == "PLACED":
                # Order arrives!
                order["status"] = "DELIVERED"
                delivered_orders.append(o_id)
                
                # Update DB PurchaseOrder
                db_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == o_id).first()
                if db_po:
                    db_po.status = "DELIVERED"
                    db_po.actual_delivery_date = date_str
                    
                # Update inventory ledger
                ledger = InventoryLedger(
                    part_id=order["part_id"],
                    transaction_type='DELIVERY',
                    quantity=order["quantity"],
                    date=date_str,
                    reference_id=o_id
                )
                db.add(ledger)
                
                # Update Inventory Stock
                inv = db.query(Inventory).filter(Inventory.part_id == order["part_id"]).first()
                if inv:
                    inv.stock_on_hand += order["quantity"]
                    inv.stock_on_order = max(0, inv.stock_on_order - order["quantity"])
                    
        # Remove delivered orders from open_orders
        for o_id in delivered_orders:
            del open_orders[o_id]
            
        # B. Attempt to Revive Downed Vehicles
        resolved_revivals = []
        for v_id, down_info in list(downed_vehicles.items()):
            # Check if all missing parts are now available
            parts_available = True
            for p_id, qty in down_info["missing_parts"].items():
                inv = db.query(Inventory).filter(Inventory.part_id == p_id).first()
                if not inv or inv.stock_on_hand < qty:
                    parts_available = False
                    break
                    
            if parts_available:
                # Revive vehicle!
                resolved_revivals.append(v_id)
                
                # Consume inventory
                for p_id, qty in down_info["missing_parts"].items():
                    inv = db.query(Inventory).filter(Inventory.part_id == p_id).first()
                    inv.stock_on_hand -= qty
                    
                    # Create ledger entry
                    ledger = InventoryLedger(
                        part_id=p_id,
                        transaction_type='USAGE',
                        quantity=-qty,
                        date=date_str
                    )
                    db.add(ledger)
                    db.flush()
                    
                    # Log PartUsage
                    use = PartUsage(
                        vehicle_id=v_id,
                        part_id=p_id,
                        quantity=qty,
                        usage_date=date_str
                    )
                    if down_info["reason"] == "FAILURE":
                        use.failure_id = down_info["ref_id"]
                    else:
                        use.maintenance_plan_id = down_info["ref_id"]
                    db.add(use)
                    
                    # Update ledger reference
                    ledger.reference_id = use.id
                    
                # Calculate downtime hours
                start_dt = datetime.strptime(down_info["start_date"], "%Y-%m-%d")
                days_down = (current_sim_date - start_dt).days
                downtime_hours = days_down * 24.0
                
                # Resolve Failure/Maintenance record
                if down_info["reason"] == "FAILURE":
                    fail_rec = db.query(Failure).filter(Failure.id == down_info["ref_id"]).first()
                    if fail_rec:
                        fail_rec.resolved = True
                        fail_rec.downtime_hours = downtime_hours
                else:
                    pm_rec = db.query(MaintenancePlan).filter(MaintenancePlan.id == down_info["ref_id"]).first()
                    if pm_rec:
                        pm_rec.status = "COMPLETED"
                        
                # Re-activate vehicle
                vehicle_status_tracker[v_id] = "ACTIVE"
                veh = db.query(Vehicle).filter(Vehicle.id == v_id).first()
                if veh:
                    veh.status = "ACTIVE"
                    
        # Remove resolved revivals
        for v_id in resolved_revivals:
            del downed_vehicles[v_id]
            
        # C. Daily Telemetry Accumulation
        for v in vehicles:
            v_id = v.id
            if vehicle_status_tracker[v_id] == "ACTIVE":
                # Stochastically add running hours based on model type
                if v.model == "CAT 797F":
                    daily_hours = round(random.uniform(14.0, 18.0), 1)
                else:  # Komatsu PC8000
                    daily_hours = round(random.uniform(10.0, 14.0), 1)
                    
                vehicle_hours_tracker[v_id] = round(vehicle_hours_tracker[v_id] + daily_hours, 1)
                
                # Log telemetry
                tel = VehicleTelemetry(
                    vehicle_id=v_id,
                    date=date_str,
                    operating_hours=vehicle_hours_tracker[v_id]
                )
                db.add(tel)
                
                # Update component wear in tracker
                for c_id, comp in component_tracker.items():
                    if comp["vehicle_id"] == v_id:
                        comp["current_hours"] = round(comp["current_hours"] + daily_hours, 1)
                            
        # D. Trigger New Preventive Maintenance Plans
        for v in vehicles:
            v_id = v.id
            if vehicle_status_tracker[v_id] != "ACTIVE":
                continue
                
            curr_hours = vehicle_hours_tracker[v_id]
            next_pm_bound = last_pm_trigger[v_id] + 250
            
            if curr_hours >= next_pm_bound:
                last_pm_trigger[v_id] = next_pm_bound
                pm_type = "PM500" if (next_pm_bound % 500 == 0) else "PM250"
                
                pm_comp_type = random.choice(component_types)
                # Find active component of this type
                active_comp_id = next(
                    c_id for c_id, comp in component_tracker.items() 
                    if comp["vehicle_id"] == v_id and comp["type"] == pm_comp_type
                )
                
                # Rescheduling logic: 10% chance of maintenance delay (SCENARIO_MAINTENANCE_RESCHEDULE)
                is_rescheduled = random.random() < 0.10
                sched_date = date_str
                original_date = None
                reason = None
                resched_ts = None
                
                if is_rescheduled:
                    original_date = date_str
                    delay_days = random.randint(3, 7)
                    sched_date = (current_sim_date + timedelta(days=delay_days)).strftime("%Y-%m-%d")
                    reason = "Operational bottleneck - high load capacity target"
                    resched_ts = datetime.now().isoformat()
                    
                    # Apply wear penalty directly: components age extra hours
                    for c_id, comp in component_tracker.items():
                        if comp["vehicle_id"] == v_id:
                            comp["current_hours"] = round(comp["current_hours"] + 120.0, 1)
                            
                plan = MaintenancePlan(
                    vehicle_id=v_id,
                    component_id=active_comp_id,
                    description=pm_type,
                    scheduled_date=sched_date,
                    scheduled_hours=next_pm_bound,
                    original_scheduled_date=original_date,
                    rescheduled_reason=reason,
                    rescheduled_timestamp=resched_ts,
                    status="PENDING"
                )
                db.add(plan)
        
        db.flush()  # Ensure newly generated plans are persisted for execution step
        
        # E. Process Pending Maintenance Plans Scheduled for Today
        today_plans = db.query(MaintenancePlan)\
            .filter(MaintenancePlan.scheduled_date == date_str, MaintenancePlan.status == 'PENDING')\
            .all()
            
        for plan in today_plans:
            v_id = plan.vehicle_id
            # Retrieve active component
            comp_rec = db.query(Component).filter(Component.id == plan.component_id).first()
            if not comp_rec:
                continue
            
            # Check parts requirements from templates
            required_parts = {}
            templates = db.query(MaintenanceTemplate)\
                .filter(MaintenanceTemplate.maintenance_type == plan.description, MaintenanceTemplate.component_type == comp_rec.type)\
                .all()
                
            for t in templates:
                required_parts[t.part_id] = t.quantity
                
            parts_available = True
            for p_id, qty in required_parts.items():
                inv = db.query(Inventory).filter(Inventory.part_id == p_id).first()
                if not inv or inv.stock_on_hand < qty:
                    parts_available = False
                    break
                    
            if parts_available:
                # Execute maintenance!
                for p_id, qty in required_parts.items():
                    inv = db.query(Inventory).filter(Inventory.part_id == p_id).first()
                    inv.stock_on_hand -= qty
                    
                    ledger = InventoryLedger(
                        part_id=p_id,
                        transaction_type='USAGE',
                        quantity=-qty,
                        date=date_str
                    )
                    db.add(ledger)
                    db.flush()
                    
                    use = PartUsage(
                        vehicle_id=v_id,
                        part_id=p_id,
                        maintenance_plan_id=plan.id,
                        quantity=qty,
                        usage_date=date_str
                    )
                    db.add(use)
                    ledger.reference_id = use.id
                    
                plan.status = "COMPLETED"
            else:
                # Stockout! Vehicle goes DOWN for maintenance
                vehicle_status_tracker[v_id] = "DOWN"
                # Update DB vehicle status
                veh = db.query(Vehicle).filter(Vehicle.id == v_id).first()
                if veh:
                    veh.status = "MAINTENANCE"
                    
                downed_vehicles[v_id] = {
                    "reason": "MAINTENANCE",
                    "ref_id": plan.id,
                    "missing_parts": required_parts,
                    "start_date": date_str
                }
                
                # Order replenishment for missing parts
                for p_id, qty in required_parts.items():
                    trigger_part_order(db, p_id, date_str, open_orders, next_order_id, supplier_delay_day=(date_str == "2025-06-15"))
                    next_order_id += 1

        # F. Process Wear-based Component Failures (Weibull Process)
        for c_id, comp in list(component_tracker.items()):
            v_id = comp["vehicle_id"]
            if vehicle_status_tracker[v_id] != "ACTIVE":
                continue
                
            c_type = comp["type"]
            c_hours = comp["current_hours"]
            
            # Calculate Weibull hazard rate
            params = weibull_params[c_type]
            beta = params["beta"]
            # Accelerate wear if scheduled maintenance was overdue
            eta = params["eta"]
            
            # Probability of failure in next hour
            hazard = (beta / eta) * ((c_hours / eta) ** (beta - 1))
            p_failure = min(0.99, hazard * 15.0)
            
            # Check for stochastically generated failure
            is_failure = random.random() < p_failure
            scenario_id = 'SCENARIO_NORMAL_WEAR'
            
            # Catastrophic failure injection (0.1% chance on any active component)
            if not is_failure and random.random() < 0.001:
                is_failure = True
                scenario_id = 'SCENARIO_CATASTROPHIC_FAILURE'
                
            if is_failure:
                # Down vehicle
                vehicle_status_tracker[v_id] = "DOWN"
                veh = db.query(Vehicle).filter(Vehicle.id == v_id).first()
                if veh:
                    veh.status = "DOWN"
                    
                # Create Failure record referencing failed component c_id
                fail_rec = Failure(
                    vehicle_id=v_id,
                    component_id=c_id,
                    failure_date=date_str,
                    operating_hours=vehicle_hours_tracker[v_id],
                    severity="CATASTROPHIC" if scenario_id == 'SCENARIO_CATASTROPHIC_FAILURE' else "MINOR",
                    resolved=False,
                    scenario_id=scenario_id
                )
                db.add(fail_rec)
                db.flush()
                
                # Determine parts required
                part_codes = part_failure_map[c_type]
                part_code_selected = random.choice(part_codes)
                
                # Sparse history injection (5% chance of rare part failure)
                if c_type in sparse_failure_map and random.random() < 0.05:
                    part_code_selected = sparse_failure_map[c_type]
                    fail_rec.scenario_id = 'SCENARIO_SPARSE_HISTORY'
                    
                part_rec = next(p for p in parts if p.part_number == part_code_selected)
                fail_rec.part_id = part_rec.id
                
                required_qty = 1
                required_parts = {part_rec.id: required_qty}
                
                # Update final component hours in DB for the old component before replacing it
                old_db_c = db.query(Component).filter(Component.id == c_id).first()
                if old_db_c:
                    old_db_c.current_hours = comp["current_hours"]
                
                # Relational Component replacement: Create a NEW Component row
                new_comp = Component(
                    vehicle_id=v_id,
                    type=c_type,
                    installed_date=date_str,
                    operating_hours_at_install=vehicle_hours_tracker[v_id],
                    current_hours=0.0
                )
                db.add(new_comp)
                db.flush()  # Populate new_comp.id
                
                # Update component tracker for future runs
                component_tracker[new_comp.id] = {
                    "vehicle_id": v_id,
                    "type": c_type,
                    "installed_date": date_str,
                    "operating_hours_at_install": vehicle_hours_tracker[v_id],
                    "current_hours": 0.0
                }
                
                # De-register old component from wear simulation
                del component_tracker[c_id]
                
                # Check stock for replacement part
                inv = db.query(Inventory).filter(Inventory.part_id == part_rec.id).first()
                if inv and inv.stock_on_hand >= required_qty:
                    # Resolve failure immediately
                    inv.stock_on_hand -= required_qty
                    
                    ledger = InventoryLedger(
                        part_id=part_rec.id,
                        transaction_type='USAGE',
                        quantity=-required_qty,
                        date=date_str
                    )
                    db.add(ledger)
                    db.flush()
                    
                    use = PartUsage(
                        vehicle_id=v_id,
                        part_id=part_rec.id,
                        failure_id=fail_rec.id,
                        quantity=required_qty,
                        usage_date=date_str
                    )
                    db.add(use)
                    ledger.reference_id = use.id
                    
                    fail_rec.resolved = True
                    vehicle_status_tracker[v_id] = "ACTIVE"
                    veh.status = "ACTIVE"
                else:
                    # Stockout! Vehicle remains downed
                    downed_vehicles[v_id] = {
                        "reason": "FAILURE",
                        "ref_id": fail_rec.id,
                        "missing_parts": required_parts,
                        "start_date": date_str
                    }
                    
                    # Order replacement parts
                    trigger_part_order(db, part_rec.id, date_str, open_orders, next_order_id, supplier_delay_day=(date_str == "2025-06-15"))
                    next_order_id += 1
                    
        # G. Baseline Inventory Replenishment Check
        for p in parts:
            inv = db.query(Inventory).filter(Inventory.part_id == p.id).first()
            if inv:
                total_stock = inv.stock_on_hand + inv.stock_on_order
                if total_stock < p.min_stock_level:
                    order_qty = max(p.min_order_qty, p.min_stock_level * 2)
                    trigger_part_order(db, p.id, date_str, open_orders, next_order_id, order_qty=order_qty, supplier_delay_day=(date_str == "2025-06-15"))
                    next_order_id += 1
                    
        current_sim_date += timedelta(days=1)
        
        if day % 30 == 0:
            db.flush()
            
    # Update final component hours in DB for active components
    for c_id, comp in component_tracker.items():
        db_c = db.query(Component).filter(Component.id == c_id).first()
        if db_c:
            db_c.current_hours = comp["current_hours"]
            
    # Commit transaction
    db.commit()
    print("Simulation execution complete.")
    
    # 9. Generate Summary Reports
    write_data_summary(db)
    write_validation_report(db)

def trigger_part_order(db: Session, part_id: int, date_str: str, open_orders: dict, order_id: int, order_qty: int = None, supplier_delay_day: bool = False) -> int:
    """Helper to place a purchase order with suppliers, incorporating lead time distributions."""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        return 0
        
    qty = order_qty if order_qty is not None else part.min_order_qty
    
    # Calculate delivery date with variability
    supplier = part.supplier
    base_lead = supplier.base_lead_time_days
    
    # Log-normal lead time simulation to represent standard delay curves
    lead_time = int(np.random.lognormal(np.log(base_lead), 0.15))
    lead_time = max(1, lead_time) # guarantee at least 1 day lead time
    
    # Supplier disruption inject (SCENARIO_SUPPLIER_DELAY)
    # If the order is placed on or after 2025-06-15 with supplier Heavy Undercarriage Ltd, and no prior delayed order exists, inflate lead time by 4x
    is_delayed = False
    if supplier.name == "Heavy Undercarriage Ltd" and date_str >= "2025-06-15":
        prior_orders = db.query(PurchaseOrder).join(Part).join(Supplier)\
            .filter(Supplier.name == "Heavy Undercarriage Ltd", PurchaseOrder.order_date >= "2025-06-15")\
            .count()
        if prior_orders == 0:
            is_delayed = True
            
    if is_delayed:
        lead_time *= 4
        print(f"Supplier Delay Injected: Heavy Undercarriage Ltd lead time inflated to {lead_time} days on order placed on {date_str}.")
        
    expected_delivery = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=lead_time)).strftime("%Y-%m-%d")
    
    # DB entry
    po = PurchaseOrder(
        id=order_id,
        part_id=part_id,
        quantity=qty,
        order_date=date_str,
        expected_delivery_date=expected_delivery,
        status="PLACED"
    )
    db.add(po)
    
    # Update inventory
    inv = db.query(Inventory).filter(Inventory.part_id == part_id).first()
    if inv:
        inv.stock_on_order += qty
        
    # Tracker insert
    open_orders[order_id] = {
        "part_id": part_id,
        "quantity": qty,
        "expected_delivery_date": expected_delivery,
        "status": "PLACED"
    }
    
    return order_id

def write_data_summary(db: Session):
    summary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/data_summary.json"))
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    num_vehicles = db.query(Vehicle).count()
    num_components = db.query(Component).count()
    num_parts = db.query(Part).count()
    num_suppliers = db.query(Supplier).count()
    num_maintenance = db.query(MaintenancePlan).count()
    num_failures = db.query(Failure).count()
    num_usage = db.query(PartUsage).count()
    
    # Failures by component
    failures_by_comp = {}
    for c_type in ["ENGINE", "TRANSMISSION", "HYDRAULICS", "UNDERCARRIAGE"]:
        failures_by_comp[c_type] = db.query(Failure).join(Component).filter(Component.type == c_type).count()
        
    # Usage by part
    usage_by_part = {}
    for p in db.query(Part).all():
        usage_by_part[p.part_number] = int(db.query(func.sum(PartUsage.quantity)).filter(PartUsage.part_id == p.id).scalar() or 0)
        
    # Total downtime
    total_downtime = db.query(func.sum(Failure.downtime_hours)).scalar() or 0.0
    
    # Scenario counts
    scenario_counts = {
        "SCENARIO_NORMAL_WEAR": db.query(Failure).filter(Failure.scenario_id == 'SCENARIO_NORMAL_WEAR').count(),
        "SCENARIO_CATASTROPHIC_FAILURE": db.query(Failure).filter(Failure.scenario_id == 'SCENARIO_CATASTROPHIC_FAILURE').count(),
        "SCENARIO_SPARSE_HISTORY": db.query(Failure).filter(Failure.scenario_id == 'SCENARIO_SPARSE_HISTORY').count()
    }
    
    # Sparse parts (parts with usage frequency <= 3)
    sparse_parts = []
    for p in db.query(Part).all():
        usages = db.query(PartUsage).filter(PartUsage.part_id == p.id).count()
        if usages <= 3:
            sparse_parts.append({"part_number": p.part_number, "name": p.name, "usage_frequency": usages})
            
    summary = {
        "number_of_vehicles": num_vehicles,
        "number_of_components": num_components,
        "number_of_parts": num_parts,
        "number_of_suppliers": num_suppliers,
        "number_of_maintenance_events": num_maintenance,
        "number_of_failures": num_failures,
        "number_of_part_usage_records": num_usage,
        "total_downtime_hours": float(total_downtime),
        "failures_by_component": failures_by_comp,
        "usage_by_part": usage_by_part,
        "sparse_parts": sparse_parts,
        "scenario_counts": scenario_counts
    }
    
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=4)
        
    print(f"Data summary report generated at: {summary_path}")

def write_validation_report(db: Session):
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/data_validation_report.json"))
    
    errors = []
    
    # 1. Foreign-key / DB consistency check
    # Check that all components point to valid vehicles
    for c in db.query(Component).all():
        if not db.query(Vehicle).filter(Vehicle.id == c.vehicle_id).first():
            errors.append(f"Foreign Key Error: Component id {c.id} points to non-existent vehicle id {c.vehicle_id}.")
            
    # 2. No negative inventory
    for inv in db.query(Inventory).all():
        if inv.stock_on_hand < 0:
            errors.append(f"Validation Error: Part id {inv.part_id} has negative stock_on_hand ({inv.stock_on_hand}).")
            
    # 3. No negative quantities in usage
    for u in db.query(PartUsage).all():
        if u.quantity < 0:
            errors.append(f"Validation Error: PartUsage id {u.id} has negative quantity ({u.quantity}).")
            
    # 4. Component installation before failure
    for f in db.query(Failure).all():
        comp = db.query(Component).filter(Component.id == f.component_id).first()
        if comp and comp.installed_date > f.failure_date:
            errors.append(f"Logic Error: Component id {f.component_id} was installed on {comp.installed_date}, which is after failure date {f.failure_date}.")
            
    # 5. Failure before associated part usage
    for u in db.query(PartUsage).filter(PartUsage.failure_id != None).all():
        f = db.query(Failure).filter(Failure.id == u.failure_id).first()
        if f and f.failure_date > u.usage_date:
            errors.append(f"Logic Error: Failure id {u.failure_id} date {f.failure_date} is after usage date {u.usage_date}.")
            
    # 6. Maintenance before associated part usage
    for u in db.query(PartUsage).filter(PartUsage.maintenance_plan_id != None).all():
        m = db.query(MaintenancePlan).filter(MaintenancePlan.id == u.maintenance_plan_id).first()
        if m and m.scheduled_date > u.usage_date:
            errors.append(f"Logic Error: MaintenancePlan id {u.maintenance_plan_id} scheduled date {m.scheduled_date} is after usage date {u.usage_date}.")
            
    # 7. Supplier exists for every part
    for p in db.query(Part).all():
        if not db.query(Supplier).filter(Supplier.id == p.supplier_id).first():
            errors.append(f"Foreign Key Error: Part id {p.id} references non-existent supplier id {p.supplier_id}.")
            
    # 8. Every part has inventory record
    for p in db.query(Part).all():
        if not db.query(Inventory).filter(Inventory.part_id == p.id).first():
            errors.append(f"Database Error: Part id {p.id} has no inventory record.")
            
    # 9. No impossible operating hours regressions (telemetry hours should increase over time)
    for v in db.query(Vehicle).all():
        tel = db.query(VehicleTelemetry).filter(VehicleTelemetry.vehicle_id == v.id).order_by(VehicleTelemetry.date).all()
        for idx in range(1, len(tel)):
            if tel[idx].operating_hours < tel[idx-1].operating_hours:
                errors.append(f"Telemetry Error: Vehicle id {v.id} operating hours regressed from {tel[idx-1].operating_hours} on {tel[idx-1].date} to {tel[idx].operating_hours} on {tel[idx].date}.")
                
    validation_status = "PASSED" if len(errors) == 0 else "FAILED"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": validation_status,
        "errors_detected": len(errors),
        "errors_list": errors
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Data validation report generated at: {report_path} - Status: {validation_status}")

if __name__ == "__main__":
    main()
