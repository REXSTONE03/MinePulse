# Stakeholder Acceptance Walkthrough & Design Validation

> [!NOTE]
> **Methodology Disclaimer**: This document presents a **Scenario-Based Stakeholder Acceptance Walkthrough & Design Validation** mapping real-world heavy-equipment operational personas (Maintenance Planner & Dispatcher) to MinePulse AI's features, data models, decision algorithms, and user interfaces. It does not represent an empirical field study or human-subjects trial.

---

## 1. Stakeholder Personas & Operational Roles

### Persona A: Heavy Equipment Maintenance Planner
* **Operational Scope**: Responsible for scheduling preventive maintenance (PM) intervals, managing component replacement cycles, ensuring spare parts kits are available prior to servicing, and minimizing vehicle downtime across the haul truck and excavator fleet.
* **Primary Key Performance Indicators (KPIs)**: Fleet Availability (%), Mean Time Between Failures (MTBF), Schedule Compliance (%), Zero Work-Stoppage Due to Missing Parts.
* **Information Requirements**:
  1. Component-level wearout probabilities ($\beta, \eta$) across 7, 30, 60, and 90-day horizons.
  2. Early warning flags for high-risk components ($\ge 35\%$ failure risk) lacking scheduled PM events.
  3. Partitioned parts demand forecasts ($D_{\text{planned}} + D_{\text{failure}}$).
  4. Required part numbers and kit quantities per maintenance template (PM250, PM500, PM1000).

### Persona B: Chief Operations Dispatcher / Inventory Controller
* **Operational Scope**: Manages daily mine site logistics, part purchase orders, supplier lead-time buffers, stockroom allocations, and emergency reorder approvals.
* **Primary Key Performance Indicators (KPIs)**: Stockout Rate (%), Inventory Holding Costs ($), Supplier On-Time Delivery Rate (%), Emergency Expedited Freight Cost ($).
* **Information Requirements**:
  1. Real-time stock on hand, stock on order, and allocated stock.
  2. Optimized Economic Reorder Quantity ($Q^*$) taking into account lead times and demand uncertainty ($P_{95}$).
  3. Action prioritization (`URGENT_REORDER`, `REORDER`, `MONITOR`, `NORMAL`).
  4. Non-destructive Dispatcher Override mechanism with audit trail to adjust automated recommendations based on operational context (e.g., inter-site inventory transfers).

---

## 2. Scenario-Based Operational Walkthroughs

### Scenario 1: Preventive Maintenance Planning & Kit Readiness
* **Situation**: Maintenance Planner prepares for upcoming 30-day service cycles for CAT 797F haul trucks.
* **Walkthrough Steps**:
  1. The planner accesses the MinePulse AI Dashboard (`/dashboard`) or queries `POST /api/v1/recommendations`.
  2. The system evaluates component failure risks (`predict_component_failure_risk`) and filters components in `HIGH` or `CRITICAL` risk tiers ($P_{\text{fail}} \ge 35\%$).
  3. For Engine #104 (Risk = 42.1%), the system checks whether a PM plan is scheduled in the next 30 days.
  4. **System Action**: Generates a `SCHEDULE_MAINTENANCE` recommendation linking Engine Filter Kits (`P-ENG-101`) to the PM schedule, guaranteeing part reservation in inventory (`stock_allocated`).

### Scenario 2: Probabilistic Parts Shortage & Reorder Trigger ($Q^*$)
* **Situation**: Hydraulic pump seal kits (`P-HYD-903`) experience accelerated failure-driven demand across excavators due to severe site operating conditions.
* **Walkthrough Steps**:
  1. Stock on hand for `P-HYD-903` is 2 units; lead time is 14 days; minimum order quantity is 10 units.
  2. Forecasted 30-day demand: $D_{\text{planned}} = 0.0$, $D_{\text{failure}} = 22.54$ units ($P_{95} = 58.35$ units).
  3. **Decision Engine Formula**:
     $$\text{Target Inventory} = \text{math.ceil}(D_{\text{total}}) + \text{Safety Stock} + \text{Min Stock} = 23 + 12 + 5 = 40 \text{ units}$$
     $$\text{Projected Shortage} = \text{Target Inventory} - \text{Available Inventory} = 40 - 2 = 38 \text{ units}$$
     $$Q^* = \max(\text{Projected Shortage}, \text{Min Order Qty}) = \max(38, 10) = 38 \text{ units}$$
  4. **System Action**: Generates an `ORDER NOW` recommendation with `URGENT` priority because stock on hand (2) is below lead-time demand.

### Scenario 3: Dispatcher Override & System Auditability
* **Situation**: Dispatcher receives an `ORDER NOW` recommendation for 38 units of `P-HYD-903`, but knows that a secondary site warehouse is transferring 20 units via internal truck delivery arriving tomorrow.
* **Walkthrough Steps**:
  1. Dispatcher selects the recommendation in the UI and opens the **Apply Dispatcher Override** interface.
  2. Changes decision to `MONITOR`, sets `override_qty = 0`, and enters rationale: *"Inter-site transfer of 20 units arriving tomorrow from Pit B inventory."*
  3. Submits `POST /api/v1/recommendations/{id}/override`.
  4. **System Action**:
     * Updates recommendation status to `OVERRIDDEN`.
     * Writes exact snapshot of original recommendation, new decision, dispatcher identity, timestamp, and reason to `overrides` table.
     * Appends an immutable audit log record to `audit_log` table for governance review.

---

## 3. Traceability Mapping: User Requirements to MinePulse Modules

| Operational User Need | MinePulse System Component | Backend Implementation | UI / API Contract |
| :--- | :--- | :--- | :--- |
| **Point-in-Time Fleet Status** | Snapshot Engine | [`snapshot.py`](../backend/app/services/snapshot.py) | `get_feature_snapshot()` |
| **Component Failure Probability** | Weibull Risk Model | [`failure_risk.py`](../backend/app/services/failure_risk.py) | `POST /api/v1/predict` |
| **Parts Demand & Uncertainty** | Demand Forecaster | [`demand_forecast.py`](../backend/app/services/demand_forecast.py) | `POST /api/v1/forecast` |
| **Inventory Reorder Quantity ($Q^*$)** | Operational Decision Engine | [`decision_engine.py`](../backend/app/services/decision_engine.py) | `POST /api/v1/recommendations` |
| **Dispatcher Decision Control** | Override Service | [`decision_engine.py`](../backend/app/services/decision_engine.py) | `POST /api/v1/recommendations/{id}/override` |
| **Compliance & Model Audit** | Audit Logging | [`models.py`](../backend/app/database/models.py) (`AuditLog`) | `GET /api/v1/audit` |
