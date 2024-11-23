from datetime import timedelta
import os
import sys

from pytokenx import TokenManager, FileTokenStorage, token_validator, flask_token_validator, TokenStorage

# 使用文件存储
token_manager = TokenManager(FileTokenStorage("tokens.json"))
# sqlite存储
# token_manager = TokenManager(SQLAlchemyTokenStorage(connection_string="sqlite:///test.db"))
# 自定义存储
# class CustomTokenStorage(TokenStorage):
#     xxxx

# 生成token
token1 = token_manager.generate_token(user_id="test_user", expiry= timedelta(days=1)) 
print("generate token1 with expiry ",token1)  # MieZqFUchiasygXW
# 验证token
token_data = token_manager.validate_token(token1) 
print("validate token1  pass", token_data)

# 生成带quota的token
token2 = token_manager.generate_token(expiry= timedelta(days=1), quota=10)
print("generate token2 with quota",token2)
# 验证带quota的token, 仅验证，不扣除
token_data = token_manager.validate_token(token2, cost_quota=2 , deduct_quota=False)
print("validate token2  pass", token_data)
# 扣除quota
token_manager.deduct_quota(token2, 2)
# 获取token数据
token_data = token_manager.get_token_data(token2)
print("get token2 data",token_data)
# 使用装饰器
@token_validator(token_manager)
def my_function(token):
    print(token)
    print(token_manager.get_current_token_data())  # 从当前线程中获取当前token数据 

my_function(token=token2)


# # flask装饰器
# @app.route("/get_code", methods=["POST"])
# @flask_token_validator(token_manager)
# def get_code():
#     pass 

# 通用装饰器
# 1.定义获取token的方法
def extract_token_func(*args, **kwargs) -> str:
    return args[0]

# 使用装饰器
@token_validator(token_manager, extract_token_func=extract_token_func)
def my_function_custom(token):
    print(token)

my_function_custom(token2)


# 删除token
token_manager.delete_token(token2) 

token_manager.storage.close()



if os.path.exists("tokens.json"):
    os.remove("tokens.json")