import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import Base, User, UserFavorite, QueryHistory
from app.services.user_service import (
    register_user,
    login_user,
    get_current_user,
    get_user_favorites,
    add_user_favorite,
    delete_user_favorite,
    get_user_history,
    add_query_history
)
from app.schemas.user_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserFavoriteRequest
)

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


def test_register_and_login(db_session):
    register_request = UserRegisterRequest(
        username="testuser",
        password="testpassword123",
        nickname="Test User"
    )
    
    user = register_user(db_session, register_request)
    assert user.username == "testuser"
    assert user.nickname == "Test User"
    
    login_request = UserLoginRequest(
        username="testuser",
        password="testpassword123"
    )
    
    login_response = login_user(db_session, login_request)
    assert login_response.access_token is not None
    assert login_response.user.username == "testuser"


def test_favorite_count(db_session):
    register_request = UserRegisterRequest(
        username="testuser2",
        password="testpassword123",
        nickname="Test User 2"
    )
    
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
    register_request = UserRegisterRequest(
        username="testuser3",
        password="testpassword123",
        nickname="Test User 3"
    )
    
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
    register_request = UserRegisterRequest(
        username="testuser4",
        password="testpassword123",
        nickname="Test User 4"
    )
    
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
    register_request = UserRegisterRequest(
        username="testuser5",
        password="testpassword123",
        nickname="Test User 5"
    )
    
    user = register_user(db_session, register_request)
    
    add_query_history(db_session, user.user_id, "recommend", '{"start":1,"end":2}', "推荐了3条路线")
    
    history = get_user_history(db_session, user.user_id)
    assert history.total == 1
    assert history.histories[0].query_type == "recommend"


def test_duplicate_favorite(db_session):
    register_request = UserRegisterRequest(
        username="testuser6",
        password="testpassword123",
        nickname="Test User 6"
    )
    
    user = register_user(db_session, register_request)
    
    favorite_request = UserFavoriteRequest(
        favorite_type="line",
        target_id=1,
        target_name="测试线路"
    )
    
    add_user_favorite(db_session, user.user_id, favorite_request)
    
    with pytest.raises(ValueError, match="Favorite already exists"):
        add_user_favorite(db_session, user.user_id, favorite_request)