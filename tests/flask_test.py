

# flask_token_validator测试

from flask import Flask
import os
import sys
import pytest
from flask import Flask
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pytokenx import flask_token_validator, TokenManager, FileTokenStorage

token = None

@pytest.fixture(scope="session")
def app():
    test_file = "test_tokens.json"
    token_manager = TokenManager(FileTokenStorage(test_file))
    global token
    token = token_manager.generate_token()
    app = create_app(token_manager)
    app.config.update({
        "TESTING": True,
    })

    # other setup can go here

    yield app

    # clean up / reset resources here
    # 清理临时目录
    if os.path.exists(test_file):
        os.remove(test_file)

@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


# 创建一个简单的Flask应用
def create_app(token_manager:TokenManager):
    app = Flask(__name__)
    
    @app.route('/hello')
    @flask_token_validator(token_manager)
    def hello():
        return token_manager.get_current_token()
    
    return app    

# 测试用例
def test_token_validate(client):
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/hello', headers=headers)
    assert response.status_code == 200
    assert response.text == token


def test_token_invalidate(client):
    headers = {'Authorization': f'Bearer 111000'}
    response = client.get('/hello', headers=headers)
    assert response.status_code == 401