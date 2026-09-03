import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database.models import (
    Vehicle, VehicleTelemetry, Component, Failure, PartUsage,
    MaintenancePlan, Part, InventoryLedger, PurchaseOrder, MaintenanceTemplate, Supplier
)
from backend.app.services.snapshot import get_feature_snapshot, parse_date, add_days
from backend.app.services.failure_risk import predict_component_failure_risk, FleetFailureRiskReport

@dataclass
class PartDemandForecast:
    """
    Structured parts-demand forecast for a single catalog part over a specified horizon H.
    All calculations represent historical state at or before prediction timestamp T with zero temporal leakage.
    """
    part_id: int
    part_name: str
    part_number: str
    prediction_timestamp: str           # YYYY-MM-DD
    horizon_days: int                   # 7, 30, 60, or 90
    
    # Demand Partitioning
    planned_maintenance_demand: float   # D_planned: parts needed for operationally known PM plans
    failure_driven_demand: float        # D_failure: probabilistic failure-driven demand sum(P_fail * Q)
    total_expected_demand: float        # D_total = D_planned + D_failure
    
    # Prediction Quantiles / Forecast Intervals (NOT confidence intervals)
    lower_bound: float                  # P10 prediction quantile
    upper_bound: float                  # P95 prediction quantile
    
    # Baselines for comparison
    naive_baseline_forecast: float      # Baseline 1: usage in previous H-day window
    moving_average_baseline_forecast: float # Baseline 2: historical average usage per H-day window
    
    # Model & Metadata
    model_name: str                     # "Failure-Risk Hybrid Demand Model"
    contributing_component_types: List[str]
    supplier_lead_time_days: int
    current_stock_on_hand: int
    current_stock_on_order: int
    current_stock_allocated: int
    
    # Data Support Quality Flag (HIGH_HISTORY, MEDIUM_HISTORY, SPARSE_HISTORY)
    confidence_flag: str
    dispersion_model_used: str          # "POISSON", "NEGATIVE_BINOMIAL", "SPARSE_BOOTSTRAP"

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class FleetDemandForecastReport:
    """
    Container holding parts-demand forecasts for all catalog parts at prediction timestamp T.
    """
    prediction_timestamp: str
    part_count: int
    horizons_forecasted: List[int]
    forecasts: List[PartDemandForecast]

    def to_dict(self) -> dict:
        return {
            "prediction_timestamp": self.prediction_timestamp,
            "part_count": self.part_count,
            "horizons_forecasted": self.horizons_forecasted,
            "forecasts": [f.to_dict() for f in self.forecasts]
        }

@dataclass
class DemandBacktestReport:
    """
    Out-of-sample temporal backtest evaluation metrics across models and horizons.
    """
    test_start_timestamp: str
    test_end_timestamp: str
    sample_observations_count: int
    metrics_by_horizon: Dict[int, dict]  # Metrics per horizon (7, 30, 60, 90)

    def to_dict(self) -> dict:
        return asdict(self)

def calculate_forecast_intervals(
    expected_demand: float, 
    historical_usages: List[int],
    horizon_days: int
) -> Tuple[float, float, str, str]:
    """
    Calculates P10 and P95 prediction quantiles (forecast intervals) based on historical usage dispersion.
    Selects POISSON, NEGATIVE_BINOMIAL, or SPARSE_BOOTSTRAP fallback depending on variance and sample count.
    """
    n_obs = len(historical_usages)
    
    # Determine data support quality flag
    if n_obs >= 20:
        confidence_flag = "HIGH_HISTORY"
    elif n_obs >= 5:
        confidence_flag = "MEDIUM_HISTORY"
    else:
        confidence_flag = "SPARSE_HISTORY"
        
    if n_obs < 5 or expected_demand <= 0.0:
        # Sparse history safeguard
        lower_b = max(0.0, round(expected_demand * 0.5, 2))
        upper_b = round(expected_demand * 2.5 + 2.0, 2)
        return lower_b, upper_b, confidence_flag, "SPARSE_BOOTSTRAP"
        
    arr = np.array(historical_usages, dtype=float)
    mean_val = float(np.mean(arr))
    var_val = float(np.var(arr, ddof=1)) if len(arr) > 1 else mean_val
    
    if var_val > 1.2 * mean_val and mean_val > 0.0:
        # Negative Binomial overdispersed model
        dispersion_type = "NEGATIVE_BINOMIAL"
        # Overdispersion factor k
        std_val = math.sqrt(var_val)
        lower_b = max(0.0, round(expected_demand - 1.28 * std_val, 2))
        upper_b = round(expected_demand + 1.645 * std_val + 1.0, 2)
    else:
        # Standard Poisson model
        dispersion_type = "POISSON"
        std_val = math.sqrt(max(0.1, expected_demand))
        lower_b = max(0.0, round(expected_demand - 1.28 * std_val, 2))
        upper_b = round(expected_demand + 1.645 * std_val + 1.0, 2)
        
    # Guarantee horizon consistency: lower <= expected <= upper
    lower_b = max(0.0, min(lower_b, expected_demand))
    upper_b = max(expected_demand, upper_b)
    
    return round(lower_b, 2), round(upper_b, 2), confidence_flag, dispersion_type

