import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.database.models import Base, Supplier
from scripts.generate_synthetic_data import generate_data

# Test database setup with full seed
engine = create_engine("sqlite:///test_minepulse_rbac.db", connect_args={"check_same_thread": False})
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

def get_token(username, password):
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return res.json()["access_token"]

def test_viewer_role_access():
    token = get_token("viewer", "viewer123")
    headers = {"Authorization": f"Bearer {token}"}

    # VIEWER can read predictions & forecasts
    res_pred = client.post("/api/v1/predict", json={"prediction_timestamp": "2025-06-01"}, headers=headers)
    assert res_pred.status_code == 200

    # VIEWER is forbidden (403) from applying overrides
    res_override = client.post(
        "/api/v1/recommendations/1/override",
        json={"dispatcher_name": "viewer", "new_decision": "MONITOR", "override_qty": 0, "reason": "Test"},
        headers=headers
    )
    assert res_override.status_code == 403

def test_dispatcher_role_access():
    token = get_token("dispatcher", "dispatcher123")
    headers = {"Authorization": f"Bearer {token}"}

    # First generate a recommendation so ID 1 exists
    client.post("/api/v1/recommendations", json={"prediction_timestamp": "2025-06-01"}, headers=headers)

    # DISPATCHER can perform overrides
    res_override = client.post(
        "/api/v1/recommendations/1/override",
        json={"dispatcher_name": "dispatcher", "new_decision": "MONITOR", "override_qty": 0, "reason": "Authorized dispatcher override"},
        headers=headers
    )
    assert res_override.status_code == 200

def test_planner_role_access():
    token = get_token("planner", "planner123")
    headers = {"Authorization": f"Bearer {token}"}

    # MAINTENANCE_PLANNER can trigger retraining
    res_retrain = client.post("/api/v1/monitoring/trigger-retrain", json={"force": True}, headers=headers)
    assert res_retrain.status_code == 200

def test_admin_full_access():
    token = get_token("admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    # ADMIN can access audit log
    res_audit = client.get("/api/v1/audit", headers=headers)
    assert res_audit.status_code == 200
