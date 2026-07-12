from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies.auth import create_access_token, get_password_hash, verify_password
from app.models.user import EmailVerificationCode, QueryHistory, User
from app.schemas.user_schema import (
    LoginResponse,
    QueryHistoryDTO,
    QueryHistoryResponse,
    UserDTO,
    UserFavoriteDTO,
    UserFavoriteRequest,
    UserFavoriteResponse,
    UserLoginRequest,
    UserMeResponse,
    UserRegisterRequest,
    UserUpdateRequest,
)
from app.services.email_service import (
    EmailServiceConfigError,
    EmailServiceError,
    send_verification_code,
)

# The final database schema does not define a user_favorite table. To keep the
# already-published favorite API working without changing any non-backend code,
# favorite records are stored in user_query_history using a reserved query_type.
FAVORITE_QUERY_TYPE = "__favorite__"


def send_register_email_code(db: Session, email: str) -> None:
    """Send a registration verification code to *email*.

    Raises:
        ValueError: Email already registered or rate-limited.
        EmailServiceConfigError: QQ Mail SMTP not configured.
        EmailServiceError: SMTP send failed.
    """
    email = email.strip().lower()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("Email already registered")

    rate_limit_window = settings.EMAIL_CODE_RESEND_SECONDS
    recent = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == "register",
            EmailVerificationCode.created_at
            >= datetime.now() - timedelta(seconds=rate_limit_window),
        )
        .first()
    )
    if recent:
        raise ValueError(
            f"Please wait {rate_limit_window} seconds before requesting another code"
        )

    plain_code = send_verification_code(email)

    code_hash = hashlib.sha256(plain_code.encode()).hexdigest()
    expires_at = datetime.now() + timedelta(minutes=settings.EMAIL_CODE_EXPIRE_MINUTES)

    record = EmailVerificationCode(
        email=email,
        code_hash=code_hash,
        purpose="register",
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()


def _user_dto(user: User) -> UserDTO:
    return UserDTO(
        user_id=user.user_id,
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


def _history_dto(history: QueryHistory) -> QueryHistoryDTO:
    return QueryHistoryDTO(
        history_id=history.history_id,
        user_id=history.user_id,
        query_type=history.query_type,
        origin_name=history.origin_name,
        origin_longitude=float(history.origin_longitude) if history.origin_longitude is not None else None,
        origin_latitude=float(history.origin_latitude) if history.origin_latitude is not None else None,
        destination_name=history.destination_name,
        destination_longitude=(
            float(history.destination_longitude) if history.destination_longitude is not None else None
        ),
        destination_latitude=(
            float(history.destination_latitude) if history.destination_latitude is not None else None
        ),
        selected_route_id=history.selected_route_id,
        query_content=history.query_content,
        query_params=history.query_content,
        result_summary=history.result_summary,
        created_at=history.created_at,
    )


def register_user(db: Session, request: UserRegisterRequest) -> UserDTO:
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise ValueError("Username already exists")

    email = request.email.strip().lower()
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        raise ValueError("Email already registered")

    latest_code = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == "register",
            EmailVerificationCode.used_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    if not latest_code:
        raise ValueError("No verification code found for this email")
    if latest_code.expires_at < datetime.now():
        raise ValueError("Verification code has expired")

    code_hash = hashlib.sha256(request.verification_code.encode()).hexdigest()
    if latest_code.code_hash != code_hash:
        raise ValueError("Invalid verification code")

    new_user = User(
        username=request.username,
        password_hash=get_password_hash(request.password),
        nickname=request.nickname or "",
        email=email,
        role="passenger",
        status="active",
    )
    db.add(new_user)

    latest_code.used_at = datetime.now()

    db.commit()
    db.refresh(new_user)
    return _user_dto(new_user)


def login_user(db: Session, request: UserLoginRequest) -> LoginResponse:
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise ValueError("Username or password error")
    if user.status != "active":
        raise ValueError("User account is disabled")

    user.last_login_at = datetime.now()
    db.commit()
    db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )
    return LoginResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_dto(user),
    )


