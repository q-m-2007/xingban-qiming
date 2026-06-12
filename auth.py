"""
用户认证模块
Token认证 + 过期机制
"""

import hashlib
import time
import logging
from typing import Optional, Dict
from fastapi import HTTPException, Header

logger = logging.getLogger(__name__)

# Token存储（生产环境应用Redis）
_tokens: Dict[str, Dict] = {}

# Token过期时间（秒）
TOKEN_EXPIRE = 86400  # 24小时

# 清理计数器
_cleanup_counter = 0
_CLEANUP_INTERVAL = 100  # 每100次请求清理一次


def generate_token(user_id: int, username: str) -> str:
    """生成Token"""
    raw = f"{user_id}:{username}:{time.time()}:{hashlib.md5(str(time.time()).encode()).hexdigest()}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    _tokens[token] = {
        "user_id": user_id,
        "username": username,
        "created_at": time.time(),
        "expires_at": time.time() + TOKEN_EXPIRE,
    }
    return token


def verify_token(token: str) -> Optional[Dict]:
    """验证Token（含过期检查）"""
    global _cleanup_counter

    # 定期清理过期Token
    _cleanup_counter += 1
    if _cleanup_counter >= _CLEANUP_INTERVAL:
        _cleanup_counter = 0
        cleanup_expired_tokens()

    if token not in _tokens:
        return None

    token_data = _tokens[token]

    # 检查过期
    if time.time() > token_data.get("expires_at", 0):
        del _tokens[token]
        return None

    return token_data


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """获取当前用户（FastAPI依赖注入）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")

    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]

    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    return user


def remove_token(token: str):
    """删除Token（登出）"""
    _tokens.pop(token, None)


def cleanup_expired_tokens():
    """清理过期Token"""
    now = time.time()
    expired = [t for t, d in _tokens.items() if now > d.get("expires_at", 0)]
    for t in expired:
        del _tokens[t]
    if expired:
        logger.info(f"清理了 {len(expired)} 个过期Token")
