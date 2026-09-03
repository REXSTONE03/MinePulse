# MinePulse AI — Requirements Specification

This document details the functional and non-functional requirements for the MinePulse AI parts-demand forecaster and decision-support system.

---

## 1. Functional Requirements (FR)

### FR-01: Vehicle Fleet Information Management
* **Description**: The system shall maintain records for all vehicles in the mining fleet, including vehicle identifier, name, model, age, current operating hours, and operational status.
* **Input**: Vehicle ID, vehicle name, model, age, operational status.
* **Output**: Detailed vehicle status profile.

### FR-02: Component Tracking
* **Description**: The system shall track major vehicle components (Engine, Transmission, Hydraulics, Undercarriage) including serial numbers, installation dates, operating hours at installation, and cumulative component operating hours.
* **Input**: Component ID, vehicle association, installation history, cumulative hours.
* **Output**: Component age and wear state.

### FR-03: Maintenance Schedule Management
* **Description**: The system shall maintain a schedule of planned preventive maintenance events, including planned execution date, target operating hours, description of work, and status (Pending, Completed, Rescheduled).
* **Input**: Vehicle ID, component ID, scheduled date, task details.
* **Output**: Maintenance plan timeline.

### FR-04: Historical Failure Logging
* **Description**: The system shall log all component and part failures, recording the failure date, vehicle operating hours at failure, part responsible, failure severity (Catastrophic, Minor), and downtime duration.
* **Input**: Vehicle ID, component ID, failure date, operating hours, part ID, severity.
* **Output**: Historical failure log.

### FR-05: Part Consumption Logging
* **Description**: The system shall maintain an immutable history of part usage associated with both planned maintenance events and unplanned failure events.
* **Input**: Part ID, quantity, date, association (failure ID or maintenance plan ID).
* **Output**: Consumption metrics by part and vehicle.

### FR-06: Supplier and Lead Time Tracking
* **Description**: The system shall maintain supplier records, including part catalogs, base lead times (in days), minimum order quantities, and supplier reliability metrics.
* **Input**: Supplier ID, name, lead times, reliability parameters.
* **Output**: Lead time estimates per part.

### FR-07: Parts Demand Forecasting (Prediction Task B)
* **Description**: The system shall forecast the future quantity of each part required during a defined forecast horizon, separating planned maintenance demand ($D_{planned}$) from failure-driven demand ($D_{failure}$).
* **Input**: Parts catalog, maintenance schedule, component failure probabilities.
* **Output**: Expected part demand ($E[D_{total}]$).

### FR-08: Uncertainty Quantification & Terminology
* **Description**: The system shall expose parts demand forecasts using statistically correct prediction intervals (P50: median, P80: 80th percentile, P95: 95th percentile of the predictive distribution) and evaluate empirical coverage and interval width.
* **Input**: Model historical errors, demand statistics.
* **Output**: Prediction intervals (P50, P80, P95) with data density warnings for sparse parts.

### FR-09: Parts Availability Risk Estimation (Prediction Task C)
* **Description**: The system shall calculate the probability that required parts will be unavailable when needed (stockout risk) during the lead-time window, distinct from demand forecasting.
* **Input**: Current inventory, outstanding orders, forecast demand distribution.
* **Output**: Stockout probability (percentage) for each part.

### FR-10: Ordering Recommendations & Objective Function
* **Description**: The system shall generate parts-ordering recommendations, classifying actions as `ORDER NOW`, `MONITOR`, or `NORMAL`, utilizing an objective cost minimization function (holding cost vs. downtime cost).
* **Input**: Stockout risk, unit cost, supplier lead time, minimum order quantity.
* **Output**: Recommendation status, recommended quantity, and rationales.

### FR-11: Dispatcher Override (Human-in-the-Loop)
* **Description**: AI recommendations must be advisory. The dispatcher can Approve, Reject, Modify quantity, or Override urgency.
* **Input**: Recommendation ID, dispatcher name, new decision, overridden quantity, justification.
* **Output**: Updated order recommendation state.

### FR-12: Dispatcher Decision Auditing
* **Description**: The system shall record all overrides in an immutable audit trail, preserving the original AI recommendation, human decision, overridden quantity, user, timestamp, and reason. The original recommendation must never be silently overwritten.
* **Input**: User credentials, override payload, reason.
* **Output**: Audit trail entries.

### FR-13: Chronological Back-Testing & Counterfactual Evaluation
* **Description**: The system shall support back-testing of the forecasting and decision engine using chronological rolling windows. The baseline and MinePulse AI must face the exact same historical/synthetic event stream.
* **Input**: Historic datasets, split dates, model configurations.
* **Output**: Back-test performance metrics.

### FR-14: Downtime Simulator & Measurement
* **Description**: The system shall run a deterministic, event-driven simulation to measure vehicle-hours of downtime caused specifically by unavailable parts (distinguishing mechanical, planned maintenance, and parts-unavailability downtime).
* **Input**: Historical ground-truth failures, simulated stock levels, and supplier delivery delays.
* **Output**: Downtime hours comparison: Baseline vs. MinePulse AI.

### FR-15: Prediction Error & Failure Analysis
* **Description**: The system shall identify and classify forecasting errors in a structured error table (catastrophic failures, sparse data, rescheduling, model errors).
* **Input**: Forecast logs, actual usage events.
* **Output**: Error diagnostic table and confusion matrix metrics.

---

## 2. Non-Functional Requirements (NFR)

### NFR-01: Reproducibility
* **Specification**: The data generation, model training, simulation, and back-testing pipeline must yield identical results across executions. Enforced via global random seeding.

### NFR-02: Explainability
* **Specification**: The failure risk prediction and demand forecasting must provide understandable explanations (feature contributions, demand breakdown formula, and model selection justifications).

### NFR-03: Data Integrity
* **Specification**: The database schema must enforce referential integrity and prevent data corruption. Enforced via SQLite foreign key constraints and check constraints.

### NFR-04: Model Governance & Traceability
* **Specification**: Every recommendation must store a reference to the active model version, training dataset version, feature set version, and training timestamp that generated it.

### NFR-05: Maintainability
* **Specification**: The codebase must be modular and follow standard clean-code architecture, avoiding hard-coded hackathon constraints.

### NFR-06: Usability
* **Specification**: The operational interface must instantly convey the operational risk of the fleet to a dispatcher.

### NFR-07: API Separation
* **Specification**: The client application must communicate with the server strictly via standard HTTP REST API endpoints.

### NFR-08: Testability
* **Specification**: Core algorithms (downtime simulation, demand forecasting formulas, and order recommendation logic) must have associated test suites.
