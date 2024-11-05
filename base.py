from datetime import datetime, timedelta
import inspect
import secrets
import string
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any, List
from functools import wraps

class TokenValidationError(Exception):
    """Base exception for token validation errors"""

    pass


class TokenNotFoundError(TokenValidationError):
    """Token not found in request"""

    pass


class InvalidTokenError(TokenValidationError):
    """Token is invalid or expired"""

    pass


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
        self.expires_at = expires_at
        self.deleted_at = deleted_at
        self.is_active = is_active

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
    def cleanup_expired_tokens(self) -> None:
        pass

    @abstractmethod
    def expire_token(self, token: str) -> None:
        pass


class TokenManager:
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

    def generate_token(
        self,
        user_id: str = None,
        token_type: str = "default",
        extra_data: Optional[Dict] = None,
        expiry: Optional[timedelta] = None,
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

        return token_data.to_dict()

    def delete_token(self, token: str) -> None:
        self.storage.delete_token(token)


class WebAuthDecoratorAdapter(ABC):
    """Base adapter for web frameworks"""

    @abstractmethod
    def get_token_from_request(self, *args, **kwargs) -> str:
        """Extract token from the current request"""
        pass

    @abstractmethod
    def handle_error(self, error: Exception) -> Any:
        """Handle token validation errors"""
        pass

    def __init__(
        self, token_manager: Any, token_type: str = "default", inject_token: bool = True
    ):
        self.token_manager = token_manager
        self.token_type = token_type
        self.inject_token = inject_token

    def __call__(self, func: Callable) -> Callable:
        is_coroutine = inspect.iscoroutinefunction(func)

        if is_coroutine:

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    token = await self.adapter.get_token_from_request(*args, **kwargs)
                    token_data = self.token_manager.validate_token(
                        token, self.token_type
                    )

                    if not token_data:
                        raise InvalidTokenError()

                    if self.inject_token:
                        kwargs["token_data"] = token_data

                    return await func(*args, **kwargs)
                except Exception as e:
                    return self.adapter.handle_error(e)

            return async_wrapper
        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    token = self.adapter.get_token_from_request(*args, **kwargs)
                    token_data = self.token_manager.validate_token(
                        token, self.token_type
                    )

                    if not token_data:
                        raise InvalidTokenError()

                    if self.inject_token:
                        kwargs["token_data"] = token_data

                    return func(*args, **kwargs)
                except Exception as e:
                    return self.adapter.handle_error(e)

            return wrapper


def token_validator(token_manager: TokenManager, token_type: str = "default"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = kwargs.pop("token", None)
            if not token:
                raise ValueError("No token provided")

            token_data = token_manager.validate_token(token, token_type)
            if not token_data:
                raise ValueError("Invalid or expired token")

            kwargs["token_data"] = token_data
            return f(*args, **kwargs)

        return decorated_function

    return decorator
