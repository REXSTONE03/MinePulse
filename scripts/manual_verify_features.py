import os
import sys
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal, DEFAULT_DB_PATH
from backend.app.database.models import Vehicle, VehicleTelemetry, Component, Failure, PartUsage, Part
from backend.app.services.features import generate_features

def run_manual_verification():
    db = SessionLocal()
    prediction_timestamp = "2025-06-01"
    print(f"--- MANUAL FEATURE VERIFICATION FOR T = {prediction_timestamp} ---")
    
    fleet_features = generate_features(db, prediction_timestamp)
    print(f"Total Active Components Extracted: {fleet_features.component_count}")
    
    # Inspect first 3 component feature vectors
    for i, f in enumerate(fleet_features.features[:3]):
        print(f"\n================ COMPONENT {i+1} ================")
        print(f"Component ID: {f.component_id} | Vehicle ID: {f.vehicle_id} | Type: {f.component_type} ({f.vehicle_model})")
        print(f"Component Age Hours: {f.component_age_hours:.1f} hrs | Component Age Days: {f.component_age_days:.1f} days")
        print(f"Hours Since Install: {f.hours_since_component_installation:.1f} hrs | Hours Since Last Maintenance: {f.hours_since_last_maintenance:.1f} hrs")
        print(f"Previous Component Failures: {f.previous_component_failure_count} | Vehicle/Comp-Type Failures: {f.previous_failures_vehicle_component_type}")
        print(f"7d Run Hours: {f.running_hours_7d:.1f} | 30d Run Hours: {f.running_hours_30d:.1f} | 90d Run Hours: {f.running_hours_90d:.1f}")
        print(f"Utilization Trend (7d/30d): {f.utilization_trend_7d_vs_30d:.4f}")
        print(f"Delayed Maintenance Count: {f.delayed_maintenance_count} | Penalty Hours: {f.hours_associated_with_delayed_maintenance:.1f}")
        print(f"Part Usages (30d): {f.part_usage_30d} | (90d): {f.part_usage_90d}")
        print(f"Min Stock: {f.min_stock_on_hand} | Total Stock: {f.total_stock_on_hand} | Lead Time: {f.max_supplier_lead_time_days} days | Reliability: {f.min_supplier_reliability:.2f}")
        
        # Raw Database Verification for Component 1
        if i == 0:
            print("\n--- RAW SQLITE DIRECT AUDIT COMPARISON ---")
            # 1. Telemetry audit
            tel_T = db.query(VehicleTelemetry).filter(VehicleTelemetry.vehicle_id == f.vehicle_id, VehicleTelemetry.date <= prediction_timestamp).order_by(VehicleTelemetry.date.desc()).first()
            tel_30 = db.query(VehicleTelemetry).filter(VehicleTelemetry.vehicle_id == f.vehicle_id, VehicleTelemetry.date <= "2025-05-02").order_by(VehicleTelemetry.date.desc()).first()
            
            raw_hours_T = tel_T.operating_hours if tel_T else 0.0
            raw_hours_30 = tel_30.operating_hours if tel_30 else 0.0
            expected_30d_run = round(raw_hours_T - raw_hours_30, 1)
            
            print(f"Raw DB Telemetry at T (2025-06-01): {raw_hours_T:.1f} hrs")
            print(f"Raw DB Telemetry at T-30d (2025-05-02): {raw_hours_30:.1f} hrs")
            print(f"Calculated 30d Run Hours: {expected_30d_run:.1f} hrs | Feature Vector Value: {f.running_hours_30d:.1f} hrs")
            assert f.running_hours_30d == expected_30d_run, "30d Running hours discrepancy!"
            
            # 2. Raw failures audit
            raw_comp_fails = db.query(Failure).filter(Failure.component_id == f.component_id, Failure.failure_date <= prediction_timestamp).count()
            print(f"Raw DB Failures for Comp {f.component_id} <= T: {raw_comp_fails} | Feature Vector Value: {f.previous_component_failure_count}")
            assert f.previous_component_failure_count == raw_comp_fails, "Component failure count discrepancy!"
            
            print(">>> RAW SQLITE AUDIT MATCHED 100% PERFECTLY! <<<")
            
    db.close()

if __name__ == "__main__":
    run_manual_verification()
