"""
用户认证模块
简易token认证
"""

import hashlib
import time
from typing import Optional, Dict
from fastapi import HTTPException, Header

# Token存储（生产环境应用Redis）
_tokens: Dict[str, Dict] = {}


def generate_token(user_id: int, username: str) -> str:
    """生成token"""
    raw = f"{user_id}:{username}:{time.time()}"
    token = hashlib.md5(raw.encode()).hexdigest()
    _tokens[token] = {
        "user_id": user_id,
        "username": username,
        "created_at": time.time(),
    }
    return token


def verify_token(token: str) -> Optional[Dict]:
    """验证token"""
    return _tokens.get(token)


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """获取当前用户（FastAPI依赖注入）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")

    # 支持 "Bearer token" 格式
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]

    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    return user


def remove_token(token: str):
    """删除token（登出）"""
    _tokens.pop(token, None)
