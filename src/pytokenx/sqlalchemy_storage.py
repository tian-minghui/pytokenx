from dataclasses import MISSING, fields
from datetime import datetime
import json
from typing import Optional, Dict
from .base import TokenStorage, TokenData

sqlalchemy_installed = True
# 可选依赖
try:
    from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Boolean
    from sqlalchemy.orm import sessionmaker, declarative_base
    Base = declarative_base()

    class TokenModel(Base):
        """Token data structure for database storage"""
        __tablename__ = 'tokens'

        id = Column(Integer, primary_key=True, autoincrement=True)
        token = Column(String(100), unique=True, nullable=False, index=True)
        token_type = Column(String(20), nullable=False, default="default")
        ext = Column(JSON, nullable=True, default={})
        created_at = Column(DateTime, nullable=False, default=datetime.now)
        expires_at = Column(DateTime, nullable=True)
        deleted_at = Column(DateTime, nullable=True)
        quota = Column(Integer, nullable=False, default=-1)
        r_quota = Column(Integer, nullable=False, default=-1)

        @classmethod
        def from_token_data(cls, token_data: TokenData) -> 'TokenModel':
            """Convert TokenData to TokenModel"""
            # 获取数据库模型中定义的字段
            model_fields = {c.name for c in cls.__table__.columns}
            
            # 创建模型实例的初始化数据
            init_data = {}
            
            # 处理基本字段
            for field in fields(token_data):
                field_name = field.name
                if field_name in model_fields:
                    # 如果字段在数据库模型中存在，直接使用
                    init_data[field_name] = getattr(token_data, field_name)
                else:
                    # 如果字段不在数据库模型中，存入ext
                    if token_data.ext is None:
                        token_data.ext = {}
                    value = getattr(token_data, field_name)
                    # 确保值是JSON可序列化的
                    try:
                        json.dumps(value)
                        token_data.ext[field_name] = value
                    except (TypeError, OverflowError):
                        # 如果值不可序列化（如datetime对象），存储其字符串表示
                        if isinstance(value, datetime):
                            token_data.ext[field_name] = value.isoformat()
                        else:
                            token_data.ext[field_name] = str(value)
            
            init_data['ext'] = token_data.ext
            return cls(**init_data)

        def to_token_data(self) -> TokenData:
            """Convert TokenModel to TokenData"""
            # 获取TokenData的字段信息
            token_data_fields = {f.name: f for f in fields(TokenData)}
            
            # 准备初始化数据
            init_data = {}
            
            # 处理基本字段
            for field_name, field in token_data_fields.items():
                if hasattr(self, field_name):
                    init_data[field_name] = getattr(self, field_name)
                elif self.ext and field_name in self.ext:
                    # 从ext中获取额外字段
                    init_data[field_name] = self.ext[field_name]
                elif field.default is not MISSING:
                    # 使用默认值
                    init_data[field_name] = field.default
                elif field.default_factory is not MISSING:
                    # 使用默认工厂函数
                    init_data[field_name] = field.default_factory()
                else:
                    # 对于没有默认值的字段，设置为None
                    init_data[field_name] = None
            
            return TokenData(**init_data)
except ImportError:
    sqlalchemy_installed = False



class SQLAlchemyTokenStorage(TokenStorage):
    def __init__(self, connection_string: str):
        if not sqlalchemy_installed:
            raise ImportError("SQLAlchemy is not installed")
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def close(self):
        if self.Session:
            self.Session.close_all()
        if self.engine:
            self.engine.dispose()

    def save_token(self, token_data: TokenData) -> None:
        session = self.Session()
        token_model = TokenModel.from_token_data(token_data)
        session.add(token_model)
        session.commit()
        session.close()

    def get_token(self, token: str) -> Optional[TokenData]:
        session = self.Session()
        token_model = (
            session.query(TokenModel).filter_by(token=token).first()
        )
        session.close()

        if token_model:
            return token_model.to_token_data()
        return None

    def delete_token(self, token: str) -> None:
        session = self.Session()
        token_model = session.query(TokenModel).filter_by(token=token).first()
        if token_model:
            token_model.deleted_at = datetime.now()
            session.commit()
        session.close()
    
    def update_token(self, token_data: TokenData) -> None:
        session = self.Session()
        token_model = session.query(TokenModel).filter_by(token=token_data.token).first()
        if token_model:
            token_model.from_token_data(token_data)
            session.commit()
        session.close()

    def add_quota(self, token: str, quota_delta: int) -> None:
        session = self.Session()
        session.query(TokenModel).filter_by(token=token).update({TokenModel.r_quota: TokenModel.r_quota + quota_delta})
        session.commit()
        session.close()
    