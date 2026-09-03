# MinePulse AI: Parts-Demand Forecaster & Operational Decision-Support System

> [!IMPORTANT]
> **Synthetic Dataset & Evaluation Scope Disclaimer**
> This dataset is synthetically generated for controlled development, testing, temporal-leakage verification, and methodology demonstration. Performance on synthetic data must NOT be presented as proof of real-world mining site performance.
> **Current Status**: Phase 1–3 are complete for the current 35% milestone. Phase 4–6 remain under development.

MinePulse AI is an operational decision-support system designed to reduce vehicle downtime in mining operations caused by unavailable parts. It connects vehicle telematics, scheduled maintenance plans, historical component failures, parts usage history, and supplier lead times to predict component failure risks and parts demand under statistical uncertainty.

---

## 1. Project Overview
Mining operations depend on heavy haul trucks and excavators operating under harsh conditions. Ordering parts after component failures causes severe, avoidable vehicle downtime. MinePulse AI builds a parts-demand forecaster tied directly to planned maintenance schedules and failure-risk models to proactively ensure parts availability.

## 2. Problem Statement
Unplanned component failures lead to missing spare parts, prolonged vehicle downtime, and lost site productivity. Existing operations rely on static reorder points or reactive ordering post-failure, failing to integrate vehicle operating hours, component degradation history, and planned maintenance templates.

## 3. Proposed Solution
MinePulse AI introduces a zero-temporal-leakage predictive pipeline that:
1. Reconstructs point-in-time fleet snapshots at any historical timestamp $T$.
2. Extracts 30+ component, telemetry, maintenance, failure, and inventory features.
3. Fits Weibull competing-risks failure models to estimate 7, 30, 60, and 90-day component failure probabilities.
4. Forecasts parts demand partitioned into planned maintenance demand ($D_{\text{planned}}$) and failure-driven probabilistic demand ($D_{\text{failure}}$) with prediction quantiles ($P_{10}, P_{95}$).
5. Evaluates model accuracy using out-of-sample temporal backtesting.

## 4. Current Project Status
**Milestone**: 35% Project Completion Review  
**Status**: Phase 1–3 are complete for the current 35% milestone. Phase 4–6 remain under development.

* **Completed**:
  * Phase 1 — Architecture & Requirements
  * Phase 2 — Database Schema & Causal Data Foundation
  * Phase 3.1 — Feature Engineering Layer
  * Phase 3.2 — Failure-Risk Prediction Service
  * Phase 3.3 — Parts-Demand Forecasting Service
* **Remaining (Unstarted)**:
  * Phase 4 — Operational Decision Engine (Inventory Optimization $Q^*$)
  * Phase 5 — FastAPI REST API Gateway
  * Phase 6 — React Web Interface Dashboard

## 5. Requirement Traceability Matrix

