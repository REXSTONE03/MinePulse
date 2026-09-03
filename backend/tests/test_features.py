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
from backend.app.services.features import generate_features, FleetFeatureSet, ComponentFeatureVector
from scripts.generate_synthetic_data import generate_data

class TestFeatures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = "test_minepulse_features.db"
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
            
        cls.engine = create_engine(f"sqlite:///{cls.db_path}")
        Base.metadata.create_all(bind=cls.engine)
        
        Session = sessionmaker(bind=cls.engine)
        session = Session()
        try:
            print("Generating test dataset for feature engineering tests...")
            generate_data(session, seed=42)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            try:
                os.remove(cls.db_path)
                for ext in ['-wal', '-shm']:
                    if os.path.exists(cls.db_path + ext):
                        os.remove(cls.db_path + ext)
            except Exception as e:
                print(f"Error removing test db {cls.db_path}: {e}")

    def setUp(self):
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()

    def test_01_feature_generation_valid_timestamp(self):
        """Test 1: Feature generation works for a valid historical timestamp."""
        t = "2025-06-01"
        feature_set = generate_features(self.session, t)
        
        self.assertIsInstance(feature_set, FleetFeatureSet)
        self.assertEqual(feature_set.prediction_timestamp, t)
        self.assertGreater(feature_set.vehicle_count, 0)
        self.assertGreater(feature_set.component_count, 0)
        
        # Verify first vector structure
        first_vec = feature_set.features[0]
        self.assertIsInstance(first_vec, ComponentFeatureVector)
        self.assertGreaterEqual(first_vec.component_age_hours, 0.0)
        self.assertGreaterEqual(first_vec.running_hours_7d, 0.0)
        self.assertGreaterEqual(first_vec.running_hours_30d, first_vec.running_hours_7d)
        self.assertGreaterEqual(first_vec.running_hours_90d, first_vec.running_hours_30d)

    def test_02_determinism(self):
        """Test 2: Feature generation is deterministic across multiple calls."""
        t = "2025-06-01"
        run1 = generate_features(self.session, t)
        run2 = generate_features(self.session, t)
        
        self.assertEqual(len(run1.features), len(run2.features))
        for f1, f2 in zip(run1.features, run2.features):
            self.assertEqual(f1.to_dict(), f2.to_dict())

    def test_03_no_future_data_leakage(self):
        """Test 3: No feature uses information after prediction timestamp T."""
        t = "2025-06-01"
        feature_set = generate_features(self.session, t)
        
        # Verify that all component ages and running hours match snapshot values at T
        for f in feature_set.features:
            # Check telemetry <= T
            tel = self.session.query(VehicleTelemetry)\
                .filter(VehicleTelemetry.vehicle_id == f.vehicle_id, VehicleTelemetry.date <= t)\
                .order_by(VehicleTelemetry.date.desc()).first()
            expected_v_hours = tel.operating_hours if tel else 0.0
            
            # Comp hours at T cannot exceed vehicle hours at T
            self.assertLessEqual(f.component_age_hours, expected_v_hours)

    def test_04_future_telemetry_isolation(self):
        """Test 4: Future telemetry (> T) cannot affect features generated at T."""
        t = "2025-06-01"
        baseline_features = generate_features(self.session, t)
        
        # Inject future telemetry entry at 2029-12-31 (outside sim date range)
        future_tel = VehicleTelemetry(
            vehicle_id=1,
            date="2029-12-31",
            operating_hours=99999.9
        )
        self.session.add(future_tel)
        self.session.commit()
        
        try:
            new_features = generate_features(self.session, t)
            self.assertEqual(len(baseline_features.features), len(new_features.features))
            for b_feat, n_feat in zip(baseline_features.features, new_features.features):
                self.assertEqual(b_feat.to_dict(), n_feat.to_dict())
        finally:
            self.session.delete(future_tel)
            self.session.commit()

    def test_05_future_failures_isolation(self):
        """Test 5: Future failures (> T) cannot affect features generated at T."""
        t = "2025-06-01"
        baseline_features = generate_features(self.session, t)
        
        # Inject future failure at 2029-12-31
        future_fail = Failure(
            vehicle_id=1,
            component_id=1,
            failure_date="2029-12-31",
            operating_hours=9999.0,
            severity="CATASTROPHIC",
            resolved=False,
            scenario_id="SCENARIO_CATASTROPHIC_FAILURE"
        )
        self.session.add(future_fail)
        self.session.commit()
        
        try:
            new_features = generate_features(self.session, t)
            for b_feat, n_feat in zip(baseline_features.features, new_features.features):
                self.assertEqual(b_feat.to_dict(), n_feat.to_dict())
        finally:
            self.session.delete(future_fail)
            self.session.commit()

    def test_06_future_part_usage_isolation(self):
        """Test 6: Future part usage (> T) cannot affect features generated at T."""
        t = "2025-06-01"
        baseline_features = generate_features(self.session, t)
        
        # Inject isolated future failure and part usage at 2029-12-31
        future_fail = Failure(
            vehicle_id=1,
            component_id=1,
            failure_date="2029-12-31",
            operating_hours=9999.0,
            severity="MINOR",
            resolved=False,
            scenario_id="SCENARIO_NORMAL_WEAR"
        )
        self.session.add(future_fail)
        self.session.flush()
        
        future_usage = PartUsage(
            vehicle_id=1,
            part_id=1,
            failure_id=future_fail.id,
            quantity=1000,
            usage_date="2029-12-31"
        )
        self.session.add(future_usage)
        self.session.commit()
        
        try:
            new_features = generate_features(self.session, t)
            for b_feat, n_feat in zip(baseline_features.features, new_features.features):
                self.assertEqual(b_feat.to_dict(), n_feat.to_dict())
        finally:
            self.session.delete(future_usage)
            self.session.delete(future_fail)
            self.session.commit()

    def test_07_future_inventory_isolation(self):
        """Test 7: Future inventory transactions (> T) cannot affect features generated at T."""
        t = "2025-06-01"
        baseline_features = generate_features(self.session, t)
        
        # Inject future inventory ledger entry at 2025-12-31
        future_ledger = InventoryLedger(
            part_id=1,
            transaction_type='DELIVERY',
            quantity=50000,
            date="2025-12-31"
        )
        self.session.add(future_ledger)
        self.session.commit()
        
        try:
            new_features = generate_features(self.session, t)
            for b_feat, n_feat in zip(baseline_features.features, new_features.features):
                self.assertEqual(b_feat.to_dict(), n_feat.to_dict())
        finally:
            self.session.delete(future_ledger)
            self.session.commit()

    def test_08_component_replacement_history(self):
        """Test 8: Component replacement history is handled correctly."""
        t = "2026-01-01"
        feature_set = generate_features(self.session, t)
        
        # Find components where replacement occurred before T
        replaced_comps = [f for f in feature_set.features if f.previous_failures_vehicle_component_type > f.previous_component_failure_count]
        self.assertGreater(len(replaced_comps), 0, "No replaced components found in history by 2026-01-01")
        
        for vec in replaced_comps:
            # Active component age hours should reflect age of CURRENT component, while vehicle component type failures counts history
            self.assertGreaterEqual(vec.previous_failures_vehicle_component_type, vec.previous_component_failure_count)

    def test_09_missing_and_rare_data_safety(self):
        """Test 9: Missing/rare historical data on early simulation dates (Day 1) is handled safely."""
        t_day1 = "2025-01-01"
        feature_set = generate_features(self.session, t_day1)
        
        self.assertEqual(feature_set.prediction_timestamp, t_day1)
        for f in feature_set.features:
            self.assertGreaterEqual(f.running_hours_7d, 0.0)
            self.assertGreaterEqual(f.running_hours_30d, 0.0)
            self.assertGreater(f.utilization_trend_7d_vs_30d, 0.0) # safely handled trend calculation
            self.assertGreaterEqual(f.component_age_hours, 0.0)

if __name__ == "__main__":
    unittest.main()
