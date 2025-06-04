from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from jose import jwt, JWTError

from datetime import timedelta, datetime
from uuid import UUID as uuid
from os import getenv
from typing import Annotated

from .models import User, bcrypt_context
from .db import get_db

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/token")

def create_access_token(user_id: uuid, token_version: int, expires_delta: timedelta):
    expires = datetime.now() + expires_delta
    encode = {"id": str(user_id), "token_version": token_version, "exp": expires}
    token = jwt.encode(encode, getenv("SECRET_KEY"), algorithm=getenv("ALGORITHM"))
    return {"access_token": token, "token_type": "bearer"}

def authenticate_user(username: str, password: str, db: Session):
    user = db.query(User).filter(User.email == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def get_current_user(
        token: Annotated[str, Depends(oauth2_bearer)],
        db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, getenv("SECRET_KEY"), algorithms=getenv("ALGORITHM"))
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate user. Invalid JWT. {token}")

    try:
        user_id: uuid = uuid(payload.get("id"))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user. Invalid id.")

    expire = payload.get("exp")
    if datetime.now().timestamp() >= expire:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has expired. You need to log in again.")

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user. User not found.")

    token_version: int = payload.get("token_version")

    if token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate user. Invalid token version.")

    return {"id": user_id, "token_version": token_version}