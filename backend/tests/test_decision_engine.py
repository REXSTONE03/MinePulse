import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from backend.app.database.models import Base, Part, Inventory, Supplier, Recommendation, Override, AuditLog
from backend.app.services.decision_engine import (
    calculate_inventory_decision,
    generate_operational_recommendations,
    apply_dispatcher_override,
    get_recommendations_list,
    get_audit_trail
)

from backend.app.database.session import SessionLocal

@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()



def test_calculate_inventory_decision_adequate_stock():
    decision = calculate_inventory_decision(
        part_id=1,
        part_name="Test Engine Oil Filter",
        part_number="FLT-001",
        expected_demand=10.0,
        planned_demand=8.0,
        failure_demand=2.0,
        p10_demand=6.0,
        p95_demand=15.0,
        stock_on_hand=50,
        stock_on_order=0,
        stock_allocated=0,
        min_stock_level=5,
        min_order_qty=10,
        lead_time_days=7,
        unit_cost=100.0,
        supplier_reliability=0.98,
        max_component_risk=0.05
    )
    assert decision["recommended_order_qty"] == 0
    assert decision["action_required"] == "NORMAL"
    assert decision["priority"] == "LOW"
    assert decision["projected_shortage"] == 0

def test_calculate_inventory_decision_shortage_reorder():
    decision = calculate_inventory_decision(
        part_id=2,
        part_name="Hydraulic Cylinder Seal Kit",
        part_number="HYD-002",
        expected_demand=25.0,
        planned_demand=10.0,
        failure_demand=15.0,
        p10_demand=15.0,
        p95_demand=40.0,
        stock_on_hand=5,
        stock_on_order=0,
        stock_allocated=2,
        min_stock_level=10,
        min_order_qty=20,
        lead_time_days=14,
        unit_cost=350.0,
        supplier_reliability=0.90,
        max_component_risk=0.45
    )
    assert decision["recommended_order_qty"] >= 20
    assert decision["action_required"] == "ORDER NOW"
    assert decision["priority"] in ["URGENT", "HIGH"]
    assert decision["projected_shortage"] > 0

def test_generate_operational_recommendations(db_session):
    report = generate_operational_recommendations(db_session, prediction_timestamp="2025-06-01", horizon_days=30)
    
    assert "inventory_recommendations" in report
    assert "maintenance_recommendations" in report
    assert "summary" in report
    assert report["summary"]["total_parts_analyzed"] > 0
    
    # Check structure of first inventory recommendation
    inv_rec = report["inventory_recommendations"][0]
    assert "part_id" in inv_rec
    assert "action_required" in inv_rec
    assert "recommended_order_qty" in inv_rec
    assert "explanation" in inv_rec

def test_apply_dispatcher_override(db_session):
    # Fetch a recommendation from DB
    rec = db_session.query(Recommendation).first()
    assert rec is not None
    
    override_res = apply_dispatcher_override(
        db=db_session,
        recommendation_id=rec.id,
        dispatcher_name="Dispatcher_Jane_Doe",
        new_decision="MONITOR",
        override_qty=0,
        reason="Supplier confirmed expedited shipment arriving early",
        timestamp="2025-06-01T10:30:00"
    )
    
    assert override_res["status"] == "SUCCESS"
    assert override_res["recommendation"]["status"] == "OVERRIDDEN"
    assert override_res["recommendation"]["new_action"] == "MONITOR"
    
    # Verify Audit log was written
    logs = get_audit_trail(db_session, limit=10)
    assert len(logs) > 0
    latest_log = logs[0]
    assert latest_log["action"] == "OVERRIDE_APPLIED"
    assert latest_log["user"] == "Dispatcher_Jane_Doe"

def test_invalid_dispatcher_override(db_session):
    with pytest.raises(ValueError):
        apply_dispatcher_override(
            db=db_session,
            recommendation_id=99999,  # Non-existent ID
            dispatcher_name="User",
            new_decision="MONITOR",
            override_qty=0,
            reason="Test",
            timestamp="2025-06-01T10:30:00"
        )
