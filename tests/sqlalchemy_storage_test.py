
# 使用sqlite测试
import os
import time
import pytest
from datetime import datetime, timedelta
from ..core import TokenData, TokenStorage, SQLAlchemyTokenStorage


class TestSQLAlchemyTokenStorage:

    def setup_class(self):

        self.path = "test_tokens.db"
        self.storage = SQLAlchemyTokenStorage(connection_string=f"sqlite:///{self.path}")
    
    def teardown_class(self):
        # 关闭数据库
        self.storage.close()
        time.sleep(1)
        # 删除测试文件 
        if os.path.exists(self.path):
            print("删除测试文件")
            os.remove(self.path)

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
            token="test_delete_token",
            token_type="test",
            user_id="test_user", 
            extra_data={},
            created_at=datetime.utcnow()
        )
        
        self.storage.save_token(token_data)
        self.storage.delete_token("test_delete_token")
        
        assert self.storage.get_token("test_delete_token").deleted_at is not None
        
        
    def test_expire_token(self):
        token_data = TokenData(
            token="test_expire_token",
            token_type="test", 
            user_id="test_user",
            extra_data={},
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        self.storage.save_token(token_data)
        self.storage.expire_token("test_expire_token")
        
        retrieved_data = self.storage.get_token("test_expire_token")
        assert retrieved_data.is_active is False