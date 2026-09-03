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
from backend.app.services.demand_forecast import (
    generate_demand_forecast, evaluate_demand_forecast_backtest,
    FleetDemandForecastReport, PartDemandForecast
)
from scripts.generate_synthetic_data import generate_data

class TestDemandForecast(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = "test_minepulse_demand_forecast.db"
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
            
        cls.engine = create_engine(f"sqlite:///{cls.db_path}")
        Base.metadata.create_all(bind=cls.engine)
        
        Session = sessionmaker(bind=cls.engine)
        session = Session()
        try:
            print("Generating test dataset for demand forecast tests...")
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

    def test_01_valid_forecast_generation(self):
        """Test 1: Demand forecast generation succeeds for all parts across horizons 7, 30, 60, 90."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        self.assertIsInstance(report, FleetDemandForecastReport)
        self.assertEqual(report.prediction_timestamp, t)
        self.assertGreater(report.part_count, 0)
        self.assertEqual(report.horizons_forecasted, [7, 30, 60, 90])
        self.assertEqual(len(report.forecasts), report.part_count * 4)
        
        for f in report.forecasts:
            self.assertIsInstance(f, PartDemandForecast)
            self.assertIn(f.horizon_days, [7, 30, 60, 90])
            self.assertIn(f.confidence_flag, ["HIGH_HISTORY", "MEDIUM_HISTORY", "SPARSE_HISTORY"])
            self.assertIn(f.dispersion_model_used, ["POISSON", "NEGATIVE_BINOMIAL", "SPARSE_BOOTSTRAP"])

    def test_02_determinism(self):
        """Test 2: Demand forecasts are deterministic."""
        t = "2025-06-01"
        run1 = generate_demand_forecast(self.session, t)
        run2 = generate_demand_forecast(self.session, t)
        
        self.assertEqual(len(run1.forecasts), len(run2.forecasts))
        for f1, f2 in zip(run1.forecasts, run2.forecasts):
            self.assertEqual(f1.to_dict(), f2.to_dict())

    def test_03_non_negative_demand(self):
        """Test 3: Demand components (planned, failure, total) are strictly non-negative."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        for f in report.forecasts:
            self.assertGreaterEqual(f.planned_maintenance_demand, 0.0)
            self.assertGreaterEqual(f.failure_driven_demand, 0.0)
            self.assertGreaterEqual(f.total_expected_demand, 0.0)
            self.assertEqual(f.total_expected_demand, round(f.planned_maintenance_demand + f.failure_driven_demand, 2))

    def test_04_horizon_consistency(self):
        """Test 4: Demand forecasts are non-decreasing across horizons (D_7d <= D_30d <= D_60d <= D_90d)."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        # Group forecasts by part_id
        forecasts_by_part = {}
        for f in report.forecasts:
            forecasts_by_part.setdefault(f.part_id, []).append(f)
            
        for pid, f_list in forecasts_by_part.items():
            f_list.sort(key=lambda item: item.horizon_days)
            f7, f30, f60, f90 = f_list[0], f_list[1], f_list[2], f_list[3]
            
            # Planned demand horizon consistency
            self.assertLessEqual(f7.planned_maintenance_demand, f30.planned_maintenance_demand)
            self.assertLessEqual(f30.planned_maintenance_demand, f60.planned_maintenance_demand)
            self.assertLessEqual(f60.planned_maintenance_demand, f90.planned_maintenance_demand)
            
            # Total demand horizon consistency
            self.assertLessEqual(f7.total_expected_demand, f30.total_expected_demand)
            self.assertLessEqual(f30.total_expected_demand, f60.total_expected_demand)
            self.assertLessEqual(f60.total_expected_demand, f90.total_expected_demand)

    def test_05_future_usage_isolation(self):
        """Test 5: Future part usage (> T) cannot affect historical forecasts generated at T."""
        t = "2025-06-01"
        baseline_report = generate_demand_forecast(self.session, t)
        
        # Inject future usage at 2029-12-31 with valid failure reference
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
            quantity=5000,
            usage_date="2029-12-31"
        )
        self.session.add(future_usage)
        self.session.commit()
        
        try:
            new_report = generate_demand_forecast(self.session, t)
            for f1, f2 in zip(baseline_report.forecasts, new_report.forecasts):
                self.assertEqual(f1.to_dict(), f2.to_dict())
        finally:
            self.session.delete(future_usage)
            self.session.delete(future_fail)
            self.session.commit()

    def test_06_future_failures_isolation(self):
        """Test 6: Future failures (> T) cannot affect historical forecasts generated at T."""
        t = "2025-06-01"
        baseline_report = generate_demand_forecast(self.session, t)
        
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
            new_report = generate_demand_forecast(self.session, t)
            for f1, f2 in zip(baseline_report.forecasts, new_report.forecasts):
                self.assertEqual(f1.to_dict(), f2.to_dict())
        finally:
            self.session.delete(future_fail)
            self.session.commit()

    def test_07_future_maintenance_isolation(self):
        """Test 7: Future maintenance plans created/scheduled after T cannot affect forecasts at T."""
        t = "2025-06-01"
        baseline_report = generate_demand_forecast(self.session, t)
        
        # Inject future maintenance plan created & scheduled at 2029-12-31
        future_plan = MaintenancePlan(
            vehicle_id=1,
            component_id=1,
            description="PM500",
            scheduled_date="2029-12-31",
            scheduled_hours=9999.0,
            original_scheduled_date="2029-12-31",
            status="PENDING"
        )
        self.session.add(future_plan)
        self.session.commit()
        
        try:
            new_report = generate_demand_forecast(self.session, t)
            for f1, f2 in zip(baseline_report.forecasts, new_report.forecasts):
                self.assertEqual(f1.to_dict(), f2.to_dict())
        finally:
            self.session.delete(future_plan)
            self.session.commit()

    def test_08_failure_risk_incorporation(self):
        """Test 8: Failure-risk probabilities are incorporated correctly into failure-driven demand."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        # Verify that failure-driven demand is positive for parts mapped to active components
        failure_demands = [f.failure_driven_demand for f in report.forecasts if f.horizon_days == 30]
        self.assertTrue(any(fd > 0.0 for fd in failure_demands))

    def test_09_planned_maintenance_demand(self):
        """Test 9: Known pending PM plans in [T, T+H] add correctly to planned_maintenance_demand."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        # At least one part should have planned maintenance demand from known pending PM plans
        planned_demands = [f.planned_maintenance_demand for f in report.forecasts if f.horizon_days == 90]
        self.assertTrue(any(pd > 0.0 for pd in planned_demands))

    def test_10_rare_sparse_parts_safety(self):
        """Test 10: Low-frequency/sparse parts generate safe forecasts with SPARSE_HISTORY confidence flag."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        # Find rare part P-UND-407 or sparse parts P-ENG-901
        sparse_forecasts = [f for f in report.forecasts if f.part_number in ["P-UND-407", "P-ENG-901", "P-TRN-902", "P-HYD-903"]]
        self.assertGreater(len(sparse_forecasts), 0)
        
        for f in sparse_forecasts:
            self.assertEqual(f.confidence_flag, "SPARSE_HISTORY")
            self.assertEqual(f.dispersion_model_used, "SPARSE_BOOTSTRAP")
            self.assertGreaterEqual(f.lower_bound, 0.0)
            self.assertGreaterEqual(f.upper_bound, f.total_expected_demand)

    def test_11_uncertainty_bounds_validity(self):
        """Test 11: Uncertainty prediction bounds satisfy lower <= expected <= upper."""
        t = "2025-06-01"
        report = generate_demand_forecast(self.session, t)
        
        for f in report.forecasts:
            self.assertLessEqual(f.lower_bound, f.total_expected_demand)
            self.assertLessEqual(f.total_expected_demand, f.upper_bound)

if __name__ == "__main__":
    unittest.main()
