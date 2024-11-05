import pytest
import os
import json
from datetime import datetime, timedelta
from pytoken.base import TokenData, TokenStorage
from pytoken.file_storage import FileTokenStorage

class TestFileTokenStorage:
    def setup_method(self):
        self.test_file = "test_tokens.json"
        self.storage = FileTokenStorage(self.test_file)
        
    def teardown_method(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
            
    def test_save_and_get_token(self):
        token_data = TokenData(
            token="test_token",
            token_type="test",
            user_id="test_user",
            extra_data={"key": "value"},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        self.storage.save_token(token_data)
        retrieved_data = self.storage.get_token("test_token")
        
        assert retrieved_data is not None
        assert retrieved_data.token == token_data.token
        assert retrieved_data.token_type == token_data.token_type
        assert retrieved_data.user_id == token_data.user_id
        assert retrieved_data.extra_data == token_data.extra_data
        assert retrieved_data.is_active == token_data.is_active
        
    def test_delete_token(self):
        token_data = TokenData(
            token="test_token",
            token_type="test",
            user_id="test_user", 
            extra_data={},
            created_at=datetime.utcnow()
        )
        
        self.storage.save_token(token_data)
        self.storage.delete_token("test_token")
        
        assert self.storage.get_token("test_token").deleted_at is not None
        
    def test_cleanup_expired_tokens(self):
        # 创建过期的token
        expired_token = TokenData(
            token="expired_token",
            token_type="test",
            user_id="test_user",
            extra_data={},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # 创建有效的token
        valid_token = TokenData(
            token="valid_token", 
            token_type="test",
            user_id="test_user",
            extra_data={},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        self.storage.save_token(expired_token)
        self.storage.save_token(valid_token)
        
        self.storage.cleanup_expired_tokens()
        
        assert self.storage.get_token("expired_token") is None
        assert self.storage.get_token("valid_token") is not None
        
    def test_expire_token(self):
        token_data = TokenData(
            token="test_token",
            token_type="test", 
            user_id="test_user",
            extra_data={},
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        self.storage.save_token(token_data)
        self.storage.expire_token("test_token")
        
        retrieved_data = self.storage.get_token("test_token")
        assert retrieved_data is not None
        assert retrieved_data.is_active is False

