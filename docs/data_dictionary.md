# MinePulse AI — Data Dictionary

> [!IMPORTANT]
> **Synthetic Dataset Disclaimer**
> This dataset is synthetic and is intended for methodological evaluation and prototype validation, not as evidence of real mining-site performance.

This document details the database schema, data types, nullability, constraints, indexes, and relationships for the SQLite database.

---

## ER Diagram Concept (Relational Layout)

```
        +------------------+           +----------------------+
        |     vehicles     | <-------+ |   maintenance_plans  |
        +------------------+           +----------------------+
                 ^                                |
                 | (1:N)                          | (N:1)
                 |                                v
        +------------------+           +----------------------+
        |    components    | <-------+ |       failures       |
        +------------------+           +----------------------+
                 ^                                |
                 | (1:N)                          | (N:1)
                 |                                v
        +------------------+           +----------------------+
        |      parts       | <-------+ |      part_usage      |
        +------------------+           +----------------------+
                 ^                                
                 | (N:1)                          
                 |                                
        +------------------+            +---------------------+
        |    suppliers     |            |  model_governance   |
        +------------------+            +---------------------+
                                                   |
                                                   | (1:N)
                                                   v
                                        +---------------------+
                                        |   recommendations   |
                                        +---------------------+
```

---

## 1. Table: `vehicles`
Stores metadata and cumulative status of each mining haul truck.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Unique system identifier for the vehicle. |
| `name` | TEXT | - | No | UNIQUE | Human-readable name (e.g. "Haul Truck HT-01"). |
| `model` | TEXT | - | No | - | Vehicle model (e.g. "CAT 797F"). |
| `age_years` | REAL | - | No | CHECK(age_years >= 0) | Chronological age of the vehicle. |
| `operating_hours` | REAL | - | No | DEFAULT 0.0 | Cumulative engine operating hours. |
| `status` | TEXT | - | No | CHECK(status IN ('ACTIVE', 'DOWN', 'MAINTENANCE')) | Current operational status. |

* **Indexes**: `idx_vehicles_status` on `status`.

---

## 2. Table: `components`
Tracks major assembly groups installed on each vehicle to calculate wear and failure hazard.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Unique identifier for the component. |
| `vehicle_id` | INTEGER | FK | No | REFERENCES vehicles(id) ON DELETE CASCADE | Associated vehicle. |
| `type` | TEXT | - | No | CHECK(type IN ('ENGINE', 'TRANSMISSION', 'HYDRAULICS', 'UNDERCARRIAGE')) | Category of the component. |
| `installed_date` | TEXT | - | No | ISO8601 Date String | Date the component was installed. |
| `operating_hours_at_install` | REAL | - | No | DEFAULT 0.0 | Operating hours of the vehicle at install. |
| `current_hours` | REAL | - | No | DEFAULT 0.0 | Current operating hours of the component. |

* **Indexes**: `idx_components_vehicle` on `vehicle_id`.

---

## 3. Table: `suppliers`
Details about parts suppliers and historical lead-time estimates.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Unique identifier for the supplier. |
| `name` | TEXT | - | No | - | Supplier name. |
| `base_lead_time_days` | INTEGER | - | No | CHECK(base_lead_time_days > 0) | Expected order-to-delivery time. |
| `reliability_rate` | REAL | - | No | CHECK(reliability_rate BETWEEN 0.0 AND 1.0) | Historical rate of on-time delivery. |

---

## 4. Table: `parts`
Master catalog of parts that can be ordered and replaced.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Unique identifier for the part catalog item. |
| `name` | TEXT | - | No | - | Part name (e.g. "Bearing B-204"). |
| `part_number` | TEXT | - | No | UNIQUE | Manufacturer part number. |
| `unit_cost` | REAL | - | No | CHECK(unit_cost >= 0) | Financial cost per unit. |
| `supplier_id` | INTEGER | FK | No | REFERENCES suppliers(id) | Preferred supplier for re-ordering. |
| `min_order_qty` | INTEGER | - | No | DEFAULT 1, CHECK(min_order_qty > 0) | MOQ imposed by supplier. |
| `min_stock_level` | INTEGER | - | No | DEFAULT 0 | Safety stock threshold level. |
| `lead_time_days` | INTEGER | - | No | DEFAULT 7 | Catalog lead time in days. |

