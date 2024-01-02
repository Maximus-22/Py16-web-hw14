import json, pickle

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, HTTPException, Depends, status, Path, Query, UploadFile, File
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.conf.config import config
from src.repository import users as rep_users
from src.schemas.user import UserResponseSchema
from src.entity.models import User, Role
from src.services.auth import auth_service
# from src.services.roles import RoleAccess


router = APIRouter(prefix="/users", tags=["users"])

cloudinary.config(cloud_name=config.CLOUDINARY_NAME, api_key=config.CLOUDINARY_API_KEY,
                  api_secret=config.CLOUDINARY_API_SECRET, secure=True,)


@router.get("/me", response_model=UserResponseSchema, dependencies=[Depends(RateLimiter(times=1, seconds=20))],)
async def get_current_user(user: User = Depends(auth_service.get_current_user)):
    """
    The get_current_user function is a dependency that will be used in the get_users function.
    It uses the auth_service module to check if there is a valid JWT token in the request header, and if so, it returns
    the user object associated with that token. If not, it raises an HTTPException.
    
    :param user: User: Get the current user
    :return: The user object
    :doc-author: Trelent
    """
    return user


# [patch] -> так як змiна тiльки одного параметра
@router.patch("/avatar", response_model=UserResponseSchema, dependencies=[Depends(RateLimiter(times=1, seconds=20))],)
async def get_current_user(file: UploadFile = File(), user: User = Depends(auth_service.get_current_user),
                           db: AsyncSession = Depends(get_db),):
    """
    The get_current_user function is a dependency that returns the current user.
    It will be used in several places, including:
    - The UserResponseSchema (to include the avatar_url)
    - The get_current_user endpoint (to return the current user)
    
    :param file: UploadFile: Get the file from the request body
    :param user: User: Get the current user
    :param db: AsyncSession: Access the database
    :param : Get the current user
    :return: The logged-in user's user object
    :doc-author: Trelent
    """
    # це значення Metadata сервiсу 
    public_id = f"Py16-Web/{user.email}"

    # у uploader.upload є параметр chunk_size (й декiлька iнших), завдяки яким можна вiдкорегувати параметри завантаженого
    # зображення, до того моменту, поки воно ще не потрапило у Сloudinary (тобто ще у пам'ятi)
    # <chunk_size> -> обмеження розмiру зображення (перед передачею до хмари) 
    resourse = cloudinary.uploader.upload(file.file, public_id=public_id, owerite=True)
    print(resourse)
    resourse_url = cloudinary.CloudinaryImage(public_id).build_url(width=250, height=250,
                                                                   crop="fill", version=resourse.get("version"))
    
    user = await rep_users.update_avatar_url(user.email, resourse_url, db)

    # вiдразу кешування <user> з новим URL для аватари
    auth_service.cache.set(user.email, pickle.dumps(user))
    auth_service.cache.expire(user.email, 300)

    return user