def get_current_user(db: Session, user: User) -> UserMeResponse:
    history_count = (
        db.query(func.count(QueryHistory.history_id))
        .filter(
            QueryHistory.user_id == user.user_id,
            QueryHistory.query_type != FAVORITE_QUERY_TYPE,
        )
        .scalar()
        or 0
    )
    favorite_count = (
        db.query(func.count(QueryHistory.history_id))
        .filter(
            QueryHistory.user_id == user.user_id,
            QueryHistory.query_type == FAVORITE_QUERY_TYPE,
        )
        .scalar()
        or 0
    )
    return UserMeResponse(
        user=_user_dto(user),
        favorite_count=int(favorite_count),
        history_count=int(history_count),
    )


def update_user(db: Session, user: User, request: UserUpdateRequest) -> UserDTO:
    if request.nickname is not None:
        user.nickname = request.nickname

    if request.new_password:
        if not request.old_password or not verify_password(request.old_password, user.password_hash):
            raise ValueError("Old password error")
        user.password_hash = get_password_hash(request.new_password)

    db.commit()
    db.refresh(user)
    return _user_dto(user)


def get_user_history(db: Session, user_id: int, page: int = 1, limit: int = 20) -> QueryHistoryResponse:
    offset = (page - 1) * limit
    base_query = db.query(QueryHistory).filter(
        QueryHistory.user_id == user_id,
        QueryHistory.query_type != FAVORITE_QUERY_TYPE,
    )
    histories = (
        base_query.order_by(QueryHistory.created_at.desc(), QueryHistory.history_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = base_query.count()
    return QueryHistoryResponse(
        histories=[_history_dto(history) for history in histories],
        total=total,
    )


def add_query_history(
    db: Session,
    user_id: int | None,
    query_type: str,
    query_params: str | None = None,
    result_summary: str = "",
    **fields: Any,
) -> QueryHistoryDTO:
    if query_type == FAVORITE_QUERY_TYPE:
        raise ValueError("Reserved query type")

    new_history = QueryHistory(
        user_id=user_id,
        query_type=query_type,
        query_content=query_params,
        result_summary=result_summary,
        origin_name=fields.get("origin_name"),
        origin_longitude=fields.get("origin_longitude"),
        origin_latitude=fields.get("origin_latitude"),
        destination_name=fields.get("destination_name"),
        destination_longitude=fields.get("destination_longitude"),
        destination_latitude=fields.get("destination_latitude"),
        selected_route_id=fields.get("selected_route_id"),
    )
    db.add(new_history)
    db.commit()
    db.refresh(new_history)
    return _history_dto(new_history)


def _favorite_dto(record: QueryHistory) -> UserFavoriteDTO:
    return UserFavoriteDTO(
        favorite_id=record.history_id,
        user_id=int(record.user_id),
        favorite_type=record.query_content or "route",
        target_id=int(record.selected_route_id or 0),
        target_name=record.result_summary or "",
        created_at=record.created_at,
    )


def get_user_favorites(db: Session, user_id: int, page: int = 1, limit: int = 20) -> UserFavoriteResponse:
    offset = (page - 1) * limit
    base_query = db.query(QueryHistory).filter(
        QueryHistory.user_id == user_id,
        QueryHistory.query_type == FAVORITE_QUERY_TYPE,
    )
    favorites = (
        base_query.order_by(QueryHistory.created_at.desc(), QueryHistory.history_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return UserFavoriteResponse(
        favorites=[_favorite_dto(record) for record in favorites],
        total=base_query.count(),
    )


def add_user_favorite(db: Session, user_id: int, request: UserFavoriteRequest) -> UserFavoriteDTO:
    existing = (
        db.query(QueryHistory)
        .filter(
            QueryHistory.user_id == user_id,
            QueryHistory.query_type == FAVORITE_QUERY_TYPE,
            QueryHistory.query_content == request.favorite_type,
            QueryHistory.selected_route_id == request.target_id,
        )
        .first()
    )
    if existing:
        raise ValueError("Favorite already exists")

    record = QueryHistory(
        user_id=user_id,
        query_type=FAVORITE_QUERY_TYPE,
        selected_route_id=request.target_id,
        query_content=request.favorite_type,
        result_summary=request.target_name or "",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _favorite_dto(record)


def delete_user_favorite(db: Session, user_id: int, favorite_id: int) -> bool:
    favorite = (
        db.query(QueryHistory)
        .filter(
            QueryHistory.history_id == favorite_id,
            QueryHistory.user_id == user_id,
            QueryHistory.query_type == FAVORITE_QUERY_TYPE,
        )
        .first()
    )
    if not favorite:
        return False
    db.delete(favorite)
    db.commit()
    return True