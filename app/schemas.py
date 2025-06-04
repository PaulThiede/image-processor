from pydantic import BaseModel, EmailStr, Field

from typing import Optional
from datetime import datetime
from uuid import UUID as uuid
from uuid import uuid4

class RegisterUserRequest(BaseModel):
    username: str = ""
    email: EmailStr = "name@gmail.com"
    password: str = ""

class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class ResizeTransformation(BaseModel):
    width: int
    height: int

class CropTransformation(BaseModel):
    width: int
    height: int
    x: int
    y: int

class FilterTransformation(BaseModel):
    grayscale: bool = False
    sepia: bool = False


class TransformImageRequest(BaseModel):
    resize: Optional[ResizeTransformation] = None
    crop: Optional[CropTransformation] = None
    rotate: Optional[int] = None
    format: Optional[str] = None
    filters: Optional[FilterTransformation] = None