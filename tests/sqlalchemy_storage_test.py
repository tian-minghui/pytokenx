# 使用sqlite测试
import time
import pytest
from datetime import datetime, timedelta
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.pytokenx import TokenData, SQLAlchemyTokenStorage


class TestSQLAlchemyTokenStorage:

    def setup_class(self):

        self.path = "test_tokens.db"
        self.storage = SQLAlchemyTokenStorage(
            connection_string=f"sqlite:///{self.path}"
        )

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
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        self.storage.save_token(token_data)
        retrieved_data = self.storage.get_token("test_token")

        assert retrieved_data is not None
        assert retrieved_data.token == token_data.token
        assert retrieved_data.token_type == token_data.token_type

    def test_delete_token(self):
        token_data = TokenData(
            token="test_delete_token",
            token_type="test",
            created_at=datetime.utcnow(),
        )

        self.storage.save_token(token_data)
        self.storage.delete_token("test_delete_token")

        assert self.storage.get_token("test_delete_token").deleted_at is not None

    def test_add_quota(self):
        token_data = TokenData(
            token="test_add_quota",
            token_type="test",
            created_at=datetime.utcnow(),
            quota=10
        )

        self.storage.save_token(token_data)
        self.storage.add_quota("test_add_quota", 10)

        assert self.storage.get_token("test_add_quota").r_quota == 20