| Capability | Implementation | Verification |
|---|---|---|
| Architecture | [`docs/architecture.md`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/docs/architecture.md) | Documentation review |
| Database | [`backend/app/database/models.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/backend/app/database/models.py) | `test_data_foundation.py` |
| Snapshot / Anti-Leakage | [`backend/app/services/snapshot.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/backend/app/services/snapshot.py) | `test_data_foundation.py` |
| Feature Engineering | [`backend/app/services/features.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/backend/app/services/features.py) | `test_features.py` |
| Failure Risk | [`backend/app/services/failure_risk.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/backend/app/services/failure_risk.py) | `test_failure_risk.py` |
| Parts Demand | [`backend/app/services/demand_forecast.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/backend/app/services/demand_forecast.py) | `test_demand_forecast.py` |
| Data Validation | [`scripts/validate_data.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/scripts/validate_data.py) | Validation result |
| Backtesting | Phase 3 services / [`scripts/manual_verify_failure_risk.py`](file:///C:/Users/vpcga/Desktop/COE%20PROJECT/scripts/manual_verify_failure_risk.py) | Backtest outputs |

---

## 6. System Architecture
The Phase 1–3 pipeline follows a modular, decoupled data flow:

```
[ SQLite Database ]
       │
       ▼
[ Point-in-Time Snapshot Engine (snapshot.py) ]
       │
       ▼
[ Feature Engineering Layer (features.py) ]
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
[ Weibull Failure-Risk Engine (failure_risk.py) ] [ Known PM Plans (snapshot) ]
       │                                         │
       └────────────────────┬────────────────────┘
                            ▼
     [ Parts-Demand Forecaster (demand_forecast.py) ]
                            │
                            ▼
             [ Temporal Backtesting Harness ]
```

---

## 7. Repository Structure

```
COE PROJECT/
├── PROJECT_STATUS.md                       # Project status & 35% evaluation milestone document
├── README.md                               # Primary system documentation
├── requirements.txt                        # Python dependencies
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   ├── models.py                   # 12 ORM models (SQLAlchemy 2.0)
│   │   │   └── session.py                  # Database connection manager
│   │   └── services/
│   │       ├── snapshot.py                 # Anti-leakage snapshot engine
│   │       ├── features.py                 # Feature engineering service
│   │       ├── failure_risk.py             # Weibull failure risk service
│   │       └── demand_forecast.py          # Parts-demand forecasting service
│   └── tests/
│       ├── test_data_foundation.py         # Database & snapshot test suite (10 tests)
│       ├── test_features.py                # Feature layer test suite (9 tests)
│       ├── test_failure_risk.py            # Failure risk test suite (10 tests)
│       └── test_demand_forecast.py         # Demand forecasting test suite (11 tests)
├── scripts/
│   ├── generate_synthetic_data.py          # Causal operations simulator (720 days)
│   ├── validate_data.py                    # Quality assurance & integrity checker
│   ├── summarize_data.py                   # Dataset summary aggregator
│   ├── audit_database.py                   # Scenario verification utility
│   └── manual_verify_failure_risk.py       # SQL manual audit & backtest script
└── docs/                                   # Architectural & mathematical specifications
```

---

## 8. Database / Data Foundation Statistics
The relational database layout (`backend/app/database/models.py`) contains 12 tables populated via the causal simulator across 720 operating days:
* **70 Vehicles** (50 CAT 797F haul trucks, 20 Komatsu excavators)
* **777 Components** (Engines, Transmissions, Hydraulics, Undercarriages)
* **39,397 Telemetry Records** (Daily operating hours tracking)
* **497 Component Failures** (Wearout degradation & catastrophic shocks)
* **6,046 Part Usage Records** (Consumption during PMs and repairs)
* **2,975 Maintenance Plans** (PM250, PM500, PM1000, PM2000 plans)
* **31 Catalog Parts** & **Inventory Ledgers**

---

## 9. Temporal Leakage Prevention
To ensure zero temporal leakage during feature generation and parameter fitting:
* The snapshot and feature-generation layers enforce point-in-time filtering, and automated tests verify that injected future telemetry, failures, maintenance, inventory, and usage do not alter historical predictions.
* Planned maintenance demand includes ONLY PM plans operationally recorded at or before prediction timestamp $T$.
* Failure risk fitting uses ONLY failure records and operating hours exposure accumulated $\le T$.

---

## 10. Feature Engineering Layer
Implemented in `backend/app/services/features.py`. Extracts 30+ point-in-time features per active component:
* **Component Metrics**: Operating age hours, installation date, operating hours since latest executed maintenance.
* **Telemetry Metrics**: 7d, 30d, 90d running hours, utilization trend ratio $\frac{\text{hours\_7d} / 7.0}{\text{hours\_30d} / 30.0}$.
* **Maintenance Penalties**: Overdue PM count, overdue wear penalty hours.
* **Failure History**: Component instance failures & vehicle component-type failures.
* **Inventory & Supplier Metrics**: Stock on hand, on order, allocated, supplier lead times, and reliability.

---

## 11. Failure-Risk Prediction Model & Results
Implemented in `backend/app/services/failure_risk.py`. Models component failures using Weibull wearout degradation ($\beta, \eta$) combined with an independent catastrophic shock rate ($\lambda_{\text{cat}}$):
$$P_{\text{failure}}(H) = 1 - \exp\left(-\left[\left(\frac{x + u H}{\eta}\right)^\beta - \left(\frac{x}{\eta}\right)^\beta\right] - \lambda_{\text{cat}} \cdot u H\right)$$

### Reported Out-of-Sample Backtest Results (June – Dec 2025 across 4,480 observations):
* **Weibull Model Brier Score**: `0.1342`
* **Constant Hazard Baseline Brier Score**: `0.0744`
* **Recall at $P \ge 0.25$**: **`58.29%`** (captures 204 out of 350 failures)
* **Precision at $P \ge 0.25$**: `10.47%`

> [!NOTE]
> **Honest Evaluation Note**: The Weibull model provides an interpretable, age-dependent wearout formulation and successfully captured 58.29% of out-of-sample failures at $P \ge 0.25$. However, it did NOT outperform the constant-hazard baseline on the overall Brier Score calibration metric (`0.1342` vs `0.0744`) due to heavy right-censoring caused by pre-emptive PM replacements in the synthetic dataset.

---

## 12. Parts-Demand Forecasting Service & Results
Implemented in `backend/app/services/demand_forecast.py`. Partitions demand into:
$$D_{\text{total}}(p, t, H) = D_{\text{planned}}(p, t, H) + D_{\text{failure}}(p, t, H)$$
* Calculates prediction quantiles ($P_{10}, P_{95}$ forecast intervals) selecting Poisson, Negative Binomial, or Sparse Bootstrap models based on historical dispersion.

### Reported Out-of-Sample Backtest Results (30-Day Horizon):
* **Failure-Risk Hybrid Model MAE**: **`3.18 units`**
* **Moving Average Baseline MAE**: `4.82 units`
* **Naive Baseline MAE**: `6.15 units`
* **Hybrid Model Pinball Loss ($P_{95}$)**: **`0.521`** (vs Moving Average `0.890`)

> [!NOTE]
> The hybrid demand model achieved lower MAE and lower Pinball Loss than both the Naive and Moving Average baselines in out-of-sample backtesting.

---

## 13. Automated Testing (40/40 Passing)
Run all 40 automated unit and integration tests across 4 test suites:

```bash
python -m pytest
```

| Test File | Test Count | Scope |
|---|---|---|
| `backend/tests/test_data_foundation.py` | 10 | Schema, snapshot anti-leakage, ledger balances, scenarios |
| `backend/tests/test_features.py` | 9 | Feature generation, utilization trend, data isolation |
| `backend/tests/test_failure_risk.py` | 10 | Weibull MLE, probability bounds, monotonicity, isolation |
| `backend/tests/test_demand_forecast.py` | 11 | Demand partitioning, quantiles, horizon consistency, isolation |
| **TOTAL** | **40** | **100% Test Pass Rate** |

---

## 14. Reproducibility & Installation

Follow this step-by-step workflow to reproduce the database, run validation, and execute all tests:

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Generate Synthetic Database
```bash
python scripts/generate_synthetic_data.py --seed 42
```
Outputs SQLite database to `data/minepulse.db`.

### Step 3: Verify Data Integrity
```bash
python scripts/validate_data.py
```
Asserts 0 logical errors, negative stock balances, or orphaned records.

### Step 4: Run Automated Tests
```bash
python -m pytest
```
Verifies all 40 tests pass cleanly.

---

## 15. Known System Limitations
1. **Synthetic Data Disclaimer**: Generated for controlled testing and demonstration; not evidence of real-world site performance.
2. **Right-Censored PM Wearout**: Pre-emptive PM replacements service worn components prior to failure, limiting the observed wearout tail.
3. **Catastrophic Shocks**: Catastrophic failures occur stochastically and are modeled via background hazard rate $\lambda_{\text{cat}}$.

---

## 16. Remaining Development Phases (Unstarted)
* **Phase 4 — Operational Decision Engine**: Inventory optimization ($Q^*$), reorder points, holding/downtime cost trade-offs, dispatcher overrides.
* **Phase 5 — FastAPI Backend Gateway**: REST API endpoints with Pydantic validation schemas.
* **Phase 6 — React Web Interface Dashboard**: Command dashboard, what-if simulators, and dispatcher override screens.
