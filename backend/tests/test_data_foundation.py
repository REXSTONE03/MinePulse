import unittest
import os
import sqlite3
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.models import (
    Base, Vehicle, VehicleTelemetry, Component, Supplier, Part,
    Inventory, InventoryLedger, MaintenancePlan, Failure, PartUsage,
    PurchaseOrder, MaintenanceTemplate
)
from backend.app.services.snapshot import get_feature_snapshot
from scripts.generate_synthetic_data import generate_data

class TestDataFoundation(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # We will use temporary SQLite databases for file-based testing
        cls.db_path_42 = "test_minepulse_42.db"
        cls.db_path_42_dup = "test_minepulse_42_dup.db"
        cls.db_path_100 = "test_minepulse_100.db"
        
        # Helper function to generate data in a specific file
        def run_gen(db_path, seed):
            if os.path.exists(db_path):
                os.remove(db_path)
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)
            
            Session = sessionmaker(bind=engine)
            session = Session()
            try:
                generate_data(session, seed)
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
                
        print("Generating test databases (this may take a few seconds)...")
        run_gen(cls.db_path_42, 42)
        run_gen(cls.db_path_42_dup, 42)
        run_gen(cls.db_path_100, 100)
        
    @classmethod
    def tearDownClass(cls):
        # Remove temporary databases after tests
        for path in [cls.db_path_42, cls.db_path_42_dup, cls.db_path_100]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    for ext in ['-wal', '-shm']:
                        if os.path.exists(path + ext):
                            os.remove(path + ext)
                except Exception as e:
                    print(f"Error removing test db {path}: {e}")

    def get_session(self, db_path):
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        return Session()

    def setUp(self):
        self.session = self.get_session(self.db_path_42)

    def tearDown(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()

    def test_01_reproducibility(self):
        """Test 1: Reproducibility with same random seed."""
        session1 = self.get_session(self.db_path_42)
        session2 = self.get_session(self.db_path_42_dup)
        try:
            # Compare count of major tables
            self.assertEqual(session1.query(Vehicle).count(), session2.query(Vehicle).count())
            self.assertEqual(session1.query(Failure).count(), session2.query(Failure).count())
            self.assertEqual(session1.query(PartUsage).count(), session2.query(PartUsage).count())
            self.assertEqual(session1.query(MaintenancePlan).count(), session2.query(MaintenancePlan).count())
            self.assertEqual(session1.query(PurchaseOrder).count(), session2.query(PurchaseOrder).count())
            
            # Compare exact vehicle operating hours
            v1 = session1.query(Vehicle).order_by(Vehicle.id).all()
            v2 = session2.query(Vehicle).order_by(Vehicle.id).all()
            for idx in range(len(v1)):
                self.assertEqual(v1[idx].operating_hours, v2[idx].operating_hours)
                self.assertEqual(v1[idx].name, v2[idx].name)
                
            # Compare exact telemetry hours
            tel1 = session1.query(VehicleTelemetry).order_by(VehicleTelemetry.id).all()
            tel2 = session2.query(VehicleTelemetry).order_by(VehicleTelemetry.id).all()
            self.assertEqual(len(tel1), len(tel2))
            for idx in range(len(tel1)):
                self.assertEqual(tel1[idx].operating_hours, tel2[idx].operating_hours)
        finally:
            session1.close()
            session2.close()

    def test_02_different_outputs_with_different_seeds(self):
        """Test 2: Different output with different seed."""
        session_42 = self.get_session(self.db_path_42)
        session_100 = self.get_session(self.db_path_100)
        try:
            # Telemetry, failure counts, or downtime hours should differ
            fail_count_42 = session_42.query(Failure).count()
            fail_count_100 = session_100.query(Failure).count()
            
            self.assertNotEqual(
                (fail_count_42, session_42.query(PartUsage).count()),
                (fail_count_100, session_100.query(PartUsage).count())
            )
        finally:
            session_42.close()
            session_100.close()

    def test_03_foreign_key_integrity(self):
        """Test 3: Foreign-key integrity checks."""
        # Verify components point to existing vehicles
        for comp in self.session.query(Component).all():
            self.assertIsNotNone(self.session.query(Vehicle).filter(Vehicle.id == comp.vehicle_id).first())
            
        # Verify telemetry records point to existing vehicles
        for tel in self.session.query(VehicleTelemetry).all():
            self.assertIsNotNone(self.session.query(Vehicle).filter(Vehicle.id == tel.vehicle_id).first())
            
        # Verify part usage points to valid parts
        for use in self.session.query(PartUsage).all():
            self.assertIsNotNone(self.session.query(Part).filter(Part.id == use.part_id).first())

    def test_04_no_future_data_leakage(self):
        """Test 4: No future-data leakage (anti-leakage snapshot validation)."""
        prediction_date = "2025-06-01"
        snapshot = get_feature_snapshot(self.session, prediction_date)
        
        # A. Verify no telemetry entries exist after prediction_date
        for v in snapshot["vehicles"]:
            tel_after = self.session.query(VehicleTelemetry)\
                .filter(VehicleTelemetry.vehicle_id == v["id"], VehicleTelemetry.date > prediction_date)\
                .all()
            if tel_after:
                latest_tel_before = self.session.query(VehicleTelemetry)\
                    .filter(VehicleTelemetry.vehicle_id == v["id"], VehicleTelemetry.date <= prediction_date)\
                    .order_by(VehicleTelemetry.date.desc()).first()
                expected_hours = latest_tel_before.operating_hours if latest_tel_before else 0.0
                self.assertEqual(v["operating_hours"], expected_hours)

        # B. Verify no failures or usages after prediction_date exist in snapshot lists
        for f in snapshot["failures"]:
            self.assertTrue(f["failure_date"] <= prediction_date)
            
        for u in snapshot["part_usage"]:
            self.assertTrue(u["usage_date"] <= prediction_date)
            
        # C. Verify maintenance plans completed after T are presented as PENDING
        for p in snapshot["maintenance_plans"]:
            usages = self.session.query(PartUsage).filter(PartUsage.maintenance_plan_id == p["id"]).all()
            has_future_usages = any(u.usage_date > prediction_date for u in usages)
            if has_future_usages:
                self.assertEqual(p["status"], "PENDING")
                
        # D. Verify inventory calculations exclude ledger transactions after prediction_date
        for inv in snapshot["inventory"]:
            part_id = inv["part_id"]
            
            # Query raw SQLite database directly to get ledger sums up to prediction_date
            conn = sqlite3.connect(self.db_path_42)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sum(quantity) FROM inventory_ledger WHERE part_id = ? AND date <= ?", 
                (part_id, prediction_date)
            )
            val = cursor.fetchone()[0]
            actual_stock_on_hand_at_T = val if val is not None else 0
            conn.close()
            
            self.assertEqual(inv["stock_on_hand"], max(0, actual_stock_on_hand_at_T))

    def test_05_valid_event_ordering(self):
        """Test 5: Valid event ordering (parts consumed after failure or plan date)."""
        # Parts usage for failure must be on or after failure date
        for use in self.session.query(PartUsage).filter(PartUsage.failure_id != None).all():
            fail = self.session.query(Failure).filter(Failure.id == use.failure_id).first()
            self.assertIsNotNone(fail)
            self.assertTrue(use.usage_date >= fail.failure_date)
            
        # Parts usage for maintenance must be on or after scheduled date (or original scheduled date)
        for use in self.session.query(PartUsage).filter(PartUsage.maintenance_plan_id != None).all():
            plan = self.session.query(MaintenancePlan).filter(MaintenancePlan.id == use.maintenance_plan_id).first()
            self.assertIsNotNone(plan)
            check_date = plan.original_scheduled_date if plan.original_scheduled_date else plan.scheduled_date
            self.assertTrue(use.usage_date >= check_date)

    def test_06_maintenance_part_linkage(self):
        """Test 6: Maintenance-part template linkage."""
        # Verify that completed maintenance plans contain usages matching the template quantities
        for plan in self.session.query(MaintenancePlan).filter(MaintenancePlan.status == 'COMPLETED').all():
            comp_type = plan.component.type
            maint_type = plan.description
            
            # Fetch template
            templates = self.session.query(MaintenanceTemplate)\
                .filter(MaintenanceTemplate.maintenance_type == maint_type, MaintenanceTemplate.component_type == comp_type)\
                .all()
                
            usages = self.session.query(PartUsage).filter(PartUsage.maintenance_plan_id == plan.id).all()
            
            # Ensure every template part is represented in the usage list
            for t in templates:
                part_usage_matches = [u for u in usages if u.part_id == t.part_id]
                self.assertTrue(len(part_usage_matches) > 0)
                total_used = sum(u.quantity for u in part_usage_matches)
                self.assertEqual(total_used, t.quantity)

    def test_07_failure_part_linkage(self):
        """Test 7: Failure-part linkage."""
        # Every resolved failure must have at least one part usage record linked to it
        for fail in self.session.query(Failure).filter(Failure.resolved == True).all():
            usages = self.session.query(PartUsage).filter(PartUsage.failure_id == fail.id).all()
            self.assertTrue(len(usages) > 0)
            for u in usages:
                self.assertEqual(u.part_id, fail.part_id)
                self.assertEqual(u.vehicle_id, fail.vehicle_id)

    def test_08_inventory_validity(self):
        """Test 8: Inventory validity (no negative stock levels)."""
        for inv in self.session.query(Inventory).all():
            self.assertTrue(inv.stock_on_hand >= 0)
            self.assertTrue(inv.stock_on_order >= 0)
            self.assertTrue(inv.stock_allocated >= 0)

    def test_09_scenario_generation(self):
        """Test 9: Scenario generation verification (catastrophic scenario presence)."""
        cat_count = self.session.query(Failure).filter(Failure.scenario_id == 'SCENARIO_CATASTROPHIC_FAILURE').count()
        self.assertTrue(cat_count > 0, "No catastrophic failures were injected in synthetic data.")

    def test_10_sparse_history_scenario(self):
        """Test 10: Sparse history scenario detection."""
        sparse_count = self.session.query(Failure).filter(Failure.scenario_id == 'SCENARIO_SPARSE_HISTORY').count()
        self.assertTrue(sparse_count > 0, "No sparse history failure cases were generated.")
        
        # Verify that usages exist for sparse parts
        sparse_parts = self.session.query(Part).filter(Part.part_number.in_(['P-ENG-901', 'P-TRN-902', 'P-HYD-903'])).all()
        for p in sparse_parts:
            usages = self.session.query(PartUsage).filter(PartUsage.part_id == p.id).count()
            self.assertTrue(usages <= 12, f"Sparse part {p.part_number} has too many usage events ({usages})")

if __name__ == "__main__":
    unittest.main()
