# MinePulse AI — System Architecture & API Contract

This document outlines the system architecture, API contract, model governance hooks, and staged development phases for the MinePulse AI project.

---

## 1. System Architecture

MinePulse AI follows a decoupled architecture separating the backend REST API (Python + FastAPI + SQLAlchemy) from the interactive client dashboard (React + Vite + Tailwind CSS).

```
                      +-----------------------------+
                      |       React Client          |
                      |   (Vite + Tailwind + Chart) |
                      +--------------+--------------+
                                     |
                                     | (JSON over HTTP)
                                     v
                      +-----------------------------+
                      |      FastAPI Backend        |
                      |   (Uvicorn ASGI Server)     |
                      +--------------+--------------+
                                     |
                         +-----------+-----------+
                         |                       |
                         v                       v
              +---------------------+ +--------------------+
              |  SQLAlchemy ORM     | | scikit-learn       |
              |  (SQLite DB File)   | | (Failure-Risk model|
              +---------------------+ +--------------------+
```

### Components
1. **Frontend Presentation**: Single-Page Application (SPA) consuming REST endpoints. Includes dashboards for fleet commands, inventory availability risk, vehicle profiles, what-if simulators, and dispatcher overrides with audit trails.
2. **REST API Gateway**: Built with FastAPI. Validates requests via Pydantic schemas, handles dependency injection for the DB session, and serves static files if compiled.
3. **Data Access Layer**: Uses SQLAlchemy with SQLite as the storage engine. 
4. **Machine Learning Pipeline**: Random Forest / Gradient Boosting model trained on historical rolling windows. Features are extracted dynamically from database tables.
5. **Simulation Engine**: Event-driven engine written in pure Python/pandas. Evaluates cumulative downtime under baseline vs. predictive inventory strategies.

---

## 2. API Contract

All backend routes are prefixed with `/api` and exchange data in JSON format.

### A. Vehicles
* **`GET /api/vehicles`**
  * *Description*: Retrieve list of all fleet vehicles with basic stats and failure risk.
  * *Response*:
    ```json
    [
      {
        "id": 1,
        "name": "Haul Truck HT-01",
        "model": "CAT 797F",
        "operating_hours": 12450.5,
        "status": "ACTIVE",
        "failure_risk": 0.12
      }
    ]
    ```

* **`GET /api/vehicles/{vehicle_id}`**
  * *Description*: Detailed vehicle profile.
  * *Response*:
    ```json
    {
      "id": 1,
      "name": "Haul Truck HT-01",
      "model": "CAT 797F",
      "age_years": 4.5,
      "operating_hours": 12450.5,
      "status": "ACTIVE",
      "components": [
        {
          "id": 4,
          "type": "ENGINE",
          "current_hours": 3200.1,
          "installed_date": "2025-01-10"
        }
      ]
    }
    ```

* **`GET /api/vehicles/{vehicle_id}/risk`**
  * *Description*: Breakdown of predicted failure risks by component type, including local feature contributions.
  * *Response*:
    ```json
    {
      "vehicle_id": 1,
      "components_risk": [
        {
          "component_id": 4,
          "type": "ENGINE",
          "failure_probability": 0.42,
          "key_drivers": [
            { "feature": "component_hours", "impact": 0.25, "direction": "positive" },
            { "feature": "hours_since_maintenance", "impact": 0.11, "direction": "positive" }
          ]
        }
      ]
    }
    ```

### B. Parts & Inventory
* **`GET /api/parts`**
  * *Description*: List all parts catalog entries, current stock levels, and supplier lead times.
  * *Response*:
    ```json
    [
      {
        "id": 101,
        "name": "Engine Bearing B-204",
        "part_number": "P-ENG-204",
        "stock_on_hand": 5,
        "stock_on_order": 2,
        "lead_time_days": 14,
        "unit_cost": 450.00
      }
    ]
    ```

* **`GET /api/parts/{part_id}/forecast`**
  * *Description*: Fetch expected parts demand forecast (expected, P50, P80, P95) for the lead-time window.
  * *Response*:
    ```json
    {
      "part_id": 101,
      "forecast_horizon_days": 14,
      "expected_demand": 1.84,
      "p50": 2,
      "p80": 3,
      "p95": 5,
      "confidence_level": "MEDIUM",
      "explanation": "High uncertainty due to scheduled engine maintenance on HT-02, combined with sparse failure history (3 occurrences)."
    }
    ```

* **`GET /api/parts/{part_id}/risk`**
  * *Description*: Inventory stockout risk analysis based on current stock, orders, and demand distributions.
  * *Response*:
    ```json
    {
      "part_id": 101,
      "stockout_probability": 0.28,
      "days_until_stockout_expected": 8,
      "incoming_orders": [
        { "order_id": 45, "quantity": 2, "expected_arrival": "2026-09-05" }
      ]
    }
    ```

### C. Recommendations & Overrides
* **`GET /api/recommendations`**
  * *Description*: Fetch active purchasing recommendations.
  * *Response*:
    ```json
    [
      {
        "id": 12,
        "part_id": 101,
        "part_name": "Engine Bearing B-204",
        "expected_demand": 1.84,
        "p80_demand": 3,
        "current_stock": 1,
        "lead_time_days": 14,
        "recommended_order_qty": 2,
        "action_required": "ORDER NOW",
        "status": "PENDING",
        "model_governance_id": 4
      }
    ]
    ```

