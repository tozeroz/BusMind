import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import Base, User, UserFavorite, QueryHistory, EmailVerificationCode
from app.services.user_service import (
    register_user,
    login_user,
    get_current_user,
    get_user_favorites,
    add_user_favorite,
    delete_user_favorite,
    get_user_history,
    add_query_history,
    send_register_email_code,
)
from app.schemas.user_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserFavoriteRequest,
)
from app.services.email_service import EmailServiceConfigError
from datetime import datetime, timedelta
import hashlib

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_user_service.db"


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def _create_verification_code(db, email: str, plain_code: str) -> EmailVerificationCode:
    code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
    record = EmailVerificationCode(
        email=email,
        code_hash=code_hash,
        purpose="register",
        expires_at=datetime.now() + timedelta(minutes=5),
    )
    db.add(record)
    db.commit()
    return record


def _register_request(
    username: str,
    password: str = "testpassword123",
    email: str = "test@example.com",
    code: str = "123456",
    nickname: str = "Test User",
) -> UserRegisterRequest:
    return UserRegisterRequest(
        username=username,
        password=password,
        password_confirm=password,
        email=email,
        verification_code=code,
        nickname=nickname,
    )


def test_register_and_login(db_session):
    _create_verification_code(db_session, "test@example.com", "123456")
    register_request = _register_request("testuser")
    
    user = register_user(db_session, register_request)
    assert user.username == "testuser"
    assert user.nickname == "Test User"
    assert user.email == "test@example.com"
    
    login_request = UserLoginRequest(
        username="testuser",
        password="testpassword123"
    )
    
    login_response = login_user(db_session, login_request)
    assert login_response.access_token is not None
    assert login_response.user.username == "testuser"


def test_password_mismatch(db_session):
    with pytest.raises(ValueError, match="Passwords do not match"):
        UserRegisterRequest(
            username="testuser",
            password="testpassword123",
            password_confirm="different",
            email="test@example.com",
            verification_code="123456",
        )


def test_verification_code_wrong(db_session):
    _create_verification_code(db_session, "wrongcode@example.com", "654321")
    register_request = _register_request("wrongcode", email="wrongcode@example.com", code="111111")
    with pytest.raises(ValueError, match="Invalid verification code"):
        register_user(db_session, register_request)


def test_email_duplicate(db_session):
    _create_verification_code(db_session, "dup@example.com", "123456")
    _create_verification_code(db_session, "dup@example.com", "654321")
    register_request = _register_request("userA", email="dup@example.com", code="123456")
    register_user(db_session, register_request)
    
    register_request2 = _register_request("userB", email="dup@example.com", code="654321")
    with pytest.raises(ValueError, match="Email already registered"):
        register_user(db_session, register_request2)


def test_register_success(db_session):
    _create_verification_code(db_session, "success@example.com", "888888")
    register_request = _register_request("newuser", email="success@example.com", code="888888")
    user = register_user(db_session, register_request)
    assert user.username == "newuser"
    assert user.email == "success@example.com"
    assert user.role == "passenger"


def test_favorite_count(db_session):
    _create_verification_code(db_session, "test2@example.com", "123456")
    register_request = _register_request("testuser2", email="test2@example.com")
    
    user = register_user(db_session, register_request)
    db_user = db_session.query(User).filter(User.user_id == user.user_id).first()
    
    user_me = get_current_user(db_session, db_user)
    assert user_me.favorite_count == 0
    
    favorite_request = UserFavoriteRequest(
        favorite_type="line",
        target_id=1,
        target_name="测试线路"
    )
    add_user_favorite(db_session, user.user_id, favorite_request)
    
    user_me = get_current_user(db_session, db_user)
    assert user_me.favorite_count == 1


def test_add_and_get_favorites(db_session):
    _create_verification_code(db_session, "test3@example.com", "123456")
    register_request = _register_request("testuser3", email="test3@example.com")
    
    user = register_user(db_session, register_request)
    
    favorite_request = UserFavoriteRequest(
        favorite_type="line",
        target_id=1,
        target_name="测试线路1"
    )
    add_user_favorite(db_session, user.user_id, favorite_request)
    
    favorite_request2 = UserFavoriteRequest(
        favorite_type="station",
        target_id=2,
        target_name="测试站点"
    )
    add_user_favorite(db_session, user.user_id, favorite_request2)
    
    favorites = get_user_favorites(db_session, user.user_id)
    assert favorites.total == 2
    assert len(favorites.favorites) == 2
    assert favorites.favorites[0].target_name == "测试站点"
    assert favorites.favorites[1].target_name == "测试线路1"


def test_delete_favorite(db_session):
    _create_verification_code(db_session, "test4@example.com", "123456")
    register_request = _register_request("testuser4", email="test4@example.com")
    
    user = register_user(db_session, register_request)
    
    favorite_request = UserFavoriteRequest(
        favorite_type="line",
        target_id=1,
        target_name="测试线路"
    )
    favorite = add_user_favorite(db_session, user.user_id, favorite_request)
    
    favorites = get_user_favorites(db_session, user.user_id)
    assert favorites.total == 1
    
    success = delete_user_favorite(db_session, user.user_id, favorite.favorite_id)
    assert success is True
    
    favorites = get_user_favorites(db_session, user.user_id)
    assert favorites.total == 0


def test_add_and_get_history(db_session):
    _create_verification_code(db_session, "test5@example.com", "123456")
    register_request = _register_request("testuser5", email="test5@example.com")
    
    user = register_user(db_session, register_request)
    
    add_query_history(db_session, user.user_id, "recommend", '{"start":1,"end":2}', "推荐了3条路线")
    
    history = get_user_history(db_session, user.user_id)
    assert history.total == 1
    assert history.histories[0].query_type == "recommend"


def test_duplicate_favorite(db_session):
    _create_verification_code(db_session, "test6@example.com", "123456")
    register_request = _register_request("testuser6", email="test6@example.com")
    
    user = register_user(db_session, register_request)
    
    favorite_request = UserFavoriteRequest(
        favorite_type="line",
        target_id=1,
        target_name="测试线路"
    )
    
    add_user_favorite(db_session, user.user_id, favorite_request)
    
    with pytest.raises(ValueError, match="Favorite already exists"):
        add_user_favorite(db_session, user.user_id, favorite_request)