import os
import sys
import sqlite3
import json
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal, DEFAULT_DB_PATH
from backend.app.database.models import (
    Vehicle, VehicleTelemetry, Component, Supplier, Part,
    Inventory, InventoryLedger, MaintenanceTemplate, MaintenancePlan,
    Failure, PartUsage, PurchaseOrder, ModelGovernance, Recommendation,
    Override, AuditLog, ExperimentRegistry
)
from backend.app.services.snapshot import get_feature_snapshot

def parse_date(d_str):
    return datetime.strptime(d_str, "%Y-%m-%d")

def run_audit():
    db = SessionLocal()
    print("Database path:", DEFAULT_DB_PATH)
    
    # 1. SCENARIO VERIFICATION
    print("\n--- 1. SCENARIO VERIFICATION ---")
    
    # Failures scenarios
    normal_wear = db.query(Failure).filter(Failure.scenario_id == 'SCENARIO_NORMAL_WEAR').count()
    cat_failures = db.query(Failure).filter(Failure.scenario_id == 'SCENARIO_CATASTROPHIC_FAILURE').count()
    sparse_history = db.query(Failure).filter(Failure.scenario_id == 'SCENARIO_SPARSE_HISTORY').count()
    
    print(f"NORMAL_WEAR Failure Count: {normal_wear}")
    print(f"CATASTROPHIC_FAILURE Failure Count: {cat_failures}")
    print(f"SPARSE_HISTORY Failure Count: {sparse_history}")
    
    # Supplier delays
    print("\nSupplier Delays:")
    all_undercarriage_orders = db.query(PurchaseOrder).join(Part).join(Supplier)\
        .filter(Supplier.name == "Heavy Undercarriage Ltd").all()
        
    for po in all_undercarriage_orders:
        order_dt = parse_date(po.order_date)
        delivery_dt = parse_date(po.actual_delivery_date) if po.actual_delivery_date else parse_date(po.expected_delivery_date)
        actual_lead = (delivery_dt - order_dt).days
        if actual_lead > po.part.supplier.base_lead_time_days * 3:
            print(f" - Supplier: {po.part.supplier.name}")
            print(f"   Part: {po.part.part_number} ({po.part.name})")
            print(f"   Order Date: {po.order_date}")
            print(f"   Base Lead Time: {po.part.supplier.base_lead_time_days} days")
            print(f"   Disrupted Lead Time: {actual_lead} days")
            print(f"   Actual Delivery Date: {po.actual_delivery_date}")
        
    # Maintenance rescheduling
    rescheduled_plans = db.query(MaintenancePlan).filter(MaintenancePlan.original_scheduled_date != None).all()
    print(f"\nRescheduled Maintenance Plans Count: {len(rescheduled_plans)}")
    if rescheduled_plans:
        # Show first 3 examples
        for p in rescheduled_plans[:3]:
            print(f" - Plan ID: {p.id}")
            print(f"   Original Scheduled: {p.original_scheduled_date}")
            print(f"   New Scheduled: {p.scheduled_date}")
            print(f"   Reason: {p.rescheduled_reason}")
            print(f"   Change Timestamp: {p.rescheduled_timestamp}")

    # 2. TEMPORAL LEAKAGE DEMONSTRATION
    print("\n--- 2. TEMPORAL LEAKAGE DEMONSTRATION ---")
    T = "2025-06-01"
    print(f"Generating snapshot as of prediction timestamp T: {T}")
    snapshot = get_feature_snapshot(db, T)
    
    # Future Failures
    future_failures_in_db = db.query(Failure).filter(Failure.failure_date > T).count()
    failures_in_snap_after_T = sum(1 for f in snapshot["failures"] if f["failure_date"] > T)
    leakage_failures = "FAIL" if failures_in_snap_after_T > 0 else "PASS"
    print(f"Future Failures in DB: {future_failures_in_db} | In Snapshot: {failures_in_snap_after_T} -> {leakage_failures}")
    
    # Future Usages
    future_usages_in_db = db.query(PartUsage).filter(PartUsage.usage_date > T).count()
    usages_in_snap_after_T = sum(1 for u in snapshot["part_usage"] if u["usage_date"] > T)
    leakage_usages = "FAIL" if usages_in_snap_after_T > 0 else "PASS"
    print(f"Future Part Usages in DB: {future_usages_in_db} | In Snapshot: {usages_in_snap_after_T} -> {leakage_usages}")
    
    # Future Maintenance Completion
    future_completed_maint_in_db = db.query(MaintenancePlan)\
        .join(PartUsage, MaintenancePlan.id == PartUsage.maintenance_plan_id)\
        .filter(PartUsage.usage_date > T).count()
    completed_plans_in_snap_after_T = sum(1 for p in snapshot["maintenance_plans"] if p["status"] == "COMPLETED" and any(
        u.usage_date > T for u in db.query(PartUsage).filter(PartUsage.maintenance_plan_id == p["id"]).all()
    ))
    leakage_maint = "FAIL" if completed_plans_in_snap_after_T > 0 else "PASS"
    print(f"Future Maint Completion in DB: {future_completed_maint_in_db} | Completed in Snapshot: {completed_plans_in_snap_after_T} -> {leakage_maint}")
    
    # Future Telemetry
    future_tel_in_db = db.query(VehicleTelemetry).filter(VehicleTelemetry.date > T).count()
    # Check if any vehicle hours in snapshot > max telemetry on/before T
    leakage_tel = "PASS"
    for v in snapshot["vehicles"]:
        db_hours_at_T = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == v["id"], VehicleTelemetry.date <= T)\
            .order_by(VehicleTelemetry.date.desc()).first()
        expected = db_hours_at_T.operating_hours if db_hours_at_T else 0.0
        if v["operating_hours"] > expected:
            leakage_tel = "FAIL"
    print(f"Future Telemetry in DB: {future_tel_in_db} | Snapshot Verification: {leakage_tel}")
    
    # Future Inventory Changes
    future_ledger_in_db = db.query(InventoryLedger).filter(InventoryLedger.date > T).count()
    # Check if stock on hand at T contains any future ledger updates
    leakage_inventory = "PASS"
    for inv in snapshot["inventory"]:
        p_id = inv["part_id"]
        actual_val = db.query(func.sum(InventoryLedger.quantity))\
            .filter(InventoryLedger.part_id == p_id, InventoryLedger.date <= T).scalar() or 0
        if inv["stock_on_hand"] != max(0, actual_val):
            leakage_inventory = "FAIL"
    print(f"Future Ledger Entries in DB: {future_ledger_in_db} | Snapshot Stock Verification: {leakage_inventory}")

    # 3. CAUSAL RELATIONSHIPS
    print("\n--- 3. CAUSAL RELATIONSHIPS ---")
    
    # A. Component wear vs failure rate
    # Group failures by component operating hours at failure
    ages = [f.operating_hours - c.operating_hours_at_install for f, c in db.query(Failure, Component).filter(Failure.component_id == Component.id).all()]
    if ages:
        quartiles = np.percentile(ages, [25, 50, 75])
        print(f"Component hours at Failure - Min: {min(ages):.1f} | 25%: {quartiles[0]:.1f} | 50% (Median): {quartiles[1]:.1f} | 75%: {quartiles[2]:.1f} | Max: {max(ages):.1f}")
        # Failure counts by age groups
        low_age = sum(1 for a in ages if a < 1000)
        med_age = sum(1 for a in ages if 1000 <= a < 2500)
        high_age = sum(1 for a in ages if 2500 <= a < 4000)
        very_high_age = sum(1 for a in ages if a >= 4000)
        print(f"Failures by Component age: <1000 hrs: {low_age} | 1000-2500 hrs: {med_age} | 2500-4000 hrs: {high_age} | >=4000 hrs: {very_high_age}")
    
    # B. Maintenance events vs Maintenance part usage
    maint_usages = db.query(PartUsage).filter(PartUsage.maintenance_plan_id != None).count()
    completed_plans = db.query(MaintenancePlan).filter(MaintenancePlan.status == 'COMPLETED').count()
    print(f"Completed Maintenance Plans: {completed_plans} | Maintenance Part Usage Records: {maint_usages}")
    
    # C. Failures vs Failure part usage
    failure_usages = db.query(PartUsage).filter(PartUsage.failure_id != None).count()
    resolved_failures = db.query(Failure).filter(Failure.resolved == True).count()
    print(f"Resolved Failures: {resolved_failures} | Failure Part Usage Records: {failure_usages}")
    
    # D. Supplier lead time vs delivery timing
    pos = db.query(PurchaseOrder).filter(PurchaseOrder.status == 'DELIVERED').all()
    delays = []
    for po in pos:
        order_dt = parse_date(po.order_date)
        delivery_dt = parse_date(po.actual_delivery_date)
        delays.append((delivery_dt - order_dt).days)
    if delays:
        print(f"Simulated Delivery Times - Min: {min(delays)} | Avg: {np.mean(delays):.2f} days | Max: {max(delays)}")

    # 4. PART-USAGE INTEGRITY
    print("\n--- 4. PART-USAGE INTEGRITY ---")
    maint_use = db.query(PartUsage).filter(PartUsage.maintenance_plan_id != None, PartUsage.failure_id == None).count()
    fail_use = db.query(PartUsage).filter(PartUsage.failure_id != None, PartUsage.maintenance_plan_id == None).count()
    neither_use = db.query(PartUsage).filter(PartUsage.maintenance_plan_id == None, PartUsage.failure_id == None).count()
    both_use = db.query(PartUsage).filter(PartUsage.maintenance_plan_id != None, PartUsage.failure_id != None).count()
    
    print(f"Maintenance-only usages: {maint_use}")
    print(f"Failure-only usages: {fail_use}")
    print(f"Neither source usages: {neither_use} (Expected: 0)")
    print(f"Linked to both sources: {both_use} (Expected: 0)")

    # 5. INVENTORY DATA
    print("\n--- 5. INVENTORY DATA ---")
    num_parts = db.query(Part).count()
    parts_with_inv = db.query(Inventory).count()
    
    min_stock_violations = 0
    for inv in db.query(Inventory).all():
        part = db.query(Part).filter(Part.id == inv.part_id).first()
        if part and inv.stock_on_hand < part.min_stock_level:
            min_stock_violations += 1
            
    negative_stock = db.query(Inventory).filter(Inventory.stock_on_hand < 0).count()
    negative_qty = db.query(PartUsage).filter(PartUsage.quantity < 0).count()
    
    print(f"Parts Catalog: {num_parts} | Parts with Inventory rows: {parts_with_inv}")
    print(f"Min Stock Violations: {min_stock_violations}")
    print(f"Negative Stock Records: {negative_stock} (Expected: 0)")
    print(f"Negative Quantity Usages: {negative_qty} (Expected: 0)")

    # 7. SCHEMA VERIFICATION
    print("\n--- 7. SCHEMA VERIFICATION ---")
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()
    
    print("Database Tables in SQLite:")
    for t in sorted(tables):
        print(f" - {t}")

    db.close()

if __name__ == "__main__":
    from sqlalchemy import func
    run_audit()
