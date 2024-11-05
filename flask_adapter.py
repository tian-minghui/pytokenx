

from typing import Any
from .base import InvalidTokenError, TokenNotFoundError, WebAuthDecoratorAdapter


class FlaskAdapter(WebAuthDecoratorAdapter):
    def __init__(self, token_header: str = 'Authorization', token_query_param: str = 'token'):
        from flask import request, jsonify
        self.request = request
        self.jsonify = jsonify
        self.token_header = token_header
        self.token_query_param = token_query_param
    
    def get_token_from_request(self, *args, **kwargs) -> str:
        # Try to get token from header
        token = self.request.headers.get(self.token_header)
        if token and token.startswith('Bearer '):
            token = token[7:]  # Remove 'Bearer ' prefix
        
        # Try to get token from query parameters
        if not token:
            token = self.request.args.get(self.token_query_param)
            
        # Try to get token from form data
        if not token:
            token = self.request.form.get(self.token_query_param)
            
        # Try to get token from JSON body
        if not token and self.request.is_json:
            token = self.request.json.get(self.token_query_param)
            
        if not token:
            raise TokenNotFoundError("Token not found in request")
            
        return token
    
    def handle_error(self, error: Exception) -> Any:
        if isinstance(error, TokenNotFoundError):
            return self.jsonify({'error': 'Token not found'}), 401
        elif isinstance(error, InvalidTokenError):
            return self.jsonify({'error': 'Invalid or expired token'}), 401
        return self.jsonify({'error': str(error)}), 500