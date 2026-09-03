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
from backend.app.services.failure_risk import (
    fit_weibull_parameters, predict_component_failure_risk, evaluate_failure_risk_backtest,
    FleetFailureRiskReport, ComponentFailureRiskPrediction, WeibullParameters
)
from scripts.generate_synthetic_data import generate_data

class TestFailureRisk(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = "test_minepulse_failure_risk.db"
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
            
        cls.engine = create_engine(f"sqlite:///{cls.db_path}")
        Base.metadata.create_all(bind=cls.engine)
        
        Session = sessionmaker(bind=cls.engine)
        session = Session()
        try:
            print("Generating test dataset for failure risk prediction tests...")
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

    def test_01_valid_probability_bounds(self):
        """Test 1: Model produces valid probabilities between 0 and 1."""
        t = "2025-06-01"
        report = predict_component_failure_risk(self.session, t)
        
        self.assertIsInstance(report, FleetFailureRiskReport)
        self.assertGreater(len(report.predictions), 0)
        
        for p in report.predictions:
            self.assertGreaterEqual(p.failure_probability_7d, 0.0)
            self.assertLessEqual(p.failure_probability_7d, 1.0)
            self.assertGreaterEqual(p.failure_probability_30d, 0.0)
            self.assertLessEqual(p.failure_probability_30d, 1.0)
            self.assertGreaterEqual(p.failure_probability_60d, 0.0)
            self.assertLessEqual(p.failure_probability_60d, 1.0)
            self.assertGreaterEqual(p.failure_probability_90d, 0.0)
            self.assertLessEqual(p.failure_probability_90d, 1.0)
            self.assertIn(p.risk_level, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    def test_02_determinism(self):
        """Test 2: Predictions are deterministic."""
        t = "2025-06-01"
        run1 = predict_component_failure_risk(self.session, t)
        run2 = predict_component_failure_risk(self.session, t)
        
        self.assertEqual(len(run1.predictions), len(run2.predictions))
        for p1, p2 in zip(run1.predictions, run2.predictions):
            self.assertEqual(p1.to_dict(), p2.to_dict())

    def test_03_wearout_hazard_monotonicity(self):
        """Test 3: Older/worn components have higher conditional wearout hazard than younger components of the same type."""
        t = "2026-01-01"
        report = predict_component_failure_risk(self.session, t)
        
        # Filter components by type e.g. ENGINE
        engine_preds = [p for p in report.predictions if p.component_type == "ENGINE"]
        self.assertGreater(len(engine_preds), 1)
        
        # Sort by component_age_hours
        engine_preds.sort(key=lambda p: p.component_age_hours)
        youngest = engine_preds[0]
        oldest = engine_preds[-1]
        
        # Older component must have higher wearout conditional failure probability over 30d
        self.assertGreater(oldest.wearout_component_prob_30d, youngest.wearout_component_prob_30d)

    def test_04_horizon_monotonicity(self):
        """Test 4: 7/30/60/90-day probabilities are mathematically consistent/non-decreasing."""
        t = "2025-06-01"
        report = predict_component_failure_risk(self.session, t)
        
        for p in report.predictions:
            self.assertLessEqual(p.failure_probability_7d, p.failure_probability_30d)
            self.assertLessEqual(p.failure_probability_30d, p.failure_probability_60d)
            self.assertLessEqual(p.failure_probability_60d, p.failure_probability_90d)

    def test_05_future_failures_isolation(self):
        """Test 5: Future failures (> T) cannot influence predictions or fitted parameters at T."""
        t = "2025-06-01"
        baseline_report = predict_component_failure_risk(self.session, t)
        baseline_params = fit_weibull_parameters(self.session, t)
        
        # Inject future wear failure at 2029-12-31
        future_fail = Failure(
            vehicle_id=1,
            component_id=1,
            failure_date="2029-12-31",
            operating_hours=99999.0,
            severity="MINOR",
            resolved=False,
            scenario_id="SCENARIO_NORMAL_WEAR"
        )
        self.session.add(future_fail)
        self.session.commit()
        
        try:
            new_report = predict_component_failure_risk(self.session, t)
            new_params = fit_weibull_parameters(self.session, t)
            
            # Fitted parameters at T must be identical
            for ctype in baseline_params:
                self.assertEqual(baseline_params[ctype].to_dict(), new_params[ctype].to_dict())
                
            # Predictions at T must be identical
            for p1, p2 in zip(baseline_report.predictions, new_report.predictions):
                self.assertEqual(p1.to_dict(), p2.to_dict())
        finally:
            self.session.delete(future_fail)
            self.session.commit()

    def test_06_future_telemetry_isolation(self):
        """Test 6: Future telemetry (> T) cannot influence predictions at T."""
        t = "2025-06-01"
        baseline_report = predict_component_failure_risk(self.session, t)
        
        # Inject future telemetry at 2029-12-31
        future_tel = VehicleTelemetry(
            vehicle_id=1,
            date="2029-12-31",
            operating_hours=99999.9
        )
        self.session.add(future_tel)
        self.session.commit()
        
        try:
            new_report = predict_component_failure_risk(self.session, t)
            for p1, p2 in zip(baseline_report.predictions, new_report.predictions):
                self.assertEqual(p1.to_dict(), p2.to_dict())
        finally:
            self.session.delete(future_tel)
            self.session.commit()

    def test_07_component_replacement_reset(self):
        """Test 7: Component replacement resets wearout hazard to new component's age."""
        t = "2026-01-01"
        report = predict_component_failure_risk(self.session, t)
        
        # Find a replaced component (installed after start date 2025-01-01)
        replaced_preds = [p for p in report.predictions if p.component_age_hours < 1000.0]
        self.assertGreater(len(replaced_preds), 0)
        
        for p in replaced_preds:
            # Component age hours is reset to low value
            self.assertLess(p.component_age_hours, 1000.0)
            # Wearout probability for 30d should be low for young component
            self.assertLess(p.wearout_component_prob_30d, 0.15)

    def test_08_catastrophic_failure_separation(self):
        """Test 8: Catastrophic failures are modeled independently via lambda_cat."""
        t = "2025-06-01"
        params = fit_weibull_parameters(self.session, t)
        
        for ctype, p in params.items():
            self.assertGreater(p.lambda_cat, 0.0)
            self.assertIsInstance(p.beta, float)
            self.assertIsInstance(p.eta, float)

    def test_09_exposure_isolation(self):
        """Test 9: Changing/removing future operating exposure after T cannot change fitted lambda_cat at T (USER CORRECTION 6)."""
        t = "2025-06-01"
        params_before = fit_weibull_parameters(self.session, t)
        
        # Add future telemetry rows after T that accumulate thousands of exposure hours
        fut_tels = [
            VehicleTelemetry(vehicle_id=v_id, date="2029-12-31", operating_hours=99999.0)
            for v_id in range(1, 10)
        ]
        self.session.add_all(fut_tels)
        self.session.commit()
        
        try:
            params_after = fit_weibull_parameters(self.session, t)
            for ctype in params_before:
                self.assertEqual(params_before[ctype].lambda_cat, params_after[ctype].lambda_cat)
                self.assertEqual(params_before[ctype].total_exposure_hours, params_after[ctype].total_exposure_hours)
        finally:
            for ft in fut_tels:
                self.session.delete(ft)
            self.session.commit()

    def test_10_edge_case_safety(self):
        """Test 10: Missing/edge-case historical data on early dates (Day 1) is handled safely."""
        t_day1 = "2025-01-01"
        report = predict_component_failure_risk(self.session, t_day1)
        
        self.assertEqual(report.prediction_timestamp, t_day1)
        for p in report.predictions:
            self.assertGreaterEqual(p.failure_probability_7d, 0.0)
            self.assertLessEqual(p.failure_probability_90d, 1.0)
            self.assertIn(p.risk_level, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

if __name__ == "__main__":
    unittest.main()
