from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class UserRegisterRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = ""
    role: Optional[str] = "passenger"

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if len(value) < 4 or len(value) > 32:
            raise ValueError("Username must be 4-32 characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 64:
            raise ValueError("Password must be 8-64 characters")
        return value

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value) > 50:
            raise ValueError("Nickname cannot exceed 50 characters")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> str:
        normalized = value or "passenger"
        if normalized not in {"passenger", "admin"}:
            raise ValueError("Role must be passenger or admin")
        return normalized


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value) > 50:
            raise ValueError("Nickname cannot exceed 50 characters")
        return value

    @model_validator(mode="after")
    def validate_password_change(self):
        if self.new_password:
            if len(self.new_password) < 8 or len(self.new_password) > 64:
                raise ValueError("New password must be 8-64 characters")
            if not self.old_password:
                raise ValueError("Old password is required to change password")
        return self


class UserDTO(BaseModel):
    user_id: int
    username: str
    nickname: Optional[str] = None
    role: str
    status: str = "active"
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(BaseModel):
    user: UserDTO
    favorite_count: int = 0
    history_count: int = 0


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserDTO


class QueryHistoryDTO(BaseModel):
    history_id: int
    user_id: Optional[int] = None
    query_type: str
    origin_name: Optional[str] = None
    origin_longitude: Optional[float] = None
    origin_latitude: Optional[float] = None
    destination_name: Optional[str] = None
    destination_longitude: Optional[float] = None
    destination_latitude: Optional[float] = None
    selected_route_id: Optional[int] = None
    query_content: Optional[str] = None
    query_params: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QueryHistoryResponse(BaseModel):
    histories: list[QueryHistoryDTO]
    total: int


class UserFavoriteDTO(BaseModel):
    favorite_id: int
    user_id: int
    favorite_type: str
    target_id: int
    target_name: str = ""
    created_at: datetime


class UserFavoriteRequest(BaseModel):
    favorite_type: str
    target_id: int
    target_name: Optional[str] = ""

    @field_validator("favorite_type")
    @classmethod
    def validate_favorite_type(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Favorite type is required")
        if len(value) > 30:
            raise ValueError("Favorite type cannot exceed 30 characters")
        return value

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Target id must be positive")
        return value


class UserFavoriteResponse(BaseModel):
    favorites: list[UserFavoriteDTO]
    total: int


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict | list] = None
    trace_id: str
    timestamp: str
