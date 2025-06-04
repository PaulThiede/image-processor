from pydantic import BaseModel, Field
from sqlalchemy import Column, Boolean, String, TIMESTAMP, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from passlib.context import CryptContext

from datetime import datetime
from uuid import uuid4

from .db import Base

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String, index=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    token_version = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.now)

    @classmethod
    def create(cls, username: str, email: str, password: str) -> "User":
        return cls(
            username=username,
            email=email,
            token_version=0,
            hashed_password=bcrypt_context.hash(password),
            created_at=datetime.now(),
            id=uuid4()
        )

    @classmethod
    def update_password(cls, password: str):
        return bcrypt_context.hash(password)

class Image(Base):
    __tablename__ = 'images'
    __table_args__ = (UniqueConstraint("user_id", "filename", name="_user_filename_uc"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now)

    @classmethod
    def create(cls, user_id: UUID, filename: str) -> "Image":
        return cls(
            filename=filename,
            user_id=user_id,
            created_at=datetime.now(),
            id=uuid4()
        )

class Token(BaseModel):
    access_token: str
    token_type: str