from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database.models import (
    Vehicle, VehicleTelemetry, Component, Failure, PartUsage,
    MaintenancePlan, Part, InventoryLedger, PurchaseOrder, MaintenanceTemplate, Supplier
)
from backend.app.services.snapshot import get_feature_snapshot, parse_date, add_days

@dataclass
class ComponentFeatureVector:
    """
    Feature vector for a single active component at prediction timestamp T.
    All metrics represent historical state at or before timestamp T with zero temporal leakage.
    """
    # Identifiers & Metadata
    component_id: int
    vehicle_id: int
    component_type: str                  # ENGINE, TRANSMISSION, HYDRAULICS, UNDERCARRIAGE
    vehicle_model: str                   # CAT 797F, Komatsu PC8000
    vehicle_name: str
    vehicle_age_years: float
    prediction_timestamp: str            # YYYY-MM-DD
    
    # 1. COMPONENT FEATURES
    component_age_hours: float          # Operating hours accumulated by this component
    component_age_days: float           # Days elapsed since component installation
    hours_since_component_installation: float  # Vehicle hours run since installation
    hours_since_last_maintenance: float # Vehicle hours run since latest completed PM for this component/vehicle
    previous_component_failure_count: int # Count of failures for this specific component instance <= T
    
    # 2. TELEMETRY FEATURES
    running_hours_7d: float              # Vehicle running hours in [T-7d, T]
    running_hours_30d: float             # Vehicle running hours in [T-30d, T]
    running_hours_90d: float             # Vehicle running hours in [T-90d, T]
    utilization_trend_7d_vs_30d: float   # Ratio of daily average running hours (7d avg / 30d avg)
    
    # 3. MAINTENANCE FEATURES
    maintenance_count_30d: int           # Count of PM events completed in [T-30d, T]
    maintenance_count_90d: int           # Count of PM events completed in [T-90d, T]
    has_delayed_maintenance: bool        # True if there is an overdue or rescheduled pending PM <= T
    delayed_maintenance_count: int       # Count of overdue or rescheduled PM plans <= T
    hours_associated_with_delayed_maintenance: float # Total overdue/penalty hours from delayed PM
    
    # 4. FAILURE HISTORY FEATURES
    previous_failures_component: int     # Count of failures for this component instance <= T
    previous_failures_vehicle_component_type: int # Count of failures for this comp type on vehicle <= T (incl. retired)
    days_since_previous_failure: Optional[float]   # Days since last failure for this comp/type <= T
    hours_since_previous_failure: Optional[float]  # Vehicle operating hours accumulated since last failure <= T
    
    # 5. PART / INVENTORY FEATURES
    associated_part_numbers: List[str]   # Catalog part numbers mapped to this component type
    part_usage_30d: int                  # Part units consumed for this component type on vehicle in [T-30d, T]
    part_usage_90d: int                  # Part units consumed for this component type on vehicle in [T-90d, T]
    min_stock_on_hand: int               # Lowest stock on hand among associated parts as of T
    total_stock_on_hand: int             # Total stock on hand among associated parts as of T
    total_stock_on_order: int            # Total stock on order among associated parts as of T
    total_stock_allocated: int           # Total stock allocated among associated parts as of T
    max_supplier_lead_time_days: int     # Max supplier lead time for associated parts
    min_supplier_reliability: float      # Min supplier reliability rate for associated parts

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class FleetFeatureSet:
    """
    Container holding metadata and feature vectors for all active components across the fleet at timestamp T.
    """
    prediction_timestamp: str
    vehicle_count: int
    component_count: int
    features: List[ComponentFeatureVector]

    def to_dict(self) -> dict:
        return {
            "prediction_timestamp": self.prediction_timestamp,
            "vehicle_count": self.vehicle_count,
            "component_count": self.component_count,
            "features": [f.to_dict() for f in self.features]
        }

