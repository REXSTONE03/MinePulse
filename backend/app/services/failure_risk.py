import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database.models import (
    Vehicle, VehicleTelemetry, Component, Failure, PartUsage,
    MaintenancePlan, Part, InventoryLedger, PurchaseOrder, MaintenanceTemplate
)
from backend.app.services.snapshot import get_feature_snapshot, parse_date
from backend.app.services.features import generate_features, FleetFeatureSet, ComponentFeatureVector

@dataclass
class WeibullParameters:
    """
    Fitted Weibull & Catastrophic parameters for a component type at a given prediction timestamp.
    All parameters derive strictly from historical failures and operating exposure <= max_timestamp.
    """
    component_type: str
    beta: float                  # Weibull shape parameter (wearout rate)
    eta: float                   # Weibull scale parameter (characteristic life in hours)
    lambda_cat: float            # Catastrophic shock failure rate (shocks per operating hour)
    wearout_samples_count: int   # Count of normal wear failures <= T used for fitting
    catastrophic_samples_count: int # Count of catastrophic failures <= T used for fitting
    total_exposure_hours: float  # Cumulative component operating exposure hours <= T

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class ComponentFailureRiskPrediction:
    """
    Failure risk prediction vector for a single active component.
    """
    vehicle_id: int
    component_id: int
    component_type: str
    vehicle_model: str
    prediction_timestamp: str
    component_age_hours: float
    daily_utilization_hours: float
    
    # Conditional failure probabilities across horizons
    failure_probability_7d: float
    failure_probability_30d: float
    failure_probability_60d: float
    failure_probability_90d: float
    
    # Baseline comparison (Constant Hazard Model)
    baseline_failure_probability_30d: float
    
    # Wearout vs Catastrophic breakdown for 30d
    wearout_component_prob_30d: float
    catastrophic_component_prob_30d: float
    
    # Risk Level Tier (LOW, MEDIUM, HIGH, CRITICAL based on 30d prob)
    risk_level: str
    
    # Model Metadata
    fitted_beta: float
    fitted_eta: float
    fitted_lambda_cat: float

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class FleetFailureRiskReport:
    """
    Container for fleet-wide failure risk predictions and fitted parameters at timestamp T.
    """
    prediction_timestamp: str
    vehicle_count: int
    component_count: int
    parameters_by_type: Dict[str, dict]
    predictions: List[ComponentFailureRiskPrediction]

    def to_dict(self) -> dict:
        return {
            "prediction_timestamp": self.prediction_timestamp,
            "vehicle_count": self.vehicle_count,
            "component_count": self.component_count,
            "parameters_by_type": self.parameters_by_type,
            "predictions": [p.to_dict() for p in self.predictions]
        }

@dataclass
class BacktestEvaluationReport:
    """
    Structured metrics from temporal backtesting evaluation.
    """
    train_end_timestamp: str
    test_start_timestamp: str
    test_end_timestamp: str
    eval_horizon_days: int
    sample_count: int
    
    # Weibull Competing-Risks Model Metrics
    weibull_brier_score: float
    weibull_mae: float
    weibull_log_loss: float
    
    # Baseline Constant-Hazard Model Metrics
    baseline_brier_score: float
    baseline_mae: float
    baseline_log_loss: float
    
    # Calibration Analysis (Observed vs Predicted Failure Rate by Bins)
    calibration_bins: List[dict]
    
    # Confusion Matrix at High/Critical Risk Threshold (P >= 0.25)
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float

    def to_dict(self) -> dict:
        return asdict(self)

# Default priors per component type used when historical wear failures <= T are sparse (< 5)
DEFAULT_WEIBULL_PRIORS = {
    "ENGINE": {"beta": 2.8, "eta": 5000.0, "default_cat_rate": 0.00002},
    "TRANSMISSION": {"beta": 2.5, "eta": 4500.0, "default_cat_rate": 0.00002},
    "HYDRAULICS": {"beta": 2.2, "eta": 4000.0, "default_cat_rate": 0.00002},
    "UNDERCARRIAGE": {"beta": 2.0, "eta": 3500.0, "default_cat_rate": 0.00002}
}

