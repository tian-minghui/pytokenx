import os
import sys

from pytokenx import TokenManager, FileTokenStorage, token_validator, flask_token_validator

# 使用文件存储
token_manager = TokenManager(FileTokenStorage("tokens.json"))
# sqlite存储
# token_manager = TokenManager(SQLAlchemyTokenStorage(connection_string="sqlite:///test.db"))
token = token_manager.generate_token(user_id="test_user", extra_data = {"name": "test_name"}) # 生成token
print(token)  # MieZqFUchiasygXW
token_data = token_manager.validate_token(token) # 验证token
if token_data:
    print(token_data)  # {'token': 'MieZqFUchiasygXW', 'token_type': 'default', 'user_id': 'test_user', 'extra_data': {'name': 'test_name'}, 'created_at': '2024-11-07T14:12:17.389325', 'expires_at': None, 'deleted_at': None, 'is_active': True}
else:
    print("token 无效")


# 使用装饰器
@token_validator(token_manager)
def my_function(token):
    print(token)
    print(token_manager.get_current_token_data())  # {'token': 'MieZqFUchiasygXW', 'token_type': 'default', 'user_id': 'test_user', 'extra_data': {'name': 'test_name'}, 'created_at': '2024-11-07T14:12:17.389325', 'expires_at': None, 'deleted_at': None, 'is_active': True}

my_function(token=token)

token_manager.delete_token(token) # 删除token

token_manager.storage.close()

if os.path.exists("tokens.json"):
    os.remove("tokens.json")