def generate_features(db: Session, prediction_timestamp: str, snapshot: Optional[dict] = None) -> FleetFeatureSet:
    """
    Generates deterministic feature vectors for all active components at prediction_timestamp (YYYY-MM-DD).
    Strictly enforces zero temporal leakage by using get_feature_snapshot or date-bounded database queries (<= prediction_timestamp).
    """
    if snapshot is None:
        snapshot = get_feature_snapshot(db, prediction_timestamp)
        
    t_dt = datetime.strptime(prediction_timestamp, "%Y-%m-%d").date()
    t_7d_str = (t_dt - timedelta(days=7)).strftime("%Y-%m-%d")
    t_30d_str = (t_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    t_90d_str = (t_dt - timedelta(days=90)).strftime("%Y-%m-%d")
    
    # Pre-map vehicles and components from snapshot
    vehicles_by_id = {v["id"]: v for v in snapshot["vehicles"]}
    components = snapshot["components"]
    snapshot_failures = snapshot["failures"]
    snapshot_part_usage = snapshot["part_usage"]
    snapshot_maint_plans = snapshot["maintenance_plans"]
    snapshot_inventory_by_part = {inv["part_id"]: inv for inv in snapshot["inventory"]}
    
    # Build part catalog mappings per component type
    # Part numbers follow convention e.g. P-ENG-*, P-TRN-*, P-HYD-*, P-UND-*
    prefix_map = {
        "ENGINE": "P-ENG-",
        "TRANSMISSION": "P-TRN-",
        "HYDRAULICS": "P-HYD-",
        "UNDERCARRIAGE": "P-UND-"
    }
    
    all_parts = db.query(Part).all()
    parts_by_comp_type: Dict[str, List[Part]] = {ctype: [] for ctype in prefix_map}
    
    for p in all_parts:
        for ctype, prefix in prefix_map.items():
            if p.part_number.startswith(prefix):
                parts_by_comp_type[ctype].append(p)
                
    # Also incorporate MaintenanceTemplate mappings
    templates = db.query(MaintenanceTemplate).all()
    for tmpl in templates:
        p_obj = next((p for p in all_parts if p.id == tmpl.part_id), None)
        if p_obj and tmpl.component_type in parts_by_comp_type:
            if p_obj not in parts_by_comp_type[tmpl.component_type]:
                parts_by_comp_type[tmpl.component_type].append(p_obj)

    feature_vectors: List[ComponentFeatureVector] = []
    
    for c in components:
        c_id = c["id"]
        v_id = c["vehicle_id"]
        c_type = c["type"]
        v_data = vehicles_by_id.get(v_id, {})
        
        v_model = v_data.get("model", "UNKNOWN")
        v_name = v_data.get("name", "UNKNOWN")
        v_age = v_data.get("age_years", 0.0)
        v_hours = v_data.get("operating_hours", 0.0)
        
        c_age_hours = c["current_hours"]
        c_install_date = c["installed_date"]
        c_install_dt = parse_date(c_install_date)
        c_age_days = max(0.0, float((t_dt - c_install_dt).days))
        
        # 1. COMPONENT FEATURES
        # Hours since last maintenance (completed plan <= T for this vehicle & comp type or comp_id)
        comp_maint_plans = [
            p for p in snapshot_maint_plans 
            if p["vehicle_id"] == v_id and p["status"] == "COMPLETED"
        ]
        
        latest_maint_veh_hours = None
        if comp_maint_plans:
            # Query last completed usage date <= T
            completed_plan_ids = {p["id"] for p in comp_maint_plans}
            comp_usages = [u for u in snapshot_part_usage if u.get("maintenance_plan_id") in completed_plan_ids]
            if comp_usages:
                latest_usage_date = max(u["usage_date"] for u in comp_usages)
                # Find vehicle hours on that telemetry date <= T
                tel_m = db.query(VehicleTelemetry)\
                    .filter(VehicleTelemetry.vehicle_id == v_id, VehicleTelemetry.date <= latest_usage_date)\
                    .order_by(VehicleTelemetry.date.desc()).first()
                if tel_m:
                    latest_maint_veh_hours = tel_m.operating_hours
                    
        if latest_maint_veh_hours is not None:
            hours_since_last_maint = max(0.0, round(v_hours - latest_maint_veh_hours, 1))
        else:
            hours_since_last_maint = c_age_hours

        # 2. TELEMETRY FEATURES
        # Running hours over windows [T-7d, T], [T-30d, T], [T-90d, T]
        # Query latest telemetry at or before T, T-7d, T-30d, T-90d
        tel_T = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == v_id, VehicleTelemetry.date <= prediction_timestamp)\
            .order_by(VehicleTelemetry.date.desc()).first()
        h_T = tel_T.operating_hours if tel_T else 0.0
        
        tel_7d = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == v_id, VehicleTelemetry.date <= t_7d_str)\
            .order_by(VehicleTelemetry.date.desc()).first()
        h_7d = tel_7d.operating_hours if tel_7d else 0.0
        
        tel_30d = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == v_id, VehicleTelemetry.date <= t_30d_str)\
            .order_by(VehicleTelemetry.date.desc()).first()
        h_30d = tel_30d.operating_hours if tel_30d else 0.0
        
        tel_90d = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == v_id, VehicleTelemetry.date <= t_90d_str)\
            .order_by(VehicleTelemetry.date.desc()).first()
        h_90d = tel_90d.operating_hours if tel_90d else 0.0
        
        running_7d = max(0.0, round(h_T - h_7d, 1))
        running_30d = max(0.0, round(h_T - h_30d, 1))
        running_90d = max(0.0, round(h_T - h_90d, 1))
        
        avg_daily_30d = running_30d / 30.0
        if avg_daily_30d > 0.0:
            utilization_trend = round((running_7d / 7.0) / (running_30d / 30.0), 4)
        else:
            utilization_trend = 1.0

        # 3. MAINTENANCE FEATURES
        # Count completed maintenance plans in windows
        comp_usages_30d = [
            u for u in snapshot_part_usage 
            if u["vehicle_id"] == v_id and u.get("maintenance_plan_id") and u["usage_date"] >= t_30d_str
        ]
        maint_count_30d = len({u["maintenance_plan_id"] for u in comp_usages_30d})
        
        comp_usages_90d = [
            u for u in snapshot_part_usage 
            if u["vehicle_id"] == v_id and u.get("maintenance_plan_id") and u["usage_date"] >= t_90d_str
        ]
        maint_count_90d = len({u["maintenance_plan_id"] for u in comp_usages_90d})
        
        # Pending/Delayed maintenance plans <= T
        pending_plans = [
            p for p in snapshot_maint_plans 
            if p["vehicle_id"] == v_id and p["status"] == "PENDING"
        ]
        
        delayed_plans = [
            p for p in pending_plans 
            if p["scheduled_date"] <= prediction_timestamp or p.get("original_scheduled_date") is not None
        ]
        
        has_delayed = len(delayed_plans) > 0
        delayed_count = len(delayed_plans)
        
        delayed_hours_penalty = 0.0
        for p in delayed_plans:
            if p["scheduled_hours"] < v_hours:
                delayed_hours_penalty += (v_hours - p["scheduled_hours"])
            if p.get("original_scheduled_date"):
                delayed_hours_penalty += 120.0  # Operational wear penalty factor
        delayed_hours_penalty = round(delayed_hours_penalty, 1)

        # 4. FAILURE HISTORY FEATURES
        # Component instance failures <= T
        comp_failures = [f for f in snapshot_failures if f["component_id"] == c_id]
        prev_comp_failures = len(comp_failures)
        
        # Vehicle + Component type failures <= T (includes retired components)
        v_ctype_comp_ids = {
            comp_db.id for comp_db in db.query(Component)
            .filter(Component.vehicle_id == v_id, Component.type == c_type, Component.installed_date <= prediction_timestamp)
            .all()
        }
        v_ctype_failures = [f for f in snapshot_failures if f["component_id"] in v_ctype_comp_ids or f["vehicle_id"] == v_id]
        # Filter strictly for matching component type
        v_ctype_failures_filtered = []
        for f in v_ctype_failures:
            f_comp = db.query(Component).filter(Component.id == f["component_id"]).first()
            if f_comp and f_comp.type == c_type:
                v_ctype_failures_filtered.append(f)
                
        prev_v_ctype_failures = len(v_ctype_failures_filtered)
        
        days_since_prev_fail: Optional[float] = None
        hours_since_prev_fail: Optional[float] = None
        
        if v_ctype_failures_filtered:
            latest_fail = max(v_ctype_failures_filtered, key=lambda f: f["failure_date"])
            fail_date = parse_date(latest_fail["failure_date"])
            days_since_prev_fail = max(0.0, float((t_dt - fail_date).days))
            
            # Hours since previous failure
            tel_f = db.query(VehicleTelemetry)\
                .filter(VehicleTelemetry.vehicle_id == v_id, VehicleTelemetry.date <= latest_fail["failure_date"])\
                .order_by(VehicleTelemetry.date.desc()).first()
            f_hours = tel_f.operating_hours if tel_f else 0.0
            hours_since_prev_fail = max(0.0, round(v_hours - f_hours, 1))

        # 5. PART / INVENTORY FEATURES
        assoc_parts = parts_by_comp_type.get(c_type, [])
        assoc_part_ids = {p.id for p in assoc_parts}
        assoc_part_numbers = [p.part_number for p in assoc_parts]
        
        usage_30d = sum(
            u["quantity"] for u in snapshot_part_usage 
            if u["vehicle_id"] == v_id and u["part_id"] in assoc_part_ids and u["usage_date"] >= t_30d_str
        )
        usage_90d = sum(
            u["quantity"] for u in snapshot_part_usage 
            if u["vehicle_id"] == v_id and u["part_id"] in assoc_part_ids and u["usage_date"] >= t_90d_str
        )
        
        inv_items = [snapshot_inventory_by_part[pid] for pid in assoc_part_ids if pid in snapshot_inventory_by_part]
        
        if inv_items:
            min_stock = min(item["stock_on_hand"] for item in inv_items)
            tot_stock = sum(item["stock_on_hand"] for item in inv_items)
            tot_order = sum(item["stock_on_order"] for item in inv_items)
            tot_alloc = sum(item["stock_allocated"] for item in inv_items)
        else:
            min_stock = 0
            tot_stock = 0
            tot_order = 0
            tot_alloc = 0
            
        if assoc_parts:
            max_lead = max(p.supplier.base_lead_time_days if p.supplier else p.lead_time_days for p in assoc_parts)
            min_rel = min(p.supplier.reliability_rate if p.supplier else 1.0 for p in assoc_parts)
        else:
            max_lead = 7
            min_rel = 1.0

        vec = ComponentFeatureVector(
            component_id=c_id,
            vehicle_id=v_id,
            component_type=c_type,
            vehicle_model=v_model,
            vehicle_name=v_name,
            vehicle_age_years=v_age,
            prediction_timestamp=prediction_timestamp,
            component_age_hours=c_age_hours,
            component_age_days=c_age_days,
            hours_since_component_installation=c_age_hours,
            hours_since_last_maintenance=hours_since_last_maint,
            previous_component_failure_count=prev_comp_failures,
            running_hours_7d=running_7d,
            running_hours_30d=running_30d,
            running_hours_90d=running_90d,
            utilization_trend_7d_vs_30d=utilization_trend,
            maintenance_count_30d=maint_count_30d,
            maintenance_count_90d=maint_count_90d,
            has_delayed_maintenance=has_delayed,
            delayed_maintenance_count=delayed_count,
            hours_associated_with_delayed_maintenance=delayed_hours_penalty,
            previous_failures_component=prev_comp_failures,
            previous_failures_vehicle_component_type=prev_v_ctype_failures,
            days_since_previous_failure=days_since_prev_fail,
            hours_since_previous_failure=hours_since_prev_fail,
            associated_part_numbers=assoc_part_numbers,
            part_usage_30d=usage_30d,
            part_usage_90d=usage_90d,
            min_stock_on_hand=min_stock,
            total_stock_on_hand=tot_stock,
            total_stock_on_order=tot_order,
            total_stock_allocated=tot_alloc,
            max_supplier_lead_time_days=max_lead,
            min_supplier_reliability=min_rel
        )
        feature_vectors.append(vec)
        
    return FleetFeatureSet(
        prediction_timestamp=prediction_timestamp,
        vehicle_count=len(vehicles_by_id),
        component_count=len(feature_vectors),
        features=feature_vectors
    )