def estimate_weibull_mle(ages: List[float], prior_beta: float, prior_eta: float) -> Tuple[float, float]:
    """
    Estimates Weibull shape (beta) and scale (eta) on observed wearout failure ages using Newton-Raphson MLE or Method of Moments.
    """
    if len(ages) < 5:
        return prior_beta, prior_eta
        
    arr = np.array(ages, dtype=float)
    arr = arr[arr > 0]
    if len(arr) < 5:
        return prior_beta, prior_eta
        
    # Method of Moments initial estimate
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else mean * 0.3
    if std <= 0 or mean <= 0:
        return prior_beta, prior_eta
        
    cv = std / mean
    # Approximation for Weibull beta from CV: beta ~ cv^(-1.086)
    beta_est = max(1.0, float(cv ** (-1.086)))
    eta_est = max(100.0, float(mean / math.gamma(1.0 + 1.0 / beta_est)))
    
    # Simple MLE refinement via grid search around estimate
    best_beta, best_eta = beta_est, eta_est
    min_nll = float("inf")
    
    beta_candidates = np.linspace(max(1.0, beta_est * 0.5), beta_est * 1.5, 20)
    for b in beta_candidates:
        # For given beta, MLE for eta is (mean(arr^beta))^(1/beta)
        e = float(np.mean(arr ** b) ** (1.0 / b))
        if e <= 0:
            continue
        # Negative Log-Likelihood
        nll = -len(arr) * math.log(b) + len(arr) * b * math.log(e) - (b - 1) * np.sum(np.log(arr)) + np.sum((arr / e) ** b)
        if nll < min_nll:
            min_nll = nll
            best_beta, best_eta = float(b), float(e)
            
    return round(best_beta, 4), round(best_eta, 2)

def fit_weibull_parameters(db: Session, max_timestamp: str) -> Dict[str, WeibullParameters]:
    """
    Fits Weibull shape (beta), scale (eta), and catastrophic shock rate (lambda_cat) per component type.
    ENFORCES STRICT TEMPORAL BOUNDARY: Uses ONLY failures and operating exposure <= max_timestamp.
    """
    component_types = ["ENGINE", "TRANSMISSION", "HYDRAULICS", "UNDERCARRIAGE"]
    params_result: Dict[str, WeibullParameters] = {}
    
    # 1. Calculate cumulative operating hours exposure for components up to max_timestamp
    # For every component installed <= max_timestamp, find its operating hours accumulated at or before max_timestamp
    comps = db.query(Component).filter(Component.installed_date <= max_timestamp).all()
    
    exposure_by_type: Dict[str, float] = {ctype: 0.0 for ctype in component_types}
    
    for c in comps:
        # Find telemetry of vehicle at max_timestamp
        tel = db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == c.vehicle_id, VehicleTelemetry.date <= max_timestamp)\
            .order_by(VehicleTelemetry.date.desc()).first()
        v_hours_at_T = tel.operating_hours if tel else c.operating_hours_at_install
        
        # Check if component failed or was replaced at or before max_timestamp
        fail = db.query(Failure)\
            .filter(Failure.component_id == c.id, Failure.failure_date <= max_timestamp)\
            .first()
            
        if fail:
            # Exposure was up to failure operating hours
            c_hours_at_T = max(0.0, fail.operating_hours - c.operating_hours_at_install)
        else:
            c_hours_at_T = max(0.0, v_hours_at_T - c.operating_hours_at_install)
            
        if c.type in exposure_by_type:
            exposure_by_type[c.type] += c_hours_at_T

    # 2. Fit parameters per component type using failures <= max_timestamp
    for ctype in component_types:
        prior = DEFAULT_WEIBULL_PRIORS.get(ctype, {"beta": 2.0, "eta": 4000.0, "default_cat_rate": 0.00002})
        
        # Fetch wearout failures <= max_timestamp
        wear_failures = db.query(Failure).join(Component)\
            .filter(
                Component.type == ctype,
                Failure.failure_date <= max_timestamp,
                Failure.scenario_id == 'SCENARIO_NORMAL_WEAR'
            ).all()
            
        # Fetch catastrophic failures <= max_timestamp
        cat_failures = db.query(Failure).join(Component)\
            .filter(
                Component.type == ctype,
                Failure.failure_date <= max_timestamp,
                Failure.scenario_id == 'SCENARIO_CATASTROPHIC_FAILURE'
            ).all()
            
        wear_ages = []
        for f in wear_failures:
            c_inst = f.component
            age_at_fail = f.operating_hours - c_inst.operating_hours_at_install if c_inst else f.operating_hours
            if age_at_fail > 0:
                wear_ages.append(age_at_fail)
                
        beta, eta = estimate_weibull_mle(wear_ages, prior["beta"], prior["eta"])
        
        tot_exp = exposure_by_type.get(ctype, 0.0)
        n_cat = len(cat_failures)
        
        if tot_exp > 1000.0 and n_cat > 0:
            lambda_cat = float(n_cat / tot_exp)
        else:
            lambda_cat = prior["default_cat_rate"]
            
        params_result[ctype] = WeibullParameters(
            component_type=ctype,
            beta=beta,
            eta=eta,
            lambda_cat=lambda_cat,
            wearout_samples_count=len(wear_ages),
            catastrophic_samples_count=n_cat,
            total_exposure_hours=tot_exp
        )
        
    return params_result

