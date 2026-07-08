from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from app.dependencies.auth import get_db, get_current_user
from app.services.user_service import register_user, login_user, get_current_user as get_current_user_service, update_user
from app.schemas.user_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserUpdateRequest,
    UserDTO,
    LoginResponse,
    ApiResponse
)
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户"])

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

@router.post(
    "/register",
    response_model=ApiResponse,
    status_code=201,
    summary="用户注册",
    responses={
        201: {"description": "注册成功"},
        400: {"description": "参数错误"},
        409: {"description": "用户名已存在"}
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
        if str(e) == "用户名已存在":
            raise HTTPException(
                status_code=409,
                detail=build_response(40900, "用户名已存在").model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@router.post(
    "/login",
    response_model=ApiResponse,
    status_code=200,
    summary="用户登录",
    responses={
        200: {"description": "登录成功"},
        400: {"description": "用户名或密码错误"}
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
            detail=build_response(40002, str(e)).model_dump()
        )

@router.get(
    "/me",
    response_model=ApiResponse,
    status_code=200,
    summary="获取当前用户信息",
    responses={
        200: {"description": "获取成功"},
        401: {"description": "未授权"}
    }
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_info = get_current_user_service(db, current_user)
    return build_response(0, "success", user_info.model_dump())

@router.patch(
    "/me",
    response_model=ApiResponse,
    status_code=200,
    summary="修改当前用户信息",
    responses={
        200: {"description": "修改成功"},
        400: {"description": "参数错误或旧密码错误"},
        401: {"description": "未授权"}
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
            detail=build_response(40002, str(e)).model_dump()
        )