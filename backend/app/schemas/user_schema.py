from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class UserRegisterRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = ""

    @field_validator('username')
    def validate_username(cls, v):
        if len(v) < 4 or len(v) > 32:
            raise ValueError('用户名长度必须在4-32字符之间')
        return v

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 64:
            raise ValueError('密码长度必须在8-64字符之间')
        return v

    @field_validator('nickname')
    def validate_nickname(cls, v):
        if v and len(v) > 32:
            raise ValueError('昵称长度不能超过32字符')
        return v

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
            raise ValueError('昵称长度不能超过32字符')
        return v

    @field_validator('new_password')
    def validate_new_password(cls, v, values):
        if v and len(v) < 8:
            raise ValueError('新密码长度必须至少8个字符')
        if v and not values.get('old_password'):
            raise ValueError('修改密码时必须提供旧密码')
        return v

class UserDTO(BaseModel):
    user_id: int
    username: str
    nickname: str
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

class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None
    trace_id: str
    timestamp: str