def predict_component_failure_risk(
    db: Session, 
    prediction_timestamp: str, 
    snapshot: Optional[dict] = None,
    fitted_params: Optional[Dict[str, WeibullParameters]] = None
) -> FleetFailureRiskReport:
    """
    Generates failure risk predictions across 7, 30, 60, and 90-day horizons for all active components.
    Uses Weibull competing-risks formula with zero temporal leakage.
    """
    if snapshot is None:
        snapshot = get_feature_snapshot(db, prediction_timestamp)
        
    if fitted_params is None:
        fitted_params = fit_weibull_parameters(db, prediction_timestamp)
        
    feature_set = generate_features(db, prediction_timestamp, snapshot=snapshot)
    
    predictions: List[ComponentFailureRiskPrediction] = []
    
    for feat in feature_set.features:
        ctype = feat.component_type
        params = fitted_params.get(ctype, WeibullParameters(ctype, 2.0, 4000.0, 0.00002, 0, 0, 0.0))
        
        beta = params.beta
        eta = params.eta
        lambda_cat = params.lambda_cat
        
        # Calculate daily utilization rate u (hrs/day)
        u = feat.running_hours_30d / 30.0
        if u <= 0.01:
            u = 14.0 # default operational utilization
            
        x = feat.component_age_hours
        
        # Horizons in days
        horizons_days = [7, 30, 60, 90]
        probs = {}
        wear_probs = {}
        cat_probs = {}
        
        for H in horizons_days:
            u_H = u * H  # Operating hours added in H days
            
            # Weibull conditional cumulative hazard: H_wear = ((x + u*H) / eta)^beta - (x / eta)^beta
            h_wear = ((x + u_H) / eta) ** beta - (x / eta) ** beta
            h_cat = lambda_cat * u_H
            
            # Competing risks probability: P_failure(H) = 1 - exp(-H_wear - lambda_cat * u * H)
            p_fail = 1.0 - math.exp(-h_wear - h_cat)
            p_fail = max(0.0, min(0.9999, p_fail))
            
            probs[H] = round(p_fail, 4)
            wear_probs[H] = round(1.0 - math.exp(-h_wear), 4)
            cat_probs[H] = round(1.0 - math.exp(-h_cat), 4)

        # Baseline Constant Hazard Model P_base(30d)
        # Baseline hazard rate lambda_base = total_failures / total_exposure
        tot_fails = params.wearout_samples_count + params.catastrophic_samples_count
        if params.total_exposure_hours > 0 and tot_fails > 0:
            lambda_base = tot_fails / params.total_exposure_hours
        else:
            lambda_base = 0.0001
            
        p_base_30 = 1.0 - math.exp(-lambda_base * u * 30.0)
        p_base_30 = round(max(0.0, min(0.9999, p_base_30)), 4)

        # Risk Classification Tier based on 30-day failure probability
        p30 = probs[30]
        if p30 < 0.10:
            risk_tier = "LOW"
        elif p30 < 0.25:
            risk_tier = "MEDIUM"
        elif p30 < 0.50:
            risk_tier = "HIGH"
        else:
            risk_tier = "CRITICAL"
            
        pred = ComponentFailureRiskPrediction(
            vehicle_id=feat.vehicle_id,
            component_id=feat.component_id,
            component_type=ctype,
            vehicle_model=feat.vehicle_model,
            prediction_timestamp=prediction_timestamp,
            component_age_hours=x,
            daily_utilization_hours=round(u, 2),
            failure_probability_7d=probs[7],
            failure_probability_30d=probs[30],
            failure_probability_60d=probs[60],
            failure_probability_90d=probs[90],
            baseline_failure_probability_30d=p_base_30,
            wearout_component_prob_30d=wear_probs[30],
            catastrophic_component_prob_30d=cat_probs[30],
            risk_level=risk_tier,
            fitted_beta=beta,
            fitted_eta=eta,
            fitted_lambda_cat=lambda_cat
        )
        predictions.append(pred)
        
    return FleetFailureRiskReport(
        prediction_timestamp=prediction_timestamp,
        vehicle_count=feature_set.vehicle_count,
        component_count=len(predictions),
        parameters_by_type={ctype: p.to_dict() for ctype, p in fitted_params.items()},
        predictions=predictions
    )

