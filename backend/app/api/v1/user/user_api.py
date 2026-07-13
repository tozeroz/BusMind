from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from app.dependencies.auth import get_db, get_current_user
from app.services.user_service import (
    register_user,
    login_user,
    get_current_user as get_current_user_service,
    update_user,
    get_user_history,
    get_user_favorites,
    add_user_favorite,
    delete_user_favorite,
    send_register_email_code,
)
from app.services.email_service import EmailServiceConfigError, EmailServiceError
from app.schemas.user_schema import (
    UserRegisterRequest,
    SendRegisterEmailCodeRequest,
    UserLoginRequest,
    UserUpdateRequest,
    UserDTO,
    LoginResponse,
    ApiResponse,
    QueryHistoryResponse,
    UserFavoriteResponse,
    UserFavoriteRequest,
    UserFavoriteDTO
)
from app.models.user import User
from app.services.scheduler_service import get_default_scheduler

router = APIRouter(prefix="/users", tags=["User"])

def get_trace_id() -> str:
    return f"req_{uuid4().hex[:12]}"

def get_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

def build_response(code: int, message: str, data=None) -> ApiResponse:
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        trace_id=get_trace_id(),
        timestamp=get_timestamp()
    )


# English messages raised by the user service are translated into Chinese here
# so the frontend only needs to display ``detail.message`` as-is.
_USER_ERROR_MESSAGES = {
    "Username already exists": "该用户名已被占用，请更换后重试",
    "Username or password error": "账号或密码错误，请重新输入",
    "User account is disabled": "账号已被禁用，请联系管理员",
    "Old password error": "原密码错误，请重新输入",
    "Email already registered": "该邮箱已被注册，请直接登录或更换邮箱",
    "Verification code has expired": "验证码已过期，请重新获取",
    "Invalid verification code": "验证码不正确，请重新输入",
    "No verification code found for this email": "请先点击「获取验证码」",
}

_EMAIL_ERROR_MESSAGES = {
    EmailServiceConfigError: "邮件服务尚未配置，请联系管理员",
    EmailServiceError: "验证码发送失败，请稍后重试",
}


def _email_error_message(exc: Exception) -> str:
    for exc_type, message in _EMAIL_ERROR_MESSAGES.items():
        if isinstance(exc, exc_type):
            return message
    return str(exc) or "验证码发送失败，请稍后重试"

@router.post(
    "/register/email-code",
    response_model=ApiResponse,
    status_code=200,
    summary="Send Register Email Verification Code",
    responses={
        200: {"description": "Code sent"},
        400: {"description": "Invalid email or email already registered"},
        429: {"description": "Send too frequently"},
        500: {"description": "Email service unavailable"},
    }
)
async def send_register_code(
    request: SendRegisterEmailCodeRequest,
    db: Session = Depends(get_db)
):
    """Send a 6-digit verification code to *request.email* for registration.

    Codes expire after ``EMAIL_CODE_EXPIRE_MINUTES`` minutes and re-sends are
    rate-limited to one per ``EMAIL_CODE_RESEND_SECONDS`` seconds per email.
    In non-production environments where SMTP is not yet configured the
    service layer raises ``EmailServiceConfigError`` which is mapped to a
    Chinese user-facing message.
    """
    try:
        send_register_email_code(db, request.email)
        return build_response(0, "success", {"email": request.email})
    except ValueError as e:
        raw = str(e)
        # The service raises a "wait N seconds" message for rate limiting.
        if raw.startswith("Please wait"):
            raise HTTPException(
                status_code=429,
                detail=build_response(42901, raw).model_dump(),
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, _USER_ERROR_MESSAGES.get(raw, raw)).model_dump(),
        )
    except EmailServiceError as e:
        raise HTTPException(
            status_code=500,
            detail=build_response(50001, _email_error_message(e)).model_dump(),
        )


