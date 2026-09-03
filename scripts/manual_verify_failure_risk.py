import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal
from backend.app.services.failure_risk import (
    fit_weibull_parameters, predict_component_failure_risk, evaluate_failure_risk_backtest
)

def run_manual_sanity_check():
    db = SessionLocal()
    prediction_timestamp = "2025-06-01"
    print(f"=== FAILURE RISK PREDICTION MANUAL SANITY CHECK (T = {prediction_timestamp}) ===")
    
    # 1. Inspect fitted Weibull parameters at T
    params = fit_weibull_parameters(db, prediction_timestamp)
    print("\n--- FITTED WEIBULL & CATASTROPHIC PARAMETERS (<= 2025-06-01) ---")
    for ctype, p in params.items():
        print(f"Component Type: {ctype:15s} | Beta: {p.beta:.4f} | Eta: {p.eta:7.1f} hrs | Lambda_Cat: {p.lambda_cat:.6f} | Wear Fails: {p.wearout_samples_count:2d} | Exposure: {p.total_exposure_hours:.1f} hrs")
        
    # 2. Inspect sample component risk predictions
    report = predict_component_failure_risk(db, prediction_timestamp, fitted_params=params)
    print(f"\nTotal Component Risk Predictions Generated: {report.component_count}")
    
    print("\n--- SAMPLE COMPONENT PREDICTIONS ---")
    for pred in report.predictions[:5]:
        print(f"Vehicle {pred.vehicle_id:2d} | Comp {pred.component_id:3d} ({pred.component_type:13s}) | Age: {pred.component_age_hours:6.1f} hrs | Util: {pred.daily_utilization_hours:4.1f} h/d")
        print(f"  Probs -> 7d: {pred.failure_probability_7d:.4f} | 30d: {pred.failure_probability_30d:.4f} | 60d: {pred.failure_probability_60d:.4f} | 90d: {pred.failure_probability_90d:.4f}")
        print(f"  Baseline 30d: {pred.baseline_failure_probability_30d:.4f} | Wearout 30d: {pred.wearout_component_prob_30d:.4f} | Shock 30d: {pred.catastrophic_component_prob_30d:.4f}")
        print(f"  Risk Tier: [{pred.risk_level}]")
        print("-" * 75)

    # 3. Perform Temporal Backtesting Evaluation
    print("\n=== TEMPORAL BACKTESTING EVALUATION ===")
    print("Training Period: <= 2025-06-01 | Test Period: 2025-06-01 to 2025-12-31 | Horizon: 30 Days")
    backtest = evaluate_failure_risk_backtest(
        db, 
        train_end_timestamp="2025-06-01", 
        test_start_timestamp="2025-06-01", 
        test_end_timestamp="2025-12-31",
        horizon_days=30
    )
    
    print(f"\nEvaluated Observations (Component-Date pairs): {backtest.sample_count}")
    print(f"Weibull Competing-Risk Model Brier Score: {backtest.weibull_brier_score:.4f} | Baseline Brier Score: {backtest.baseline_brier_score:.4f}")
    print(f"Weibull Model MAE: {backtest.weibull_mae:.4f} | Baseline MAE: {backtest.baseline_mae:.4f}")
    print(f"Weibull Model Log-Loss: {backtest.weibull_log_loss:.4f} | Baseline Log-Loss: {backtest.baseline_log_loss:.4f}")
    print(f"\nClassification Metrics (P >= 0.25): TP={backtest.true_positives}, FP={backtest.false_positives}, TN={backtest.true_negatives}, FN={backtest.false_negatives}")
    print(f"Precision: {backtest.precision:.4f} | Recall: {backtest.recall:.4f} | F1 Score: {backtest.f1_score:.4f}")
    
    print("\n--- CALIBRATION ANALYSIS (30-day Horizon) ---")
    for b in backtest.calibration_bins:
        print(f"  Bin {b['bin_range']:10s} | Samples: {b['sample_count']:4d} | Mean Predicted Prob: {b['mean_predicted_probability']:.4f} | Observed Failure Rate: {b['observed_failure_rate']:.4f}")
        
    db.close()

if __name__ == "__main__":
    run_manual_sanity_check()
