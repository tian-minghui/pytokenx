from typing import Dict, Optional
from .base import TokenData, TokenStorage
import json
import os
from datetime import datetime


class FileTokenStorage(TokenStorage):
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)
        else :
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
    
    def cleanup_expired_tokens(self) -> None:
        current_time = datetime.utcnow()
        active_tokens = {
            k: v for k, v in self.tokens.items()
            if not (v.expires_at and v.expires_at <= current_time)
        }
        self._write_tokens(active_tokens)

    def expire_token(self, token: str) -> None:
        if token in self.tokens:
            self.tokens[token].deleted_at = datetime.utcnow()
            self.tokens[token].is_active = False
            self._write_tokens(self.tokens)