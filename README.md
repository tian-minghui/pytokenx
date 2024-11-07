# PyToken

PyToken 是一个简单易用的 Python Token 管理器。它提供了生成、验证和管理 token 的功能。

## 特性

- 生成安全的随机 token
- 支持 token 过期时间设置
- 同时支持多种token类型
- token数据的持久化，目前支持文件、以及SQLAlchemy，也可以用户自定义

## 安装

```bash
pip install pytoken
```
## 使用
    from pytoken import TokenManager, FileTokenStorage, SQLAlchemyTokenStorage
    
    # 使用文件存储
    token_manager = TokenManager(FileTokenStorage("tokens.json"))
    # sqlite存储
    # token_manager = TokenManager(SQLAlchemyTokenStorage(connection_string="sqlite:///test.db"))
    token = token_manager.generate_token() # 生成token
    print(token)
    token_data = token_manager.validate_token(token) # 验证token
    if token_data:
        print(token_data)
    else:
        print("token 无效")
    
    token_manager.delete_token(token) # 删除token

    # 使用装饰器
    @token_validator(token_manager)
    def my_function(token):
        print(token)

