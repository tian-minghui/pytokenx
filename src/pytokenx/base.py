from datetime import datetime, timedelta
import secrets
import string
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any, List
from functools import wraps
import threading


class TokenData:
    """Token data structure"""

    def __init__(
        self,
        token: str,
        token_type: str,
        user_id: str,
        extra_data: Dict,
        created_at: datetime,
        expires_at: Optional[datetime] = None,
        deleted_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        self.token = token
        self.token_type = token_type
        self.user_id = user_id
        self.extra_data = extra_data
        self.created_at = created_at
        self.expires_at = expires_at  # 过期时间
        self.deleted_at = deleted_at  # 删除时间
        self.is_active = is_active  # 是否有效

    def to_dict(self) -> Dict:
        return {
            "token": self.token,
            "token_type": self.token_type,
            "user_id": self.user_id,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TokenData":
        return cls(
            token=data["token"],
            token_type=data["token_type"],
            user_id=data["user_id"],
            extra_data=data["extra_data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
            deleted_at=(
                datetime.fromisoformat(data["deleted_at"])
                if data.get("deleted_at")
                else None
            ),
            is_active=data["is_active"],
        )


class TokenStorage(ABC):
    @abstractmethod
    def save_token(self, token_data: TokenData) -> None:
        pass

    @abstractmethod
    def get_token(self, token: str) -> Optional[TokenData]:
        pass

    @abstractmethod
    def delete_token(self, token: str) -> None:
        pass

    @abstractmethod
    def expire_token(self, token: str) -> None:
        pass

    def close(self) -> None:
        pass


class TokenManager:
    _thread_local = threading.local()

    def __init__(
        self,
        storage: TokenStorage,
        token_length: int = 16,
        default_expiry: Optional[timedelta] = None,
    ):
        self.storage = storage
        self.token_length = token_length
        self.default_expiry = default_expiry

    def _generate_token0(self, token_length: int) -> str:
        # Generate random token
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(token_length))

    def get_current_token_data(self) -> Optional[TokenData]:
        return getattr(self._thread_local, "token_data", None)

    def get_current_token(self) -> Optional[str]:
        return getattr(self._thread_local, "token", None)

    def set_current_token_data(self, token_data: TokenData) -> None:
        setattr(self._thread_local, "token_data", token_data)
        setattr(self._thread_local, "token", token_data.token)

    def generate_token(
        self,
        user_id: str = None,
        token_type: str = "default",  # token类型
        extra_data: Optional[Dict] = None,  # 额外数据
        expiry: Optional[timedelta] = None,  # 过期时间
    ) -> str:
        while True:
            token = self._generate_token0(self.token_length)
            if not self.storage.get_token(token):
                break
        # Create token data
        token_data = TokenData(
            token=token,
            token_type=token_type,
            user_id=user_id,
            extra_data=extra_data or {},
            created_at=datetime.utcnow(),
            expires_at=(
                (datetime.utcnow() + (expiry or self.default_expiry))
                if (expiry or self.default_expiry)
                else None
            ),
            is_active=True,
        )

        # Save token
        self.storage.save_token(token_data)
        return token

    def validate_token(self, token: str, token_type: str = "default") -> Optional[Dict]:

        # Get token data
        token_data = self.storage.get_token(token)

        if not token_data:
            return None

        # Check if token is valid
        if not token_data.is_active:
            return None

        if token_data.token_type != token_type:
            return None

        if token_data.expires_at and datetime.utcnow() >= token_data.expires_at:
            self.storage.expire_token(token)
            return None
        self.set_current_token_data(token_data)
        return token_data.to_dict()

    def delete_token(self, token: str) -> None:
        self.storage.delete_token(token)


def default_extract_token_func(*args, **kwargs) -> str:
    return kwargs.get("token", None)

class TokenInvalidError(Exception):
    pass

# 通用token验证 装饰器
def token_validator(
    token_manager: TokenManager,
    token_type: str = "default",
    extract_token_func: Callable = default_extract_token_func,
):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = extract_token_func(*args, **kwargs)
            if not token:
                raise TokenInvalidError("No token provided")

            token_data = token_manager.validate_token(token, token_type)
            if not token_data:
                raise TokenInvalidError("Invalid or expired token")
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def flask_extract_token_func(*args, **kwargs):
    # Flask环境
    try:
        from flask import request
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token.split(" ")[1]
        return token
    except ImportError:
        raise ValueError("Flask is not installed")

# flask环境 装饰器  
def flask_token_validator(token_manager: TokenManager, token_type: str = "default"):
    try:
        return token_validator(token_manager, token_type, flask_extract_token_func)
    except TokenInvalidError as e:
        return {"error": str(e)}, 401