@router.post(
    "/register",
    response_model=ApiResponse,
    status_code=201,
    summary="User Register",
    responses={
        201: {"description": "Register success"},
        400: {"description": "Bad request"},
        409: {"description": "Username exists"}
    }
)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        user = register_user(db, request)
        return build_response(0, "success", user.model_dump())
    except ValueError as e:
        raw = str(e)
        if raw == "Username already exists":
            raise HTTPException(
                status_code=409,
                detail=build_response(40900, _USER_ERROR_MESSAGES[raw]).model_dump()
            )
        if raw == "Email already registered":
            raise HTTPException(
                status_code=409,
                detail=build_response(40902, _USER_ERROR_MESSAGES[raw]).model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, _USER_ERROR_MESSAGES.get(raw, raw)).model_dump()
        )

@router.post(
    "/login",
    response_model=ApiResponse,
    status_code=200,
    summary="User Login",
    responses={
        200: {"description": "Login success"},
        400: {"description": "Username or password error"}
    }
)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    try:
        login_response = login_user(db, request)
        return build_response(0, "success", login_response.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=build_response(40002, _USER_ERROR_MESSAGES.get(str(e), str(e))).model_dump()
        )

@router.get(
    "/me",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Current User",
    responses={
        200: {"description": "Get success"},
        401: {"description": "Unauthorized"}
    }
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_info = get_current_user_service(db, current_user)
    return build_response(0, "success", user_info.model_dump())


@router.post(
    "/me/refresh-arrivals",
    response_model=ApiResponse,
    status_code=202,
    summary="Trigger Bus Arrival Refresh",
)
async def refresh_arrivals_on_entry(
    current_user: User = Depends(get_current_user),
):
    """Queue a non-blocking refresh when an authenticated user enters home."""

    status = get_default_scheduler().trigger_once(cooldown_seconds=60)
    return build_response(0, "accepted", {"status": status})

@router.patch(
    "/me",
    response_model=ApiResponse,
    status_code=200,
    summary="Update Current User",
    responses={
        200: {"description": "Update success"},
        400: {"description": "Bad request or wrong old password"},
        401: {"description": "Unauthorized"}
    }
)
async def update_me(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        updated_user = update_user(db, current_user, request)
        return build_response(0, "success", updated_user.model_dump())
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=build_response(40002, _USER_ERROR_MESSAGES.get(str(e), str(e))).model_dump()
        )

@router.get(
    "/me/query-history",
    response_model=ApiResponse,
    status_code=200,
    summary="Get User Query History",
    responses={
        200: {"description": "Get success"},
        401: {"description": "Unauthorized"}
    }
)
async def get_query_history(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history_response = get_user_history(db, current_user.user_id, page, limit)
    return build_response(0, "success", history_response.model_dump())


@router.get(
    "/me/favorites",
    response_model=ApiResponse,
    status_code=200,
    summary="Get User Favorites",
    responses={
        200: {"description": "Get success"},
        401: {"description": "Unauthorized"}
    }
)
async def get_favorites(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    favorites_response = get_user_favorites(db, current_user.user_id, page, limit)
    return build_response(0, "success", favorites_response.model_dump())


@router.post(
    "/me/favorites",
    response_model=ApiResponse,
    status_code=201,
    summary="Add User Favorite",
    responses={
        201: {"description": "Add success"},
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        409: {"description": "Favorite already exists"}
    }
)
async def add_favorite(
    request: UserFavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        favorite = add_user_favorite(db, current_user.user_id, request)
        return build_response(0, "success", favorite.model_dump())
    except ValueError as e:
        if str(e) == "Favorite already exists":
            raise HTTPException(
                status_code=409,
                detail=build_response(40901, str(e)).model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )


@router.delete(
    "/me/favorites/{favorite_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Delete User Favorite",
    responses={
        200: {"description": "Delete success"},
        401: {"description": "Unauthorized"},
        404: {"description": "Favorite not found"}
    }
)
async def delete_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = delete_user_favorite(db, current_user.user_id, favorite_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=build_response(40400, "Favorite not found").model_dump()
        )
    return build_response(0, "success", None)
