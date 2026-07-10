from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
from app.models.user import User, QueryHistory, UserFavorite
from app.schemas.user_schema import UserRegisterRequest, UserLoginRequest, UserDTO, LoginResponse, UserUpdateRequest, UserMeResponse, QueryHistoryDTO, QueryHistoryResponse, UserFavoriteDTO, UserFavoriteRequest, UserFavoriteResponse
from app.dependencies.auth import verify_password, get_password_hash, create_access_token
from app.core.config import settings

def register_user(db: Session, request: UserRegisterRequest) -> UserDTO:
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise ValueError("Username already exists")
    
    hashed_password = get_password_hash(request.password)
    
    new_user = User(
        username=request.username,
        password_hash=hashed_password,
        nickname=request.nickname or "",
        role=request.role or "passenger"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserDTO(
        user_id=new_user.user_id,
        username=new_user.username,
        nickname=new_user.nickname,
        role=new_user.role,
        created_at=new_user.created_at
    )

def login_user(db: Session, request: UserLoginRequest) -> LoginResponse:
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise ValueError("Username or password error")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserDTO(
            user_id=user.user_id,
            username=user.username,
            nickname=user.nickname,
            role=user.role,
            created_at=user.created_at
        )
    )

def get_current_user(db: Session, user: User) -> UserMeResponse:
    history_count = db.query(func.count(QueryHistory.history_id)).filter(
        QueryHistory.user_id == user.user_id
    ).scalar() or 0
    
    favorite_count = db.query(func.count(UserFavorite.favorite_id)).filter(
        UserFavorite.user_id == user.user_id
    ).scalar() or 0
    
    return UserMeResponse(
        user=UserDTO(
            user_id=user.user_id,
            username=user.username,
            nickname=user.nickname,
            role=user.role,
            created_at=user.created_at
        ),
        favorite_count=favorite_count,
        history_count=history_count
    )

def update_user(db: Session, user: User, request: UserUpdateRequest) -> UserDTO:
    if request.nickname is not None:
        user.nickname = request.nickname
    
    if request.new_password and request.old_password:
        if not verify_password(request.old_password, user.password_hash):
            raise ValueError("Old password error")
        user.password_hash = get_password_hash(request.new_password)
    
    db.commit()
    db.refresh(user)
    
    return UserDTO(
        user_id=user.user_id,
        username=user.username,
        nickname=user.nickname,
        role=user.role,
        created_at=user.created_at
    )


def get_user_history(db: Session, user_id: int, page: int = 1, limit: int = 20) -> QueryHistoryResponse:
    offset = (page - 1) * limit
    
    histories = db.query(QueryHistory).filter(
        QueryHistory.user_id == user_id
    ).order_by(QueryHistory.created_at.desc()).offset(offset).limit(limit).all()
    
    total = db.query(func.count(QueryHistory.history_id)).filter(
        QueryHistory.user_id == user_id
    ).scalar() or 0
    
    history_dtos = [
        QueryHistoryDTO(
            history_id=h.history_id,
            user_id=h.user_id,
            query_type=h.query_type,
            query_params=h.query_params,
            result_summary=h.result_summary,
            created_at=h.created_at
        ) for h in histories
    ]
    
    return QueryHistoryResponse(
        histories=history_dtos,
        total=total
    )


def add_query_history(db: Session, user_id: int, query_type: str, query_params: str, result_summary: str = "") -> QueryHistoryDTO:
    new_history = QueryHistory(
        user_id=user_id,
        query_type=query_type,
        query_params=query_params,
        result_summary=result_summary
    )
    
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    
    return QueryHistoryDTO(
        history_id=new_history.history_id,
        user_id=new_history.user_id,
        query_type=new_history.query_type,
        query_params=new_history.query_params,
        result_summary=new_history.result_summary,
        created_at=new_history.created_at
    )


def get_user_favorites(db: Session, user_id: int, page: int = 1, limit: int = 20) -> UserFavoriteResponse:
    offset = (page - 1) * limit
    
    favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == user_id
    ).order_by(UserFavorite.created_at.desc()).offset(offset).limit(limit).all()
    
    total = db.query(func.count(UserFavorite.favorite_id)).filter(
        UserFavorite.user_id == user_id
    ).scalar() or 0
    
    favorite_dtos = [
        UserFavoriteDTO(
            favorite_id=f.favorite_id,
            user_id=f.user_id,
            favorite_type=f.favorite_type,
            target_id=f.target_id,
            target_name=f.target_name,
            created_at=f.created_at
        ) for f in favorites
    ]
    
    return UserFavoriteResponse(
        favorites=favorite_dtos,
        total=total
    )


def add_user_favorite(db: Session, user_id: int, request: UserFavoriteRequest) -> UserFavoriteDTO:
    existing_favorite = db.query(UserFavorite).filter(
        UserFavorite.user_id == user_id,
        UserFavorite.favorite_type == request.favorite_type,
        UserFavorite.target_id == request.target_id
    ).first()
    
    if existing_favorite:
        raise ValueError("Favorite already exists")
    
    new_favorite = UserFavorite(
        user_id=user_id,
        favorite_type=request.favorite_type,
        target_id=request.target_id,
        target_name=request.target_name
    )
    
    db.add(new_favorite)
    db.commit()
    db.refresh(new_favorite)
    
    return UserFavoriteDTO(
        favorite_id=new_favorite.favorite_id,
        user_id=new_favorite.user_id,
        favorite_type=new_favorite.favorite_type,
        target_id=new_favorite.target_id,
        target_name=new_favorite.target_name,
        created_at=new_favorite.created_at
    )


def delete_user_favorite(db: Session, user_id: int, favorite_id: int) -> bool:
    favorite = db.query(UserFavorite).filter(
        UserFavorite.favorite_id == favorite_id,
        UserFavorite.user_id == user_id
    ).first()
    
    if not favorite:
        return False
    
    db.delete(favorite)
    db.commit()
    return True