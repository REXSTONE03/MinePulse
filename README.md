# MinePulse AI: Parts-Demand Forecaster & Decision-Support System

> [!IMPORTANT]
> **Synthetic Dataset Disclaimer**
> This dataset is synthetic and is intended for methodological evaluation and prototype validation, not as evidence of real mining-site performance.

MinePulse AI is an operational decision-support system designed to reduce vehicle downtime in mining operations caused by unavailable parts. It connects vehicle telematics/operational metrics, scheduled maintenance plans, historical component failures, parts usage history, and supplier lead times to predict parts-demand under uncertainty and recommend optimal ordering actions.

---

## 1. Project Objectives & Problem Statement
Mining operations depend on heavy vehicles working in harsh conditions. Parts are currently ordered after failures, causing avoidable vehicle downtime. MinePulse AI builds a parts-demand forecaster tied to planned maintenance and failure risk. 

The primary business objective is to:
**REDUCE VEHICLE DOWNTIME CAUSED BY UNAVAILABLE PARTS.**

---

## 2. Staged Development Phases
Development is structured into six evaluation phases:
* **Phase 1: Architecture & Design Review (Completed)**: Locked down specifications, schemas, mathematical formulations, and anti-leakage snapshot logic.
* **Phase 2: Database Schema & Causal Data Foundation (Completed)**: Implemented 12 ORM models, created database tables, built causal Weibull wear simulator, and zero-leakage snapshot engine (`snapshot.py`).
* **Phase 3 Task 1: Feature Engineering Layer (Completed)**: Implemented 30+ point-in-time features per active component (`features.py`) with strict zero temporal leakage.
* **Phase 3 Task 2: Failure-Risk Prediction Service (Completed)**: Implemented Weibull MLE parameter fitting ($\beta, \eta$) and catastrophic shock rate ($\lambda_{cat}$) (`failure_risk.py`) for 7/30/60/90-day conditional failure probabilities and risk classification tiers.
* **Phase 3 Task 3: Parts-Demand Forecasting Service (Completed)**: Implemented partitioned demand ($D_{planned} + D_{failure}$) (`demand_forecast.py`), Naive and Moving Average baselines, $P_{10}/P_{95}$ prediction quantiles, dispersion models (Poisson, Negative Binomial, Sparse Bootstrap), and out-of-sample temporal backtesting.
* **Phase 4: Inventory Decision Engine (Future)**: Cost minimization function, safety stock calculation, and dispatcher overrides.
* **Phase 5: REST API (Future)**: FastAPI gateway endpoints with Pydantic validation.
* **Phase 6: Frontend Interface & Diagnostics (Future)**: React command dashboard and prediction error diagnostics.

---

## 3. Execution & Verification Commands

### A. Environment Setup
```bash
pip install sqlalchemy pytest numpy
```

### B. Generate Synthetic Operations Data
```bash
python scripts/generate_synthetic_data.py --seed 42
```

### C. Run All Automated Test Suites (40/40 Passing)
```bash
python -m pytest backend/tests/test_demand_forecast.py
python -m pytest backend/tests/test_failure_risk.py
python -m pytest backend/tests/test_features.py
python -m pytest backend/tests/test_data_foundation.py
```

### D. Execute Data Quality & Schema Validation
```bash
python scripts/validate_data.py
```
