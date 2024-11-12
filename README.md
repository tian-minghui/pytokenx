# pytokenx

pytokenx 是一个简单易用的 Python Token 管理器。它提供了生成、验证和管理 token 的功能。

## 特性

- 生成安全的随机 token, 长度可配置
- 支持 token 过期时间设置
- 同时支持多种token类型
- token数据的持久化，目前支持文件、以及SQLAlchemy，也可以用户自定义
- 支持装饰器
- 支持用户扩展数据存储和获取

## 安装

```bash
pip install pytokenx
```
## 使用
    from pytokenx import TokenManager, FileTokenStorage, SQLAlchemyTokenStorage
    
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
        print(token_manager.get_token_data())  # {'token': 'MieZqFUchiasygXW', 'token_type': 'default', 'user_id': 'test_user', 'extra_data': {'name': 'test_name'}, 'created_at': '2024-11-07T14:12:17.389325', 'expires_at': None, 'deleted_at': None, 'is_active': True}

    my_function(token=token)

    # flask装饰器 使用示例
    @app.route("/get_code", methods=["POST"])
    @flask_token_validator(token_manager)
    def get_code():
        pass 

    # 通用装饰器
    # 1.定义获取token的方法
    def extract_token_func(*args, **kwargs) -> str:
        return args[0]

    # 使用装饰器
    @token_validator(token_manager, extract_token_func=extract_token_func)
    def my_function_custom(token):
        print(token)
    
    my_function_custom(token)


    token_manager.delete_token(token) # 删除token

