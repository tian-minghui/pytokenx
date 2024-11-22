from typing import Dict, Optional
from .base import TokenData, TokenStorage
import json
import os
from datetime import datetime
from threading import RLock


class FileTokenStorage(TokenStorage):
    """
    直接使用json文件存储
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        # 判断是否包含路径
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        # 创建文件,可能要创建目录
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            print("创建目录:", dir_path)
            os.makedirs(dir_path)

        if not os.path.exists(file_path):
            print("创建文件:", file_path)
            with open(file_path, 'w') as f:
                json.dump({}, f)
        self._read_tokens()
    
    def _read_tokens(self) -> Dict:
        with open(self.file_path, 'r') as f:
            data = json.load(f)
            self.tokens = {k: TokenData.from_dict(v) for k, v in data.items()}
            return self.tokens
    
    def _write_tokens(self, tokens: Dict[str, TokenData]) -> None:
        with open(self.file_path, 'w') as f:
            json.dump({k: v.to_dict() for k, v in tokens.items()}, f)
    
    def save_token(self, token_data: TokenData) -> None:
        self.tokens[token_data.token] = token_data
        self._write_tokens(self.tokens)
    
    def get_token(self, token: str) -> Optional[TokenData]:
        return self.tokens.get(token)
    
    def delete_token(self, token: str) -> None:
        if token in self.tokens:
            self.tokens[token].deleted_at = datetime.utcnow()
            self.tokens[token].is_active = False
            self._write_tokens(self.tokens)
    
    def update_token(self, token_data):
        return self.save_token(token_data)
    
    def add_quota(self, token, quota_delta):
        if token in self.tokens:
            self.tokens[token].r_quota += quota_delta
            self._write_tokens(self.tokens)