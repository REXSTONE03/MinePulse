import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def get_auth_headers(username="admin", password="admin123"):
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["database"] == "HEALTHY"

def test_predict_failure_risk_endpoint():
    headers = get_auth_headers()
    payload = {"prediction_timestamp": "2025-06-01", "horizon_days": 30}
    response = client.post("/api/v1/predict", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_timestamp"] == "2025-06-01"
    assert "component_predictions" in data
    assert len(data["component_predictions"]) > 0

def test_forecast_demand_endpoint():
    headers = get_auth_headers()
    payload = {"prediction_timestamp": "2025-06-01", "horizon_days": 30}
    response = client.post("/api/v1/forecast", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_timestamp"] == "2025-06-01"
    assert "forecasts" in data
    assert len(data["forecasts"]) > 0

def test_recommendations_endpoint():
    headers = get_auth_headers()
    payload = {"prediction_timestamp": "2025-06-01", "horizon_days": 30}
    response = client.post("/api/v1/recommendations", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "inventory_recommendations" in data
    assert "maintenance_recommendations" in data
    assert "summary" in data

def test_list_recommendations_endpoint():
    headers = get_auth_headers()
    response = client.get("/api/v1/recommendations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_dispatcher_override_endpoint():
    headers = get_auth_headers("dispatcher", "dispatcher123")
    # First get a recommendation ID
    recs_res = client.get("/api/v1/recommendations", headers=headers)
    recs = recs_res.json()
    rec_id = recs[0]["id"]
    
    override_payload = {
        "dispatcher_name": "Chief_Dispatcher_Bob",
        "new_decision": "MONITOR",
        "override_qty": 0,
        "reason": "Sufficient buffer found in secondary mine site inventory",
        "timestamp": "2025-06-01T14:00:00"
    }
    
    response = client.post(f"/api/v1/recommendations/{rec_id}/override", json=override_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["recommendation"]["status"] == "OVERRIDDEN"

def test_invalid_override_endpoint():
    headers = get_auth_headers("dispatcher", "dispatcher123")
    override_payload = {
        "dispatcher_name": "Chief_Dispatcher_Bob",
        "new_decision": "INVALID_DECISION_TYPE",
        "override_qty": 0,
        "reason": "Test",
        "timestamp": "2025-06-01T14:00:00"
    }
    response = client.post("/api/v1/recommendations/1/override", json=override_payload, headers=headers)
    assert response.status_code == 400

def test_audit_log_endpoint():
    headers = get_auth_headers()
    response = client.get("/api/v1/audit", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["action"] == "OVERRIDE_APPLIED"