* **`POST /api/planner/override`**
  * *Description*: Override a system recommendation.
  * *Request Body*:
    ```json
    {
      "recommendation_id": 12,
      "dispatcher_name": "John Doe",
      "new_decision": "ORDER NOW",
      "override_qty": 5,
      "reason": "Retirement of vehicle HT-01 pushed back. Higher immediate usage expected."
    }
    ```
  * *Response*:
    ```json
    {
      "status": "success",
      "audit_id": 451
    }
    ```

* **`GET /api/audit`**
  * *Description*: Complete history of dispatcher overrides.
  * *Response*:
    ```json
    [
      {
        "id": 451,
        "timestamp": "2026-08-28T14:50:00Z",
        "part_id": 101,
        "dispatcher_name": "John Doe",
        "original_recommendation": {
          "action_required": "NORMAL",
          "recommended_order_qty": 2
        },
        "new_decision": "ORDER NOW (Order 5)",
        "reason": "Retirement of vehicle HT-01 pushed back. Higher immediate usage expected."
      }
    ]
    ```

### D. Simulation & Metrics
* **`GET /api/metrics`**
  * *Description*: Main dashboard operational KPIs.
  * *Response*:
    ```json
    {
      "fleet_size": 75,
      "high_risk_vehicles": 4,
      "parts_at_risk_count": 3,
      "critical_shortages_count": 1,
      "projected_downtime_hours": 12.5
    }
    ```

* **`GET /api/backtest`**
  * *Description*: Cumulative back-test performance details comparing baseline and MinePulse AI.
  * *Response*:
    ```json
    {
      "baseline": {
        "downtime_hours": 145.0,
        "stockout_events": 18,
        "emergency_orders": 12,
        "holding_cost": 15400.00
      },
      "minepulse": {
        "downtime_hours": 62.0,
        "stockout_events": 5,
        "emergency_orders": 2,
        "holding_cost": 22300.00
      },
      "improvement_pct": 57.24
    }
    ```

* **`POST /api/simulator/scenario`**
  * *Description*: Run what-if analysis under global parameter overrides (e.g. increase lead times).
  * *Request Body*:
    ```json
    {
      "global_lead_time_multiplier": 1.5,
      "confidence_level": "P95"
    }
    ```
  * *Response*:
    ```json
    {
      "simulated_downtime_hours": 88.5,
      "baseline_downtime_hours": 210.0,
      "simulated_stockout_events": 9
    }
    ```

---

## 3. Technical Risks & Questionable Assumptions

1. **SQLite Concurrent Writes**: SQLite locks the database file on writes. During rolling simulations or multiple concurrent post-overrides, the API might return `database is locked` errors.
   * *Mitigation*: We will configure SQLAlchemy with `connect_args={"timeout": 30}` and use write-ahead logging (WAL) mode to resolve locking contention.
2. **Causal Data Feedback Leakage**: In real operations, replacing a part resets the component operating hours, which drops the failure risk. If we train our model on historical data, we must ensure features are computed as they existed *at the specific historical timestamp* (point-in-time features). Otherwise, future replacements will leak back, artificially lowering historical risk curves.
   * *Mitigation*: The feature extractor will strictly use query windows up to date $T$ for training samples at $T$.
3. **P(part | failure) Stability**: We assume that if a component fails, the probability of needing a specific part is constant. In practice, failure modes change (e.g., minor wear vs catastrophic lockup require different part mixes).
   * *Mitigation*: We will track failure severity in our synthetic generator and conditional probabilities to represent both catastrophic and minor replacement behaviors.
4. **Poisson Demand Assumption**: Discrete Poisson distribution assumes events are independent. If a component failure always requires multiple identical parts (e.g. replacing all 6 cylinders), demand is bunched (overdispersed).
   * *Mitigation*: We will model demand using a Negative Binomial distribution if variance exceeds the mean in historical part counts.

---

## 4. Staged Development Phases

Instead of a 30-hour timeline, the project is structured into six academic evaluation phases:

* **Phase 1: Architecture & Design Review**: Establish and lock down specifications, schema definitions, and API contracts. Ensure zero-data-leakage pipeline design.
* **Phase 2: Database Schema & Causal Data Generation**: Create ORM models, spin up SQLite DB, and implement the deterministic, Weibull-driven synthetic generator with built-in scenario injects.
* **Phase 3: Forecasting Models & ML Pipeline**: Build time-aware feature generation pipeline. Train failure classifier and design distribution selection module for demand prediction intervals.
* **Phase 4: Downtime Simulation Engine**: Implement counterfactual event-driven simulator mapping mechanical, planned, and parts-constrained downtime.
* **Phase 5: REST API & Integration Stubs**: Implement FastAPI gateway with Pydantic validation, model governance logs, and override endpoints.
* **Phase 6: Frontend Interface & Verification**: Create the dashboard UI, integrate back-testing visualizations, run error diagnostics, and execute the test harness.
