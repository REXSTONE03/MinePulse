# MinePulse AI — Testing Strategy & Verification Plan

This document details the testing architecture, validation scripts, and specific deterministic checks designed to ensure the correctness and reproducibility of the MinePulse AI system.

---

## 1. Testing Hierarchy

To maintain academic and operational software quality, the testing plan covers four layers:

```
                  +-----------------------------------+
                  |            API Tests              |
                  | (FastAPI endpoints via TestClient)|
                  +-----------------+-----------------+
                                    |
                  +-----------------v-----------------+
                  |         Simulation Tests          |
                  | (Deterministic downtime checks)   |
                  +-----------------+-----------------+
                                    |
                  +-----------------v-----------------+
                  |        Forecasting Tests          |
                  | (Demand formulas & model selection)|
                  +-----------------+-----------------+
                                    |
                  +-----------------v-----------------+
                  |            Unit Tests             |
                  | (DB schemas, ORM, math quantiles) |
                  +-----------------------------------+
```

---

## 2. Deterministic Testing Requirements

### A. Quantile and Model Selection Checks
We enforce unit tests for predictive distribution functions.
* **Poisson Quantile Check**: Given expected demand $\lambda = 2.0$, verify that the computed P80 and P95 integers match exact mathematical Poisson CDF inverse values:
  * P50 must equal $2$
  * P80 must equal $3$
  * P95 must equal $5$
* **Negative Binomial Check**: Given mean $\mu = 2.0$ and dispersion $r = 1.0$ (representing overdispersed demand), verify that the quantiles are correctly widened compared to Poisson:
  * P50 must equal $1$
  * P80 must equal $3$
  * P95 must equal $6$ (verifying the distribution's fatter tail).

### B. Downtime Simulation Checks
We enforce deterministic simulation tests. The test setup mocks a single vehicle, one scheduled maintenance event, and one component failure:
* **Scenario**: 
  * Supplier lead time = 5 days.
  * Vehicle HT-01 experiences component failure requiring a gasket on Day 10.
  * Gasket inventory on hand = 0, stock on order = 0.
* **Expected Outputs**:
  * The simulator must register exactly 120 hours of parts-unavailability downtime (5 days $\times$ 24 hours/day).
  * Mechanical repair time (e.g. 8 hours) must be categorized under Mechanical Downtime, completely separated from Parts-Unavailability Downtime.
  * The simulator must assert that the vehicle becomes active on Day 15.

### C. Time-Aware Pipeline Check (Anti-Leakage)
* **Check**: A test dataset containing historical records up to Day 360 and future records (Day 361+) is fed into the feature generator with `prediction_timestamp = Day 360`.
* **Assertion**: Verify that the generated feature matrix does not contain values, aggregates, or labels from any rows dated $> \text{Day } 360$.

---

## 3. Test Configuration & Execution

All tests will be implemented using Python's standard `unittest` framework or `pytest`, requiring no external database servers (running against an in-memory SQLite database `sqlite:///:memory:`).

### Commands
1. Run all unit and integration tests:
   ```bash
   python -m pytest backend/tests/
   ```
2. Run simulation engine specific checks:
   ```bash
   python -m pytest backend/tests/test_simulation.py -v
   ```
