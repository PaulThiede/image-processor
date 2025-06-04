from fastapi import HTTPException, APIRouter, status, Depends, Security, Response   , UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from botocore.exceptions import BotoCoreError, NoCredentialsError
from PIL import Image as Img

from typing import Annotated
from datetime import timedelta, datetime
from os import getenv
from re import search
from io import BytesIO

from .schemas import RegisterUserRequest, TransformImageRequest
from .models import User, Image
from .auth import create_access_token, authenticate_user, get_current_user, oauth2_bearer
from .db import get_db
from .aws_integration import get_aws_connection
from .transform import transform_from_request

'''from .models import Item, User
from .schemas import CreateItemRequest, CreateUserRequest, UpdateItemRequest, UpdateUserRequest, ItemRead
from .db import get_db
from .auth import authenticate_user, create_access_token, get_current_user, oauth2_bearer
from util.sort_parser import parse_sorting'''

router = APIRouter()

user_dependency = Annotated[dict, Depends(get_current_user)]

'''
          _    _ _______ _    _ 
     /\  | |  | |__   __| |  | |
    /  \ | |  | |  | |  | |__| |
   / /\ \| |  | |  | |  |  __  |
  / ____ \ |__| |  | |  | |  | |
 /_/    \_\____/   |_|  |_|  |_|


'''


@router.get("/login", status_code=status.HTTP_200_OK)
def user(user: user_dependency, db: Session = Depends(get_db)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed.")

    new_token = create_access_token(
        user_id=user["id"],
        token_version=user["token_version"],
        expires_delta=timedelta(minutes=20)
    )

    return new_token


@router.post(
    "/token")  # curl.exe -X POST -H "Content-Type: application/json" -d '{\"title\":\"apple\"}' 'http://localhost:8000/items'
def login_for_username(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")
    token = create_access_token(user.id, user.token_version, timedelta(minutes=20))

    return token

@router.post("/register")
def register_user(register_user: RegisterUserRequest, db: Session = Depends(get_db)):
    email_taken = db.query(User).filter(User.email == register_user.email).first()

    if (email_taken):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User.create(
        username=register_user.username,
        email=str(register_user.email),
        password=register_user.password
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    new_token = create_access_token(
        user_id=user.id,
        token_version=user.token_version,
        expires_delta=timedelta(minutes=20)
    )

    return new_token


'''
   _____ __  __          _____ ______  _____ 
 |_   _|  \/  |   /\   / ____|  ____|/ ____|
   | | | \  / |  /  \ | |  __| |__  | (___  
   | | | |\/| | / /\ \| | |_ |  __|  \___ \ 
  _| |_| |  | |/ ____ \ |__| | |____ ____) |
 |_____|_|  |_/_/    \_\_____|______|_____/                                 

'''

@router.post("/uploadfile/")
async def create_upload_file(file: UploadFile, jwt: Annotated[str, Security(oauth2_bearer)], db: Session = Depends(get_db)):
    user_uuid = get_current_user(jwt, db)['id']
    aws_client = get_aws_connection()
    bucket_name = getenv("BUCKET_NAME")
    region = getenv("AWS_REGION_NAME")

    try:
        # 1. Hole alle bisherigen Bilder des Nutzers aus dem S3-Ordner
        prefix = f"images/{user_uuid}/"
        response = aws_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        existing_ids = []
        if "Contents" in response:
            for obj in response["Contents"]:
                match = search(rf"{prefix}(\d+)\.\w+", obj["Key"])
                if match:
                    existing_ids.append(int(match.group(1)))

        # 2. Ermittle nächste Bild-ID
        next_id = max(existing_ids, default=0) + 1
        file_extension = file.filename.split('.')[-1]
        s3_key = f"{prefix}{next_id}.{file_extension}"

        # 3. Lade das Bild hoch
        file_content = await file.read()
        aws_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type
        )

        print("----------------------")
        print(f"{next_id}.{file_extension}")

        image = Image.create(
            user_id=user_uuid,
            filename=f"{next_id}.{file_extension}",
        )
        db.add(image)
        db.commit()
        db.refresh(image)

        print(image.filename)

        file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        return {"url": file_url}

    except (BotoCoreError, NoCredentialsError) as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/images/{id}")
def download_image_file(id: int, jwt: Annotated[str, Security(oauth2_bearer)], db: Session = Depends(get_db)):
    user_uuid = get_current_user(jwt, db)['id']

    image = (
        db.query(Image)
        .filter(Image.user_id == user_uuid)
        .order_by(Image.created_at)  # or .order_by(Image.filename) or whatever logic you prefer
        .offset(id)
        .limit(1)
        .first()
    )

    if not image:
        raise HTTPException(status_code=404, detail=f"Image at index {id} not found.")

    filename = image.filename
    s3_key = f"images/{user_uuid}/{filename}"
    aws_client = get_aws_connection()
    print("----------------------------")
    print("S3 Key being fetched:", s3_key)

    try:
        s3_object = aws_client.get_object(Bucket=getenv("BUCKET_NAME"), Key=s3_key)
        file_content = s3_object["Body"].read()
        content_type = s3_object["ContentType"]
        return Response(content=file_content, media_type=content_type)
    except aws_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found in bucket")
    except (BotoCoreError, NoCredentialsError) as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.post("/images/{id}/transform")
def transform_image(id: int, transform: TransformImageRequest, jwt: Annotated[str, Security(oauth2_bearer)], db: Session = Depends(get_db)):
    user_uuid = get_current_user(jwt, db)['id']

    image = (
        db.query(Image)
        .filter(Image.user_id == user_uuid)
        .order_by(Image.created_at)  # or .order_by(Image.filename) or whatever logic you prefer
        .offset(id)
        .limit(1)
        .first()
    )

    if not image:
        raise HTTPException(status_code=404, detail=f"Image at index {id} not found.")

    filename = image.filename
    s3_key = f"images/{user_uuid}/{filename}"
    aws_client = get_aws_connection()
    print("----------------------------")
    print("S3 Key being fetched:", s3_key)

    try:
        s3_object = aws_client.get_object(Bucket=getenv("BUCKET_NAME"), Key=s3_key)
        file_content = s3_object["Body"].read()
        image = Img.open(BytesIO(file_content))

        image = transform_from_request(transform, image)

        # Bild in BytesIO speichern für die Response
        buffer = BytesIO()
        save_format = transform.format if transform.format else image.format or "PNG"
        image.save(buffer, format=save_format)
        buffer.seek(0)

        '''
                Andere Response:
                return Response(
                    content=buffer.read(),
                    media_type=f"image/{save_format.lower()}",  # oder image/png, etc.
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )
                '''

        return Response(content=buffer.read(), media_type=f"image/{save_format.lower()}")



    except aws_client.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found in bucket")
    except (BotoCoreError, NoCredentialsError) as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


