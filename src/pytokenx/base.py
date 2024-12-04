from dataclasses import dataclass, field
from datetime import datetime, timedelta
import secrets
import string
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict
from functools import wraps
import threading
import copy

QUOTA_UNLIMITED : int = float("-inf")


@dataclass
class TokenData:
    """Token data structure"""
    token: str
    token_type: str = "default"
    ext: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    quota: int = QUOTA_UNLIMITED
    r_quota: int = 0
    
    def __init__(
        self,
        token: str,
        token_type: str = "default",
        ext: Dict = {},
        created_at: datetime = datetime.now(),
        expires_at: Optional[datetime] = None,
        deleted_at: Optional[datetime] = None,
        quota: int = QUOTA_UNLIMITED,
        r_quota: Optional[int] = None,
    ):
        self.token = token
        self.token_type = token_type
        self.ext = ext
        self.created_at = created_at
        self.expires_at = expires_at  # 过期时间
        self.deleted_at = deleted_at  # 删除时间
        self.quota = quota # 总quota
        if r_quota is None:
            self.r_quota = quota
        else:
            self.r_quota = r_quota # 剩余quota

    def to_dict(self) -> Dict:
        return {
            "token": self.token,
            "token_type": self.token_type,
            "ext": self.ext,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "quota": self.quota,
            "r_quota": self.r_quota,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TokenData":
        return cls(
            token=data["token"],
            token_type=data["token_type"],
            ext=data["ext"],
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
            quota=data["quota"],
            r_quota=data["r_quota"],
        )
    
    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(f"'{key}' not found")


class TokenStorage(ABC):

    @abstractmethod
    def save_token(self, token_data: TokenData) -> None :
        '''
        自行处理token冲突处理逻辑

        raise TokenConflictError
        '''
        pass

    @abstractmethod
    def get_token(self, token: str) -> Optional[TokenData]:
        pass

    @abstractmethod
    def delete_token(self, token: str) -> None:
        pass

    @abstractmethod
    def update_token(self, token_data: TokenData) -> None:
        pass

    @abstractmethod
    def add_quota(self, token: str, quota_delta: int) -> None:
        pass

    def close(self) -> None:
        pass


class TokenManager:
    _thread_local = threading.local()

    def __init__(
        self,
        storage: TokenStorage,
        token_length: int = 16,
        quota: int = QUOTA_UNLIMITED, # token使用额度管理。
        default_expiry: Optional[timedelta] = None, # token过期时间
    ):
        self.storage = storage
        self.token_length = token_length
        self.default_expiry = default_expiry
        self.quota = quota

    def _generate_token0(self, token_length: int) -> str:
        # Generate random token
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(token_length))

    def get_current_token_data(self) -> Optional[TokenData]:
        """
        从当前线程中获取当前token数据
        """
        return getattr(self._thread_local, "token_data", None)

    def get_current_token(self) -> Optional[str]:
        """
        从当前线程中获取当前token
        """
        return getattr(self._thread_local, "token", None)

    def set_current_token_data(self, token_data: TokenData) -> None:
        setattr(self._thread_local, "token_data", token_data)
        setattr(self._thread_local, "token", token_data.token)

    def generate_token(
        self,
        token_type: str = "default",  # token类型
        expiry: Optional[timedelta] = None,  # 过期时间
        quota: int = QUOTA_UNLIMITED, # 限额
        **kwargs # 额外数据
    ) -> str:
        """
        生成token， 可以限制token类型，过期时间，额外数据, quota
        """
        while True:
            token = self._generate_token0(self.token_length)
            if not self.storage.get_token(token):
                break
        # Create token data
        token_data = TokenData(
            token=token,
            token_type=token_type,
            ext=kwargs,
            created_at=datetime.now(),
            expires_at=(
                (datetime.now() + (expiry or self.default_expiry))
                if (expiry or self.default_expiry)
                else None
            ),
            quota=quota
        )
        try:
            self.storage.save_token(token_data)
        except TokenConflictError:
            return self.generate_token(token_type, expiry, quota, **kwargs)
        return token

    def validate_token(self, token: str, 
                       token_type: str = "default", 
                       cost_quota: int = 1, # 消耗quota
                        deduct_quota: bool = True # 是否在验证成功后扣除
                        ) -> TokenData:
        """
        验证token
        return ext  生成token时传入的额外数据
        raise TokenInvalidError
        """
        # Get token data
        token_data = self.storage.get_token(token)
        token_data = copy.deepcopy(token_data)
        if not token_data or token_data.token_type != token_type:
            raise TokenInvalidError("Invalid token")

        if token_data.deleted_at and datetime.now() >= token_data.deleted_at:
            raise TokenInvalidError("Invalid token")

        if token_data.expires_at and datetime.now() >= token_data.expires_at:
            raise TokenInvalidError("Token expired")
        
        if token_data.quota != QUOTA_UNLIMITED:
            r_quota = token_data.r_quota - cost_quota
            if r_quota < 0:
                raise TokenInvalidError("Token quota exceeded")
            if deduct_quota:
                token_data.r_quota = r_quota
                self.deduct_quota(token, -cost_quota)

        self.set_current_token_data(token_data)
        return token_data
    
    def get_token_data(self, token: str) -> Optional[TokenData]:
        """
        获取token数据
        """
        return self.storage.get_token(token)

    def deduct_quota(self, token: str, quota_delta: int = 1):
        """
        操作token额度， 可以用于校验之后手动扣减，或者一些场景（执行失败）手动增加
        """
        self.storage.add_quota(token, -quota_delta)

    def update_token(self, token_data: TokenData) -> None:
        """
        更新token中数据
        """
        self.storage.update_token(token_data)

    def delete_token(self, token: str) -> None:
        """
        删除token
        """
        self.storage.delete_token(token)


def default_extract_token_func(*args, **kwargs) -> str:
    return kwargs.get("token", None)

class TokenInvalidError(Exception):
    pass

class TokenConflictError(Exception):
    pass

# 通用token验证 装饰器
def token_validator(
    token_manager: TokenManager,
    token_type: str = "default",
    cost_quota: int = 1,
    deduct_quota: bool = True,
    extract_token_func: Callable = default_extract_token_func,
):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = extract_token_func(*args, **kwargs)
            if not token:
                raise TokenInvalidError("No token provided")

            token_manager.validate_token(token, token_type, cost_quota, deduct_quota)
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
def flask_token_validator(token_manager: TokenManager, 
                          token_type: str = "default",
                          cost_quota: int = 1,
                          deduct_quota: bool = True
                          ):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # 使用原有的token_validator逻辑
                decorated_func = token_validator(
                    token_manager=token_manager,
                    token_type=token_type,
                    cost_quota=cost_quota,
                    deduct_quota=deduct_quota,
                    extract_token_func=flask_extract_token_func
                )(f)
                # 执行装饰后的函数
                return decorated_func(*args, **kwargs)
            except TokenInvalidError as e:
                # 在这里处理TokenInvalidError异常
                return {"error": str(e)}, 401 
        return wrapper

    return decorator