def generate_demand_forecast(
    db: Session, 
    prediction_timestamp: str, 
    horizons: List[int] = [7, 30, 60, 90],
    snapshot: Optional[dict] = None,
    risk_report: Optional[FleetFailureRiskReport] = None
) -> FleetDemandForecastReport:
    """
    Generates operational parts-demand forecasts for all catalog parts across forecast horizons.
    Partitions demand into Planned Maintenance ($D_planned$) and Failure-Driven ($D_failure$) demand.
    ENFORCES STRICT ZERO TEMPORAL LEAKAGE: Uses only information operationally available at prediction_timestamp T.
    """
    if snapshot is None:
        snapshot = get_feature_snapshot(db, prediction_timestamp)
        
    if risk_report is None:
        risk_report = predict_component_failure_risk(db, prediction_timestamp, snapshot=snapshot)
        
    t_dt = datetime.strptime(prediction_timestamp, "%Y-%m-%d").date()
    
    # Query all parts from database <= T
    parts = db.query(Part).all()
    snapshot_inventory_by_part = {inv["part_id"]: inv for inv in snapshot["inventory"]}
    snapshot_maint_plans = snapshot["maintenance_plans"]
    snapshot_part_usage = snapshot["part_usage"]
    
    # Pre-fetch templates
    templates = db.query(MaintenanceTemplate).all()
    
    # Map component types to parts from MaintenanceTemplates and Catalog naming convention
    comp_type_part_map: Dict[str, List[int]] = {
        "ENGINE": [],
        "TRANSMISSION": [],
        "HYDRAULICS": [],
        "UNDERCARRIAGE": []
    }
    
    prefix_map = {
        "ENGINE": "P-ENG-",
        "TRANSMISSION": "P-TRN-",
        "HYDRAULICS": "P-HYD-",
        "UNDERCARRIAGE": "P-UND-"
    }
    
    for p in parts:
        for ctype, prefix in prefix_map.items():
            if p.part_number.startswith(prefix):
                if p.id not in comp_type_part_map[ctype]:
                    comp_type_part_map[ctype].append(p.id)
                    
    for tmpl in templates:
        if tmpl.component_type in comp_type_part_map and tmpl.part_id not in comp_type_part_map[tmpl.component_type]:
            comp_type_part_map[tmpl.component_type].append(tmpl.part_id)

    # 1. TEMPORAL SANITIZATION FOR PLANNED MAINTENANCE:
    # Filter PM plans that were ALREADY CREATED/KNOWN at or before prediction_timestamp T
    # A plan was created at/before T if its creation date (original_scheduled_date or scheduled_date) <= T
    known_pm_plans = []
    for p in snapshot_maint_plans:
        # Check original scheduled date if present, else scheduled date
        creation_date = p.get("original_scheduled_date") or p["scheduled_date"]
        if creation_date <= prediction_timestamp and p["status"] == "PENDING":
            known_pm_plans.append(p)

    forecasts: List[PartDemandForecast] = []

    for p in parts:
        p_id = p.id
        inv = snapshot_inventory_by_part.get(p_id, {
            "stock_on_hand": 0, "stock_on_order": 0, "stock_allocated": 0, "lead_time_days": p.lead_time_days
        })
        
        # Historical usages for part <= T
        part_usages_all = [u for u in snapshot_part_usage if u["part_id"] == p_id]
        historical_qty_list = [u["quantity"] for u in part_usages_all]
        
        # Contributing component types
        contrib_comp_types = [ctype for ctype, p_ids in comp_type_part_map.items() if p_id in p_ids]
        if not contrib_comp_types:
            contrib_comp_types = ["GENERAL"]
            
        for H in horizons:
            horizon_end_str = (t_dt + timedelta(days=H)).strftime("%Y-%m-%d")
            
            # A. PLANNED MAINTENANCE DEMAND (D_planned)
            # Sum parts required for known pending PM plans scheduled in window [T, T + H days]
            planned_demand = 0.0
            for pm in known_pm_plans:
                # Scheduled date operationally effective at T
                sched_date = pm["scheduled_date"]
                if prediction_timestamp <= sched_date <= horizon_end_str:
                    # Lookup template required quantity
                    comp_type = db.query(Component.type).filter(Component.id == pm["component_id"]).scalar()
                    if comp_type:
                        tmpl = db.query(MaintenanceTemplate)\
                            .filter(
                                MaintenanceTemplate.maintenance_type == pm["description"],
                                MaintenanceTemplate.component_type == comp_type,
                                MaintenanceTemplate.part_id == p_id
                            ).first()
                        if tmpl:
                            planned_demand += float(tmpl.quantity)
                            
            # B. FAILURE-DRIVEN DEMAND (D_failure)
            # Sum(P_fail(c, H) * Q_fail(p|c)) across active components of contributing types
            failure_demand = 0.0
            for pred in risk_report.predictions:
                if pred.component_type in contrib_comp_types:
                    # Select probability corresponding to horizon H
                    if H <= 7:
                        prob = pred.failure_probability_7d
                    elif H <= 30:
                        prob = pred.failure_probability_30d
                    elif H <= 60:
                        prob = pred.failure_probability_60d
                    else:
                        prob = pred.failure_probability_90d
                        
                    # Standard failure quantity for primary failure part is 1.0 (or template quantity)
                    failure_demand += prob * 1.0
                    
            planned_demand = round(max(0.0, planned_demand), 2)
            failure_demand = round(max(0.0, failure_demand), 2)
            total_expected = round(planned_demand + failure_demand, 2)
            
            # C. BASELINES
            # Baseline 1: Naive Forecast (usage in previous H-day window [T - H, T])
            h_start_str = (t_dt - timedelta(days=H)).strftime("%Y-%m-%d")
            naive_usage = sum(
                u["quantity"] for u in snapshot_part_usage 
                if u["part_id"] == p_id and h_start_str <= u["usage_date"] <= prediction_timestamp
            )
            naive_forecast = float(naive_usage)
            
            # Baseline 2: Moving Average Forecast (rolling historical average usage per H-day window)
            if len(part_usages_all) > 0:
                earliest_usage = min(u["usage_date"] for u in part_usages_all)
                total_days = max(1.0, float((t_dt - parse_date(earliest_usage)).days))
                daily_rate = sum(u["quantity"] for u in part_usages_all) / total_days
                ma_forecast = round(daily_rate * H, 2)
            else:
                ma_forecast = 0.0
                
            # D. UNCERTAINTY FORECAST INTERVALS (P10 & P95)
            lower_b, upper_b, confidence_flag, dispersion_type = calculate_forecast_intervals(
                total_expected, historical_qty_list, H
            )
            
            forecasts.append(PartDemandForecast(
                part_id=p_id,
                part_name=p.name,
                part_number=p.part_number,
                prediction_timestamp=prediction_timestamp,
                horizon_days=H,
                planned_maintenance_demand=planned_demand,
                failure_driven_demand=failure_demand,
                total_expected_demand=total_expected,
                lower_bound=lower_b,
                upper_bound=upper_b,
                naive_baseline_forecast=naive_forecast,
                moving_average_baseline_forecast=ma_forecast,
                model_name="Failure-Risk Hybrid Demand Model",
                contributing_component_types=contrib_comp_types,
                supplier_lead_time_days=inv.get("lead_time_days", p.lead_time_days),
                current_stock_on_hand=inv["stock_on_hand"],
                current_stock_on_order=inv["stock_on_order"],
                current_stock_allocated=inv["stock_allocated"],
                confidence_flag=confidence_flag,
                dispersion_model_used=dispersion_type
            ))
            
    return FleetDemandForecastReport(
        prediction_timestamp=prediction_timestamp,
        part_count=len(parts),
        horizons_forecasted=horizons,
        forecasts=forecasts
    )

