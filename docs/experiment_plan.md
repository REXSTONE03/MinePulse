# MinePulse AI — Experimental Plan & Testing Strategy

This document details the counterfactual evaluation framework, baseline definitions, experimental registry structure, and statistical reporting requirements.

---

## 1. Counterfactual Evaluation Design

To ensure a scientifically rigorous and fair comparison, MinePulse AI and the comparison baselines are evaluated counterfactually against the exact same test sequence.

```
                    +---------------------------------------+
                    |       Synthetic Fleet Event Stream    |
                    | (Identical failures, PM events, lead  |
                    |  time delays, and operating hours)    |
                    +-------------------+-------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
                 v                                             v
+-------------------------------+             +-------------------------------+
|      Baseline Policy          |             |     MinePulse AI Policy       |
|  (Reactive / Hist. Average)   |             |  (Predictive Cost-Optimized)  |
+-------------------------------+             +-------------------------------+
                 |                                             |
                 v                                             v
+-------------------------------+             +-------------------------------+
|      Simulated Downtime       |             |      Simulated Downtime       |
|    (Baseline downtime hours)  |             |    (MinePulse downtime hours) |
+-------------------------------+             +-------------------------------+
```

Both policies face:
1. The same stochastic component failures occurring on the same days.
2. The same scheduled preventive maintenance dates.
3. The same randomized supplier lead-time delays drawn from log-normal distributions.
4. The same initial inventory state.

---

## 2. Evaluation Baselines

We compare MinePulse AI against three distinct baseline policies:

* **Baseline A (Historical Average)**:
  Reorder points are set based on historical average demand during the lead-time window. Safety stock remains static.
* **Baseline B (Maintenance-Only Demand)**:
  Orders are placed strictly to cover scheduled maintenance plans. No safety stock is held for stochastic component failures.
* **Baseline C (Reactive Ordering Policy)**:
  Safety stock is zero. Parts are ordered only after a failure occurs or on the day scheduled maintenance begins. This represents the absolute minimum inventory footprint.

---

## 3. Reproducible Experiment Registry

To ensure full reproducibility, every experiment run is documented in an experiment registry. The registry schema stores:

```json
{
  "experiment_id": "EXP-2026-001",
  "dataset_version": "synth_ds_v1.0",
  "random_seed": 42,
  "splits": {
    "training_start_day": 1,
    "training_end_day": 360,
    "validation_start_day": 361,
    "validation_end_day": 540,
    "test_start_day": 541,
    "test_end_day": 720
  },
  "models": {
    "failure_risk_model": "RandomForest_v1.0",
    "demand_model": "NegativeBinomial_ModelSelection_v1.0"
  },
  "configurations": {
    "forecast_horizon_days": 14,
    "confidence_level_alpha": 0.80,
    "baseline_policy": "Baseline_C_Reactive"
  }
}
```

Registry files are stored as JSON in `data/experiments/registry.json`. Output results (metrics) are stored separately under the matching `experiment_id`.

---

## 4. Statistical Reporting & Metrics

The back-test comparison reports:
1. **Primary Business Metric**: Vehicle-hours of parts-unavailability downtime.
2. **Secondary Metrics**:
   * Stockout events.
   * Emergency orders placed.
   * Total carrying/holding cost.
   * Overstock quantity.
   * Forecast Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).
   * Predictive interval coverage (empirical P50, P80, P95 coverage) and average interval width.
   * ML classifier diagnostics: Precision, Recall, F1-score, and ROC-AUC.
3. **Statistical Uncertainty around Results**:
   We will compute **95% bootstrapped confidence intervals** for the primary metric (downtime hours reduction) by resampling vehicles with replacement over 1,000 bootstrap iterations, reporting the 2.5th and 97.5th percentiles of downtime savings.
