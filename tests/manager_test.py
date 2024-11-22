import pytest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import datetime, timedelta
from src.pytokenx import TokenManager, TokenData, TokenStorage, TokenInvalidError

class MockTokenStorage(TokenStorage):
    def __init__(self):
        self.tokens = {}
        
    def save_token(self, token_data: TokenData) -> None:
        self.tokens[token_data.token] = token_data
        
    def get_token(self, token: str) -> TokenData:
        return self.tokens.get(token)
        
    def delete_token(self, token: str) -> None:
        if token in self.tokens:
            del self.tokens[token]
            
    def cleanup_expired_tokens(self) -> None:
        now = datetime.utcnow()
        expired = [
            token for token, data in self.tokens.items() 
            if data.expires_at and data.expires_at <= now
        ]
        for token in expired:
            self.delete_token(token)
            
    def expire_token(self, token: str) -> None:
        if token in self.tokens:
            self.tokens[token].expires_at = datetime.utcnow()
    
    def update_token(self, token_data: TokenData) -> None:
        self.tokens[token_data.token] = token_data
    
    def add_quota(self, token: str, quota_delta: int) -> None:
        if token in self.tokens:
            self.tokens[token].quota += quota_delta

class TestTokenManager:
    def setup_method(self):
        self.storage = MockTokenStorage()
        self.manager = TokenManager(
            storage=self.storage,
            token_length=16,
            default_expiry=timedelta(hours=1)
        )
        
    def test_generate_token(self):
        token = self.manager.generate_token(
            user_id="test_user",
            token_type="test",
        )
        assert len(token) == 16
        token_data = self.storage.get_token(token)
        assert token_data is not None
        assert token_data.ext.get("user_id") == "test_user"
        assert token_data.token_type == "test"
        
    def test_validate_token(self):
        token = self.manager.generate_token(
            user_id="test_user",
            token_type="test"
        )
        
        token_data = self.manager.validate_token(token, "test")
        assert token_data is not None
        assert token_data.ext.get("user_id") == "test_user"
        assert token_data["token_type"] == "test"
        
    def test_validate_expired_token(self):
        token = self.manager.generate_token(
            user_id="test_user",
            expiry=timedelta(seconds=-1)
        )
        try:
            token_data = self.manager.validate_token(token)
        except TokenInvalidError:
            assert True
        
    def test_validate_invalid_token(self):
        try:
            self.manager.validate_token("invalid_token")
        except TokenInvalidError:
            assert True
        
    def test_validate_wrong_type(self):
        token = self.manager.generate_token(token_type="type1")
        try:
            self.manager.validate_token(token, "type2")
        except TokenInvalidError:
            assert True
        
    def test_delete_token(self):
        token = self.manager.generate_token()
        self.manager.delete_token(token)
        try:
            self.manager.validate_token(token)
        except TokenInvalidError:
            assert True
    
    def test_validate_quota_token(self):
        token = self.manager.generate_token(quota=10)
        data = self.manager.validate_token(token, cost_quota=5)
        assert data.r_quota == 5
        try:
            self.manager.validate_token(token, cost_quota=6)
        except TokenInvalidError:
            assert True
        
        data = self.manager.validate_token(token, cost_quota=5)
        assert data.r_quota == 0
        
    
    


