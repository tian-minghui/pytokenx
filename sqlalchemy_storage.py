from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .base import TokenStorage, TokenData

Base = declarative_base()


class TokenModel(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, index=True)
    token_type = Column(String(32), default="default")
    user_id = Column(String(64))
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class SQLAlchemyTokenStorage(TokenStorage):
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_token(self, token_data: TokenData) -> None:
        session = self.Session()
        token_model = TokenModel(
            token=token_data.token,
            token_type=token_data.token_type,
            user_id=token_data.user_id,
            extra_data=token_data.extra_data,
            created_at=token_data.created_at,
            expires_at=token_data.expires_at,
            deleted_at=token_data.deleted_at,
            is_active=token_data.is_active,
        )
        session.add(token_model)
        session.commit()
        session.close()

    def get_token(self, token: str) -> Optional[TokenData]:
        session = self.Session()
        token_model = (
            session.query(TokenModel).filter_by(token=token, is_active=True).first()
        )
        session.close()

        if token_model:
            return TokenData(
                token=token_model.token,
                token_type=token_model.token_type,
                user_id=token_model.user_id,
                extra_data=token_model.extra_data,
                created_at=token_model.created_at,
                expires_at=token_model.expires_at,
                deleted_at=token_model.deleted_at,
                is_active=token_model.is_active,
            )
        return None

    def delete_token(self, token: str) -> None:
        session = self.Session()
        token_model = session.query(TokenModel).filter_by(token=token).first()
        if token_model:
            token_model.deleted_at = datetime.utcnow()
            token_model.is_active = False
            session.commit()
        session.close()

    def cleanup_expired_tokens(self) -> None:
        session = self.Session()
        current_time = datetime.utcnow()
        session.query(TokenModel).filter(TokenModel.expires_at <= current_time).update(
            {"is_active": False}
        )
        session.commit()
        session.close()

    def expire_token(self, token: str) -> None:
        session = self.Session()
        token_model = session.query(TokenModel).filter_by(token=token).first()
        if token_model:
            token_model.expires_at = datetime.utcnow()
            session.commit()
        session.close()
