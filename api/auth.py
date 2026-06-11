"""
认证API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

import database
import auth

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    username: str
    nickname: str


class UserInfo(BaseModel):
    user_id: int
    username: str
    nickname: str


@router.post("/register", response_model=LoginResponse)
async def register(req: RegisterRequest):
    """用户注册"""
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少3个字符")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6个字符")

    user = database.create_user(req.username, req.password, req.nickname)
    if not user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    token = auth.generate_token(user["id"], user["username"])
    return LoginResponse(
        token=token,
        user_id=user["id"],
        username=user["username"],
        nickname=user.get("nickname", user["username"]),
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """用户登录"""
    user = database.get_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = auth.generate_token(user["id"], user["username"])
    return LoginResponse(
        token=token,
        user_id=user["id"],
        username=user["username"],
        nickname=user.get("nickname", user["username"]),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(auth.get_current_user)):
    """获取当前用户信息"""
    db_user = database.get_user_by_id(user["user_id"])
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserInfo(
        user_id=db_user["id"],
        username=db_user["username"],
        nickname=db_user.get("nickname", db_user["username"]),
    )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """登出"""
    if authorization:
        token = authorization
        if token.startswith("Bearer "):
            token = token[7:]
        auth.remove_token(token)
    return {"message": "已登出"}