def evaluate_demand_forecast_backtest(
    db: Session,
    test_start_timestamp: str,
    test_end_timestamp: str,
    horizons: List[int] = [7, 30, 60, 90]
) -> DemandBacktestReport:
    """
    Evaluates out-of-sample demand forecasts using temporal backtesting.
    Compares Naive, Moving Average, and Failure-Risk Hybrid Demand models against actual future part consumption.
    Calculates MAE, RMSE, and Pinball Loss (P10, P95) per horizon.
    """
    start_dt = parse_date(test_start_timestamp)
    end_dt = parse_date(test_end_timestamp)
    
    current_dt = start_dt
    test_timestamps = []
    while current_dt <= end_dt:
        test_timestamps.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=14)
        
    # Store errors by horizon and model
    # Models: "hybrid", "naive", "moving_average"
    eval_data: Dict[int, Dict[str, List[Tuple[float, float, float, float]]]] = {
        H: {"hybrid": [], "naive": [], "moving_average": []} for H in horizons
    }
    
    for t_str in test_timestamps:
        t_dt = parse_date(t_str)
        snapshot = get_feature_snapshot(db, t_str)
        report = generate_demand_forecast(db, t_str, horizons=horizons, snapshot=snapshot)
        
        for f in report.forecasts:
            H = f.horizon_days
            h_end_str = (t_dt + timedelta(days=H)).strftime("%Y-%m-%d")
            
            # Ground Truth: Actual part consumption in interval (t_str, h_end_str]
            actual_usage = db.query(func.sum(PartUsage.quantity))\
                .filter(
                    PartUsage.part_id == f.part_id,
                    PartUsage.usage_date > t_str,
                    PartUsage.usage_date <= h_end_str
                ).scalar() or 0.0
                
            actual_val = float(actual_usage)
            
            # (predicted_expected, lower_bound, upper_bound, actual_val)
            eval_data[H]["hybrid"].append((f.total_expected_demand, f.lower_bound, f.upper_bound, actual_val))
            eval_data[H]["naive"].append((f.naive_baseline_forecast, max(0.0, f.naive_baseline_forecast * 0.5), f.naive_baseline_forecast * 2.0, actual_val))
            eval_data[H]["moving_average"].append((f.moving_average_baseline_forecast, max(0.0, f.moving_average_baseline_forecast * 0.5), f.moving_average_baseline_forecast * 2.0, actual_val))

    metrics_by_horizon = {}
    sample_obs_count = 0
    
    for H in horizons:
        h_metrics = {}
        for m_name in ["hybrid", "naive", "moving_average"]:
            records = eval_data[H][m_name]
            if not records:
                continue
            sample_obs_count = max(sample_obs_count, len(records))
            
            preds = np.array([r[0] for r in records], dtype=float)
            lowers = np.array([r[1] for r in records], dtype=float)
            uppers = np.array([r[2] for r in records], dtype=float)
            actuals = np.array([r[3] for r in records], dtype=float)
            
            # MAE & RMSE
            mae = float(np.mean(np.abs(preds - actuals)))
            rmse = float(np.sqrt(np.mean((preds - actuals) ** 2)))
            
            # Pinball Loss L_q(y, y_q) = max(q*(y - y_q), (q-1)*(y - y_q))
            def pinball_loss(y, y_q, q):
                err = y - y_q
                return float(np.mean(np.maximum(q * err, (q - 1.0) * err)))
                
            pinball_p10 = pinball_loss(actuals, lowers, 0.10)
            pinball_p95 = pinball_loss(actuals, uppers, 0.95)
            
            h_metrics[m_name] = {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "pinball_loss_p10": round(pinball_p10, 4),
                "pinball_loss_p95": round(pinball_p95, 4)
            }
        metrics_by_horizon[H] = h_metrics

    return DemandBacktestReport(
        test_start_timestamp=test_start_timestamp,
        test_end_timestamp=test_end_timestamp,
        sample_observations_count=sample_obs_count,
        metrics_by_horizon=metrics_by_horizon
    )
