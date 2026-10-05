import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.session import get_db
from backend.app.database.models import Base, User
from backend.app.auth import hash_password, verify_password, create_access_token

# Test database setup
engine = create_engine("sqlite:///test_minepulse_auth.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_password_hashing():
    raw_pass = "SecureMiningPass123"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPass", hashed) is False

def test_jwt_token_generation():
    token = create_access_token(data={"sub": "admin", "role": "ADMIN"})
    assert isinstance(token, str)
    assert len(token) > 20

def test_valid_user_login():
    payload = {"username": "admin", "password": "admin123"}
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"
    assert data["role"] == "ADMIN"

def test_invalid_user_login():
    payload = {"username": "admin", "password": "WrongPassword"}
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401

def test_get_current_user_profile():
    # Login first
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "ADMIN"

def test_unauthenticated_protected_endpoint():
    response = client.post("/api/v1/predict", json={"prediction_timestamp": "2025-06-01"})
    assert response.status_code == 401
