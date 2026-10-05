import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.database.models import Base, Supplier
from backend.app.services.monitoring import calculate_psi, evaluate_feature_drift, get_monitoring_summary
from scripts.generate_synthetic_data import generate_data

# Test database setup
engine = create_engine("sqlite:///test_minepulse_monitoring.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

db = TestingSessionLocal()
if db.query(Supplier).count() == 0:
    generate_data(db, seed=42)
db.close()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_psi_calculation_no_drift():
    ref = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    curr = [105, 195, 305, 395, 505, 595, 705, 795, 905, 995]
    psi = calculate_psi(ref, curr)
    assert psi < 0.10

def test_psi_calculation_high_drift():
    ref = [100, 200, 300, 400, 500]
    curr = [2000, 3000, 4000, 5000, 6000]
    psi = calculate_psi(ref, curr)
    assert psi >= 0.25

def test_feature_drift_evaluation(db_session=None):
    session = TestingSessionLocal()
    res = evaluate_feature_drift(session, "2025-06-01")
    assert "evaluated_features" in res
    assert "overall_drift_score" in res
    assert "recommend_retraining" in res
    session.close()

def test_monitoring_summary_service():
    session = TestingSessionLocal()
    summary = get_monitoring_summary(session, "2025-06-01")
    assert "active_model_version" in summary
    assert "failure_risk_metrics" in summary
    assert "demand_forecast_metrics" in summary
    assert "data_drift" in summary
    session.close()

def test_monitoring_api_endpoints():
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_sum = client.get("/api/v1/monitoring/summary", headers=headers)
    assert res_sum.status_code == 200

    res_drift = client.get("/api/v1/monitoring/drift", headers=headers)
    assert res_drift.status_code == 200

    res_retrain = client.post("/api/v1/monitoring/trigger-retrain", json={"force": True}, headers=headers)
    assert res_retrain.status_code == 200
    assert res_retrain.json()["status"] == "SUCCESS"