* **Indexes**: `idx_parts_supplier` on `supplier_id`.

---

## 5. Table: `inventory`
Tracks the current state of stock for each part.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `part_id` | INTEGER | PK, FK | No | REFERENCES parts(id) ON DELETE CASCADE | Part link. |
| `stock_on_hand` | INTEGER | - | No | DEFAULT 0, CHECK(stock_on_hand >= 0) | Unallocated stock physically in inventory. |
| `stock_on_order` | INTEGER | - | No | DEFAULT 0, CHECK(stock_on_order >= 0) | Quantity in transit from outstanding orders. |
| `stock_allocated` | INTEGER | - | No | DEFAULT 0 | Reserved parts for pending maintenance. |

---

## 6. Table: `maintenance_plans`
Defines upcoming scheduled preventative maintenance tasks.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Scheduled event ID. |
| `vehicle_id` | INTEGER | FK | No | REFERENCES vehicles(id) ON DELETE CASCADE | Associated vehicle. |
| `component_id` | INTEGER | FK | No | REFERENCES components(id) | Component targeted. |
| `description` | TEXT | - | No | - | Service class summary. |
| `scheduled_date` | TEXT | - | No | ISO8601 Date String | Target calendar date for execution. |
| `scheduled_hours` | REAL | - | No | CHECK(scheduled_hours >= 0) | Target vehicle operating hours. |
| `status` | TEXT | - | No | CHECK(status IN ('PENDING', 'COMPLETED', 'RESCHEDULED')) | Execution status. |

* **Indexes**: `idx_maint_date` on `scheduled_date`, `idx_maint_vehicle` on `vehicle_id`.

---

## 7. Table: `failures`
Logs the occurrence of actual parts or component breakdowns.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Unique failure event ID. |
| `vehicle_id` | INTEGER | FK | No | REFERENCES vehicles(id) | Impacted vehicle. |
| `component_id` | INTEGER | FK | No | REFERENCES components(id) | Failed component. |
| `part_id` | INTEGER | FK | Yes | REFERENCES parts(id) | Primary failed part (if localized). |
| `failure_date` | TEXT | - | No | ISO8601 Date String | Date failure occurred. |
| `operating_hours` | REAL | - | No | - | Cumulative vehicle hours at failure. |
| `downtime_hours` | REAL | - | No | DEFAULT 0.0 | Simulated downtime penalty. |
| `severity` | TEXT | - | No | CHECK(severity IN ('CATASTROPHIC', 'MINOR')) | Severity tier of breakdown. |
| `resolved` | BOOLEAN | - | No | DEFAULT 0 | Flag indicating replacement completed. |

* **Indexes**: `idx_failures_date` on `failure_date`, `idx_failures_vehicle` on `vehicle_id`.

---

## 8. Table: `part_usage`
Stores part transactions for audit and forecasting model training.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Transaction ID. |
| `vehicle_id` | INTEGER | FK | No | REFERENCES vehicles(id) | Associated vehicle. |
| `part_id` | INTEGER | FK | No | REFERENCES parts(id) | Part consumed. |
| `maintenance_plan_id` | INTEGER | FK | Yes | REFERENCES maintenance_plans(id) | Associated maintenance plan (if PM). |
| `failure_id` | INTEGER | FK | Yes | REFERENCES failures(id) | Associated failure record (if reactive). |
| `quantity` | INTEGER | - | No | CHECK(quantity > 0) | Quantity used. |
| `usage_date` | TEXT | - | No | ISO8601 Date String | Date part was installed/replaced. |

