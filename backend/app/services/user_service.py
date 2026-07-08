from sqlalchemy.orm import Session
from datetime import timedelta
from app.models.user import User
from app.schemas.user_schema import UserRegisterRequest, UserLoginRequest, UserDTO, LoginResponse, UserUpdateRequest, UserMeResponse
from app.dependencies.auth import verify_password, get_password_hash, create_access_token
from app.core.config import settings

def register_user(db: Session, request: UserRegisterRequest) -> UserDTO:
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise ValueError("用户名已存在")
    
    hashed_password = get_password_hash(request.password)
    
    new_user = User(
        username=request.username,
        password_hash=hashed_password,
        nickname=request.nickname or ""
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserDTO(
        user_id=new_user.user_id,
        username=new_user.username,
        nickname=new_user.nickname,
        created_at=new_user.created_at
    )

def login_user(db: Session, request: UserLoginRequest) -> LoginResponse:
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise ValueError("用户名或密码错误")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
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
            created_at=user.created_at
        )
    )

def get_current_user(db: Session, user: User) -> UserMeResponse:
    return UserMeResponse(
        user=UserDTO(
            user_id=user.user_id,
            username=user.username,
            nickname=user.nickname,
            created_at=user.created_at
        ),
        favorite_count=0,
        history_count=0
    )

def update_user(db: Session, user: User, request: UserUpdateRequest) -> UserDTO:
    if request.nickname is not None:
        user.nickname = request.nickname
    
    if request.new_password and request.old_password:
        if not verify_password(request.old_password, user.password_hash):
            raise ValueError("旧密码错误")
        user.password_hash = get_password_hash(request.new_password)
    
    db.commit()
    db.refresh(user)
    
    return UserDTO(
        user_id=user.user_id,
        username=user.username,
        nickname=user.nickname,
        created_at=user.created_at
    )