from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import List, Optional
import os

from backend.app.database.session import get_db, engine
from backend.app.database.models import Base, User
from backend.app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, RequireRole, seed_default_users, ACCESS_TOKEN_EXPIRE_MINUTES
)
from backend.app.schemas import (
    HealthResponse, LoginRequest, TokenResponse, UserResponse,
    PredictRequest, PredictResponse,
    ForecastRequest, ForecastResponse,
    RecommendationRequest, RecommendationResponse,
    OverrideRequest, OverrideResponse,
    AuditLogItem, RetrainTriggerRequest, RetrainTriggerResponse
)
from backend.app.services.failure_risk import predict_component_failure_risk
from backend.app.services.demand_forecast import forecast_parts_demand
from backend.app.services.decision_engine import (
    generate_operational_recommendations,
    apply_dispatcher_override,
    get_recommendations_list,
    get_audit_trail
)
from backend.app.services.monitoring import (
    get_monitoring_summary,
    evaluate_feature_drift,
    trigger_automated_retraining
)

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

# Seed default demo users for RBAC
with next(get_db()) as db_session:
    seed_default_users(db_session)

app = FastAPI(
    title="MinePulse AI REST API Gateway",
    description="Operational decision support API for heavy equipment maintenance failure-risk prediction, parts demand forecasting, and inventory optimization.",
    version="1.0.0"
)

# Configurable Security-Hardened CORS Middleware
raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000")
allowed_origins = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    # If React build dist/index.html exists, serve it; otherwise serve single-page UI
    react_dist = os.path.join(FRONTEND_DIR, "dist", "index.html")
    if os.path.exists(react_dist):
        return FileResponse(react_dist)
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "MinePulse AI API Gateway Online. Visit /docs for Swagger API documentation."}

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Public System Health and Readiness endpoint.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "HEALTHY"
    except Exception as e:
        db_status = f"UNHEALTHY: {str(e)}"
        
    return {
        "status": "ONLINE",
        "version": "1.0.0",
        "database": db_status,
        "service_status": "OPERATIONAL"
    }

# -------------------------------------------------------------------------
# AUTHENTICATION ENDPOINTS (OAuth2 / JWT)
# -------------------------------------------------------------------------

@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login_json(req: LoginRequest, db: Session = Depends(get_db)):
    """
    JSON Login endpoint returning a signed OAuth2 JWT Bearer access token.
    """
    seed_default_users(db)
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account.")

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role,
        "expires_in_minutes": ACCESS_TOKEN_EXPIRE_MINUTES
    }

@app.post("/api/v1/auth/token", response_model=TokenResponse, tags=["Authentication"])
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Standard OAuth2 Form Login endpoint compatible with Swagger UI auth flow.
    """
    return login_json(LoginRequest(username=form_data.username, password=form_data.password), db)

@app.get("/api/v1/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns profile information of the currently authenticated user.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

# -------------------------------------------------------------------------
# PREDICTIVE ANALYTICS & DECISION SERVICES (Protected by Auth & RBAC)
# -------------------------------------------------------------------------

@app.post("/api/v1/predict", response_model=PredictResponse, tags=["Failure Risk"])
def predict_failure_risk(req: PredictRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Predicts Weibull MLE wearout + catastrophic shock failure risks across component fleet for prediction timestamp T.
    """
    try:
        res = predict_component_failure_risk(db, req.prediction_timestamp)
        preds = [
            {
                "component_id": p.component_id,
                "vehicle_id": p.vehicle_id,
                "vehicle_name": f"Vehicle-{p.vehicle_id}",
                "type": p.component_type,
                "current_hours": p.component_age_hours,
                "operating_hours_at_install": 0.0,
                "installed_date": "2024-01-01",
                "weibull_beta": p.fitted_beta,
                "weibull_eta": p.fitted_eta,
                "catastrophic_rate": p.fitted_lambda_cat,
                "failure_probability_7d": p.failure_probability_7d,
                "failure_probability_30d": p.failure_probability_30d,
                "failure_probability_60d": p.failure_probability_60d,
                "failure_probability_90d": p.failure_probability_90d,
                "risk_tier": p.risk_level
            }
            for p in res.predictions
        ]
        return {
            "prediction_timestamp": res.prediction_timestamp,
            "horizon_days": req.horizon_days,
            "total_components_evaluated": len(preds),
            "component_predictions": preds
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing failure risk prediction: {str(e)}"
        )

