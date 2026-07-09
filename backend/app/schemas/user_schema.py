from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class UserRegisterRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = ""
    role: Optional[str] = "passenger"

    @field_validator('username')
    def validate_username(cls, v):
        if len(v) < 4 or len(v) > 32:
            raise ValueError('Username must be 4-32 characters')
        return v

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 64:
            raise ValueError('Password must be 8-64 characters')
        return v

    @field_validator('nickname')
    def validate_nickname(cls, v):
        if v and len(v) > 32:
            raise ValueError('Nickname cannot exceed 32 characters')
        return v

    @field_validator('role')
    def validate_role(cls, v):
        if v and v not in ['passenger', 'admin']:
            raise ValueError('Role must be passenger or admin')
        return v or 'passenger'

class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator('nickname')
    def validate_nickname(cls, v):
        if v and len(v) > 32:
            raise ValueError('Nickname cannot exceed 32 characters')
        return v

    @field_validator('new_password')
    def validate_new_password(cls, v, values):
        if v and len(v) < 8:
            raise ValueError('New password must be at least 8 characters')
        if v and not values.get('old_password'):
            raise ValueError('Old password is required to change password')
        return v

class UserDTO(BaseModel):
    user_id: int
    username: str
    nickname: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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
    user_id: int
    query_type: str
    query_params: str
    result_summary: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class QueryHistoryResponse(BaseModel):
    histories: list[QueryHistoryDTO]
    total: int

class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None
    trace_id: str
    timestamp: str