* **Indexes**: `idx_usage_part_date` on `(part_id, usage_date)`.

---

## 9. Table: `model_governance`
Registry tracking ML model parameterizations, versions, and out-of-sample metrics.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Unique model entry ID. |
| `model_version` | TEXT | - | No | - | Semantic version (e.g. "v1.0.0"). |
| `algorithm_name` | TEXT | - | No | - | Algorithm descriptor. |
| `feature_set_version` | TEXT | - | No | - | Feature set code tag. |
| `training_dataset_version` | TEXT | - | No | - | Dataset split version text. |
| `training_timestamp` | TEXT | - | No | ISO8601 Timestamp | Re-training completion time. |
| `hyperparameters` | TEXT | - | No | JSON string | Dictionary of algorithm options. |
| `metrics_serialized` | TEXT | - | No | JSON string | Test split diagnostic scores. |
| `is_active` | BOOLEAN | - | No | DEFAULT 1 | Flag indicating active inference state. |

---

## 10. Table: `recommendations`
Output ordering recommendations from the decision engine.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Recommendation ID. |
| `part_id` | INTEGER | FK | No | REFERENCES parts(id) | Target part. |
| `expected_demand` | REAL | - | No | - | Expected demand during lead time. |
| `p50_demand` | REAL | - | No | - | Median demand estimate. |
| `p80_demand` | REAL | - | No | - | 80th percentile demand. |
| `p95_demand` | REAL | - | No | - | 95th percentile demand. |
| `current_inventory` | INTEGER | - | No | - | Stock on hand at generation. |
| `lead_time_days` | INTEGER | - | No | - | Assumed lead time in days. |
| `recommended_order_qty` | INTEGER | - | No | DEFAULT 0 | Suggested buy quantity. |
| `action_required` | TEXT | - | No | CHECK(action_required IN ('ORDER NOW', 'MONITOR', 'NORMAL')) | Recommended alert tier. |
| `status` | TEXT | - | No | DEFAULT 'PENDING' | Status (`PENDING`, `APPROVED`, `OVERRIDDEN`). |
| `created_date` | TEXT | - | No | ISO8601 Date String | Date recommendation generated. |
| `model_governance_id` | INTEGER | FK | No | REFERENCES model_governance(id) | Active model generator link. |

---

## 11. Table: `overrides`
Stores dispatcher overrides of AI recommendation decisions.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Override ID. |
| `recommendation_id` | INTEGER | FK | No | REFERENCES recommendations(id) | Linked recommendation. |
| `part_id` | INTEGER | FK | No | REFERENCES parts(id) | Associated part catalog. |
| `dispatcher_name` | TEXT | - | No | - | Planner who modified. |
| `original_recommendation` | TEXT | - | No | JSON string | Preserved snapshot of AI state. |
| `new_decision` | TEXT | - | No | - | Action state after override. |
| `override_qty` | INTEGER | - | No | CHECK(override_qty >= 0) | Quantity input by user. |
| `reason` | TEXT | - | No | - | Justification for audit purposes. |
| `timestamp` | TEXT | - | No | ISO8601 DateTime String | Event timestamp. |

---

## 12. Table: `audit_log`
Immutable system audit database for tracking API events.

| Column Name | Data Type | PK/FK | Nullable? | Constraints / Defaults | Description |
|---|---|---|---|---|---|
| `id` | INTEGER | PK | No | AUTOINCREMENT | Audit log unique ID. |
| `timestamp` | TEXT | - | No | ISO8601 DateTime String | Time of action. |
| `user` | TEXT | - | No | - | Initiating user or system component. |
| `action` | TEXT | - | No | - | Type of change (e.g. "OVERRIDE_APPLIED", "SCENARIO_SIMULATION"). |
| `details` | TEXT | - | No | - | Detailed description (JSON-like text payload). |