@app.post("/api/v1/forecast", response_model=ForecastResponse, tags=["Demand Forecast"])
def forecast_demand(req: ForecastRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Forecasts partitioned parts demand (Planned PM + Failure-Driven) with P10/P95 prediction quantiles.
    """
    try:
        res = forecast_parts_demand(db, req.prediction_timestamp, req.horizon_days)
        formatted_forecasts = [
            {
                "part_id": f["part_id"],
                "part_name": f["part_name"],
                "part_number": f["part_number"],
                "planned_maintenance_demand": f["planned_maintenance_demand"],
                "failure_driven_demand": f["failure_driven_demand"],
                "total_expected_demand": f["total_expected_demand"],
                "p10_demand": f.get("p10_demand", f.get("lower_bound", 0.0)),
                "p95_demand": f.get("p95_demand", f.get("upper_bound", 0.0)),
                "confidence_flag": f.get("confidence_flag", "MEDIUM_HISTORY"),
                "dispersion_model": f.get("dispersion_model_used", f.get("dispersion_model", "POISSON"))
            }
            for f in res["forecasts"]
        ]
        return {
            "prediction_timestamp": res["prediction_timestamp"],
            "horizon_days": res["horizon_days"],
            "total_parts_evaluated": res["total_parts_evaluated"],
            "forecasts": formatted_forecasts
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing parts demand forecasting: {str(e)}"
        )

@app.post("/api/v1/recommendations", response_model=RecommendationResponse, tags=["Decision Engine"])
def generate_recommendations(req: RecommendationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Generates unified operational inventory reorder & vehicle maintenance recommendations.
    """
    try:
        res = generate_operational_recommendations(db, req.prediction_timestamp, req.horizon_days)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating operational recommendations: {str(e)}"
        )

@app.get("/api/v1/recommendations", tags=["Decision Engine"])
def list_recommendations(
    status_filter: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, OVERRIDDEN"),
    part_id: Optional[int] = Query(None, description="Filter by part ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves stored recommendations from the database.
    """
    try:
        return get_recommendations_list(db, status_filter=status_filter, part_id=part_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recommendations: {str(e)}"
        )

@app.post("/api/v1/recommendations/{recommendation_id}/override", response_model=OverrideResponse, tags=["Dispatcher Override"])
def override_recommendation(
    recommendation_id: int,
    req: OverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole(["ADMIN", "DISPATCHER"]))
):
    """
    Records a human dispatcher override for an automated recommendation with complete audit trail.
    Requires DISPATCHER or ADMIN role.
    """
    ts = req.timestamp or datetime.utcnow().isoformat()
    try:
        res = apply_dispatcher_override(
            db=db,
            recommendation_id=recommendation_id,
            dispatcher_name=req.dispatcher_name or current_user.username,
            new_decision=req.new_decision,
            override_qty=req.override_qty,
            reason=req.reason,
            timestamp=ts
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying dispatcher override: {str(e)}"
        )

@app.get("/api/v1/audit", response_model=List[AuditLogItem], tags=["Audit Log"])
def get_system_audit_log(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole(["ADMIN", "DISPATCHER", "MAINTENANCE_PLANNER"]))
):
    """
    Retrieves system audit log entries. Requires DISPATCHER, MAINTENANCE_PLANNER, or ADMIN role.
    """
    try:
        return get_audit_trail(db, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving audit log: {str(e)}"
        )

# -------------------------------------------------------------------------
# MODEL MONITORING & AUTOMATED RETRAINING (Phase G & H)
# -------------------------------------------------------------------------

@app.get("/api/v1/monitoring/summary", tags=["Model Governance & Monitoring"])
def get_monitoring_report(
    prediction_timestamp: str = Query("2025-06-01", description="Prediction timestamp T"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns unified model monitoring summary covering failure risk, demand accuracy, PSI data drift, and retraining status.
    """
    try:
        return get_monitoring_summary(db, prediction_timestamp=prediction_timestamp)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating monitoring summary: {str(e)}"
        )

@app.get("/api/v1/monitoring/drift", tags=["Model Governance & Monitoring"])
def get_data_drift_report(
    prediction_timestamp: str = Query("2025-06-01", description="Prediction timestamp T"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates Population Stability Index (PSI) feature drift between historical reference telemetry and current inference data.
    """
    try:
        return evaluate_feature_drift(db, prediction_timestamp=prediction_timestamp)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating feature drift: {str(e)}"
        )

@app.post("/api/v1/monitoring/trigger-retrain", response_model=RetrainTriggerResponse, tags=["Model Governance & Monitoring"])
def trigger_retraining_endpoint(
    req: RetrainTriggerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole(["ADMIN", "MAINTENANCE_PLANNER"]))
):
    """
    Evaluates retraining conditions (PSI >= 0.25) and emits a RETRAINING_TRIGGERED audit event.
    Requires ADMIN or MAINTENANCE_PLANNER role.
    """
    try:
        res = trigger_automated_retraining(db, user=current_user.username, force=req.force)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering automated retraining: {str(e)}"
        )
