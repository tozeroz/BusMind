from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from app.dependencies.auth import get_db, get_current_user
from app.services.user_service import register_user, login_user, get_current_user as get_current_user_service, update_user, get_user_history
from app.schemas.user_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserUpdateRequest,
    UserDTO,
    LoginResponse,
    ApiResponse,
    QueryHistoryResponse
)
from app.models.user import User

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
        if str(e) == "Username already exists":
            raise HTTPException(
                status_code=409,
                detail=build_response(40900, "Username already exists").model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
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
            detail=build_response(40002, str(e)).model_dump()
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
            detail=build_response(40002, str(e)).model_dump()
        )

@router.get(
    "/history",
    response_model=ApiResponse,
    status_code=200,
    summary="Get User Query History",
    responses={
        200: {"description": "Get success"},
        401: {"description": "Unauthorized"}
    }
)
async def get_history(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history_response = get_user_history(db, current_user.user_id, page, limit)
    return build_response(0, "success", history_response.model_dump())