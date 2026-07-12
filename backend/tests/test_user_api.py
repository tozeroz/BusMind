import pytest
import hashlib
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.models.user import Base, EmailVerificationCode
from app.dependencies.auth import get_db

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


def _seed_verification_code(email: str = "test@example.com", plain_code: str = "123456"):
    db = TestingSessionLocal()
    code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
    record = EmailVerificationCode(
        email=email,
        code_hash=code_hash,
        purpose="register",
        expires_at=datetime.now() + timedelta(minutes=5),
    )
    db.add(record)
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def test_user():
    _seed_verification_code()
    return {
        "username": "testuser",
        "password": "testpassword123",
        "password_confirm": "testpassword123",
        "email": "test@example.com",
        "verification_code": "123456",
        "nickname": "Test User",
    }


def test_register_user(client, test_user):
    response = client.post("/api/v1/users/register", json=test_user)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["username"] == test_user["username"]
    assert data["data"]["email"] == "test@example.com"


def test_register_password_mismatch(client):
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "mismatch",
            "password": "testpassword123",
            "password_confirm": "different",
            "email": "mismatch@example.com",
            "verification_code": "123456",
        },
    )
    assert response.status_code == 422


def test_register_email_duplicate(client, test_user):
    _seed_verification_code("test@example.com", "654321")
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "dupuser",
            "password": "testpassword123",
            "password_confirm": "testpassword123",
            "email": "test@example.com",
            "verification_code": "654321",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert "already registered" in data["detail"]["message"]


def test_register_bad_code(client):
    _seed_verification_code("badcode@example.com", "999999")
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "badcode",
            "password": "testpassword123",
            "password_confirm": "testpassword123",
            "email": "badcode@example.com",
            "verification_code": "111111",
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid verification code" in data["detail"]["message"]


def _login_token(client, test_user):
    response = client.post("/api/v1/users/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]
    return data["data"]["access_token"]


def test_login_user(client, test_user):
    assert _login_token(client, test_user)


def test_get_me(client, test_user):
    token = _login_token(client, test_user)
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["user"]["username"] == test_user["username"]
    assert "favorite_count" in data["data"]
    assert "history_count" in data["data"]


def test_add_and_get_favorites(client, test_user):
    token = _login_token(client, test_user)
    
    add_response = client.post(
        "/api/v1/users/me/favorites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "favorite_type": "line",
            "target_id": 1,
            "target_name": "测试线路"
        }
    )
    assert add_response.status_code == 201
    data = add_response.json()
    assert data["code"] == 0
    favorite_id = data["data"]["favorite_id"]
    
    get_response = client.get(
        "/api/v1/users/me/favorites",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    assert data["data"]["favorites"][0]["favorite_id"] == favorite_id
    


def test_delete_favorite(client, test_user):
    token = _login_token(client, test_user)
    get_response = client.get(
        "/api/v1/users/me/favorites",
        headers={"Authorization": f"Bearer {token}"},
    )
    favorites = get_response.json()["data"]["favorites"]
    assert favorites
    favorite_id = favorites[0]["favorite_id"]
    
    delete_response = client.delete(
        f"/api/v1/users/me/favorites/{favorite_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["code"] == 0
    
    get_response = client.get(
        "/api/v1/users/me/favorites",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["data"]["total"] == 0


def test_get_query_history(client, test_user):
    token = _login_token(client, test_user)
    
    response = client.get(
        "/api/v1/users/me/query-history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "histories" in data["data"]
    assert "total" in data["data"]