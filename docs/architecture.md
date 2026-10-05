# MinePulse AI — System Architecture & API Specification

This document details the production architecture, API contracts, database access patterns, security specifications, and deployment infrastructure of the MinePulse AI platform.

---

## 1. System Architecture

MinePulse AI follows a decoupled, cloud-native micro-architecture separating the React 18 / Vite single-page frontend application from the FastAPI REST backend service and the PostgreSQL ORM database layer.

```
+-----------------------------------------------------------------------------------+
|                        React 18 / Vite Production UI Client                       |
|           (Chart.js + Lucide Icons + Tailwind CSS + Axios API Service)            |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | (JSON over HTTP + OAuth2 JWT Bearer)
                                          v
+-----------------------------------------------------------------------------------+
|                           FastAPI Gateway (Uvicorn ASGI)                          |
|         (CORS Hardening + JWT Auth Middleware + RBAC Role Dependencies)           |
+-----------------------------------------+-----------------------------------------+
                                          |
                 ┌────────────────────────┼────────────────────────┐
                 ▼                        ▼                        ▼
+----------------------------------+ +--------------------+ +---------------------+
| SQLAlchemy ORM Access Layer      | | Weibull Risk &     | | Model Monitoring &  |
| (PostgreSQL 15 / SQLite Fallback)| | Demand Forecaster  | | PSI Feature Drift   |
+----------------------------------+ +--------------------+ +---------------------+
```

---

## 2. Infrastructure & Deployment Architecture

### A. Docker Containerization (`docker-compose.yml`)
* **`postgres` Service**: PostgreSQL 15 database container with volume persistence (`postgres_data`).
* **`backend` Service**: Multi-stage Python 3.11 container running Uvicorn ASGI server on port 8000.
* **`frontend` Service**: Multi-stage Node 22 build container serving Vite compiled assets via Nginx on port 3000.

### B. Kubernetes Manifests (`k8s/`)
* `namespace.yaml`: Isolated `minepulse` namespace.
* `configmap.yaml` & `secret.example.yaml`: Environment configuration and secret injection.
* `postgres-statefulset.yaml`: Persistent Volume Claim (PVC) stateful database deployment.
* `backend-deployment.yaml`: Replicated backend pods with liveness (`/api/v1/health`) and readiness probes.
* `frontend-deployment.yaml`: High-availability Nginx frontend web server pods.
* `ingress.yaml`: Ingress controller routing `/api` traffic to backend and `/` traffic to frontend.

---

## 3. Security & Access Control Specifications

### A. OAuth2 / JWT Authentication
* Password hashing using `bcrypt` via Passlib.
* Token issuance endpoint: `POST /api/v1/auth/token`.
* User profile endpoint: `GET /api/v1/auth/me`.

### B. Role-Based Access Control (RBAC)
* **`ADMIN`**: Unrestricted platform access, system configuration, model retraining.
* **`MAINTENANCE_PLANNER`**: View risk models, maintenance schedules, demand forecasts, trigger retraining.
* **`DISPATCHER`**: View inventory, Q* recommendations, apply dispatcher overrides, inspect audit logs.
* **`VIEWER`**: Read-only dashboard access.

---

## 4. API Endpoints Reference

### Public Endpoints
* `GET /api/v1/health`: System health status check.

### Authentication Endpoints
* `POST /api/v1/auth/token`: OAuth2 password login, returns JWT access token.
* `GET /api/v1/auth/me`: Fetch authenticated user profile and active role.

### Predictive & Operational Endpoints (Authenticated & Protected)
* `GET /api/v1/snapshot/summary`: Fleet operational snapshot statistics.
* `GET /api/v1/predict/failure-risk`: Weibull multi-horizon failure probabilities (7/30/60/90 days).
* `GET /api/v1/forecast/demand`: Partitioned demand forecast with P10/P95 uncertainty.
* `GET /api/v1/recommendations/inventory`: Cost-optimal Q* reorder recommendations.
* `POST /api/v1/recommendations/override`: Submit dispatcher override (Requires `DISPATCHER` or `ADMIN`).
* `GET /api/v1/audit/logs`: Historical dispatcher override audit records (Requires `DISPATCHER` or `ADMIN`).

### Governance & Monitoring Endpoints
* `GET /api/v1/monitoring/summary`: Active model version, Brier score, and demand MAE.
* `GET /api/v1/monitoring/drift`: Population Stability Index (PSI) feature drift metrics.
* `POST /api/v1/monitoring/trigger-retrain`: Evaluate thresholds or trigger automated retraining (Requires `ADMIN` or `MAINTENANCE_PLANNER`).

---

## 5. Development Phase Completion Status

All 6 development phases are **100% COMPLETE AND VERIFIED**:

1. **Phase 1: Architecture & Requirements**: COMPLETE (100%)
2. **Phase 2: Database Schema & Causal Data Foundation**: COMPLETE (100%)
3. **Phase 3: Feature Engineering, Weibull Risk & Demand Forecasting**: COMPLETE (100%)
4. **Phase 4: Operational Decision Engine (Q*) & Overrides**: COMPLETE (100%)
5. **Phase 5: FastAPI REST API Gateway & Authentication**: COMPLETE (100%)
6. **Phase 6: Production React/Vite Dashboard & Monitoring**: COMPLETE (100%)
