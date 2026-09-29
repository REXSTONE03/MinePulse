import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["database"] == "HEALTHY"

def test_predict_failure_risk_endpoint():
    payload = {"prediction_timestamp": "2025-06-01", "horizon_days": 30}
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_timestamp"] == "2025-06-01"
    assert "component_predictions" in data
    assert len(data["component_predictions"]) > 0

def test_forecast_demand_endpoint():
    payload = {"prediction_timestamp": "2025-06-01", "horizon_days": 30}
    response = client.post("/api/v1/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_timestamp"] == "2025-06-01"
    assert "forecasts" in data
    assert len(data["forecasts"]) > 0

def test_recommendations_endpoint():
    payload = {"prediction_timestamp": "2025-06-01", "horizon_days": 30}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "inventory_recommendations" in data
    assert "maintenance_recommendations" in data
    assert "summary" in data

def test_list_recommendations_endpoint():
    response = client.get("/api/v1/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_dispatcher_override_endpoint():
    # First get a recommendation ID
    recs_res = client.get("/api/v1/recommendations")
    recs = recs_res.json()
    rec_id = recs[0]["id"]
    
    override_payload = {
        "dispatcher_name": "Chief_Dispatcher_Bob",
        "new_decision": "MONITOR",
        "override_qty": 0,
        "reason": "Sufficient buffer found in secondary mine site inventory",
        "timestamp": "2025-06-01T14:00:00"
    }
    
    response = client.post(f"/api/v1/recommendations/{rec_id}/override", json=override_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["recommendation"]["status"] == "OVERRIDDEN"

def test_invalid_override_endpoint():
    override_payload = {
        "dispatcher_name": "Chief_Dispatcher_Bob",
        "new_decision": "INVALID_DECISION_TYPE",
        "override_qty": 0,
        "reason": "Test",
        "timestamp": "2025-06-01T14:00:00"
    }
    response = client.post("/api/v1/recommendations/1/override", json=override_payload)
    assert response.status_code == 400

def test_audit_log_endpoint():
    response = client.get("/api/v1/audit")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["action"] == "OVERRIDE_APPLIED"
