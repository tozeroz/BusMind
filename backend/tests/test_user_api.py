import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.user import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_user.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def test_user():
    return {
        "username": "testuser",
        "password": "testpassword123",
        "nickname": "Test User"
    }


def test_register_user(client, test_user):
    response = client.post("/api/v1/users/register", json=test_user)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["username"] == test_user["username"]


def test_login_user(client, test_user):
    response = client.post("/api/v1/users/login", json={
        "username": test_user["username"],
        "password": test_user["password"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]
    return data["data"]["access_token"]


def test_get_me(client, test_user):
    token = test_login_user(client, test_user)
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
    token = test_login_user(client, test_user)
    
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
    
    return favorite_id


def test_delete_favorite(client, test_user):
    token = test_login_user(client, test_user)
    favorite_id = test_add_and_get_favorites(client, test_user)
    
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
    token = test_login_user(client, test_user)
    
    response = client.get(
        "/api/v1/users/me/query-history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "histories" in data["data"]
    assert "total" in data["data"]