def evaluate_failure_risk_backtest(
    db: Session,
    train_end_timestamp: str,
    test_start_timestamp: str,
    test_end_timestamp: str,
    horizon_days: int = 30
) -> BacktestEvaluationReport:
    """
    Evaluates failure risk predictions using temporal backtesting.
    Parameters are fit STRICTLY on data <= train_end_timestamp.
    Predictions are evaluated on actual future failure occurrences within horizon_days.
    """
    # 1. Fit parameters strictly on training set <= train_end_timestamp
    train_params = fit_weibull_parameters(db, train_end_timestamp)
    
    # Select test prediction dates spaced e.g. every 14 days in [test_start, test_end]
    start_dt = parse_date(test_start_timestamp)
    end_dt = parse_date(test_end_timestamp)
    
    current_dt = start_dt
    test_timestamps = []
    while current_dt <= end_dt:
        test_timestamps.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=14)
        
    weibull_preds = []
    baseline_preds = []
    actual_labels = []
    
    for t_str in test_timestamps:
        t_dt = parse_date(t_str)
        t_horizon_end = (t_dt + timedelta(days=horizon_days)).strftime("%Y-%m-%d")
        
        report = predict_component_failure_risk(db, t_str, fitted_params=train_params)
        
        for pred in report.predictions:
            # Ground truth: Did this vehicle & component fail in interval (t_str, t_horizon_end]?
            fail_count = db.query(Failure)\
                .filter(
                    Failure.vehicle_id == pred.vehicle_id,
                    Failure.component_id == pred.component_id,
                    Failure.failure_date > t_str,
                    Failure.failure_date <= t_horizon_end
                ).count()
                
            label = 1 if fail_count > 0 else 0
            
            p_w = pred.failure_probability_30d if horizon_days == 30 else pred.failure_probability_7d
            p_b = pred.baseline_failure_probability_30d
            
            weibull_preds.append(p_w)
            baseline_preds.append(p_b)
            actual_labels.append(label)
            
    n = len(actual_labels)
    if n == 0:
        return BacktestEvaluationReport(
            train_end_timestamp, test_start_timestamp, test_end_timestamp, horizon_days, 0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, [], 0, 0, 0, 0, 0.0, 0.0, 0.0
        )
        
    y_true = np.array(actual_labels, dtype=float)
    p_w = np.array(weibull_preds, dtype=float)
    p_b = np.array(baseline_preds, dtype=float)
    
    # Brier Scores
    w_brier = float(np.mean((p_w - y_true) ** 2))
    b_brier = float(np.mean((p_b - y_true) ** 2))
    
    # MAE
    w_mae = float(np.mean(np.abs(p_w - y_true)))
    b_mae = float(np.mean(np.abs(p_b - y_true)))
    
    # Log Loss with clipping
    eps = 1e-15
    p_w_clip = np.clip(p_w, eps, 1 - eps)
    p_b_clip = np.clip(p_b, eps, 1 - eps)
    
    w_log_loss = float(-np.mean(y_true * np.log(p_w_clip) + (1 - y_true) * np.log(1 - p_w_clip)))
    b_log_loss = float(-np.mean(y_true * np.log(p_b_clip) + (1 - y_true) * np.log(1 - p_b_clip)))
    
    # Confusion matrix at threshold P >= 0.25 (HIGH / CRITICAL risk)
    high_risk_pred = (p_w >= 0.25).astype(int)
    tp = int(np.sum((high_risk_pred == 1) & (y_true == 1)))
    fp = int(np.sum((high_risk_pred == 1) & (y_true == 0)))
    tn = int(np.sum((high_risk_pred == 0) & (y_true == 0)))
    fn = int(np.sum((high_risk_pred == 0) & (y_true == 1)))
    
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    
    # Calibration bins ([0, 0.1], [0.1, 0.25], [0.25, 0.5], [0.5, 1.0])
    bin_edges = [0.0, 0.10, 0.25, 0.50, 1.0]
    calibration_bins = []
    
    for low, high in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (p_w >= low) & (p_w < high) if high < 1.0 else (p_w >= low) & (p_w <= high)
        bin_count = int(np.sum(mask))
        if bin_count > 0:
            mean_pred = float(np.mean(p_w[mask]))
            obs_freq = float(np.mean(y_true[mask]))
        else:
            mean_pred = 0.0
            obs_freq = 0.0
            
        calibration_bins.append({
            "bin_range": f"{low:.2f}-{high:.2f}",
            "sample_count": bin_count,
            "mean_predicted_probability": round(mean_pred, 4),
            "observed_failure_rate": round(obs_freq, 4)
        })
        
    return BacktestEvaluationReport(
        train_end_timestamp=train_end_timestamp,
        test_start_timestamp=test_start_timestamp,
        test_end_timestamp=test_end_timestamp,
        eval_horizon_days=horizon_days,
        sample_count=n,
        weibull_brier_score=round(w_brier, 4),
        weibull_mae=round(w_mae, 4),
        weibull_log_loss=round(w_log_loss, 4),
        baseline_brier_score=round(b_brier, 4),
        baseline_mae=round(b_mae, 4),
        baseline_log_loss=round(b_log_loss, 4),
        calibration_bins=calibration_bins,
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4)
    )
