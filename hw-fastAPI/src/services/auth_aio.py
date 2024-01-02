import json, pickle
import redis.asyncio as aioredis
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.database.db import get_db
from src.repository import users as rep_users
from src.conf.config import config


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SECRET_KEY = config.SECRET_KEY_JWT
    ALGORITHM = config.ALGORITHM
    cache = aioredis.Redis(host=config.REDIS_DOMAIN, port=config.REDIS_PORT, db=0,
                        password=config.REDIS_PASSWORD,)

    
    # Функцiя залежностi [get_redis()] для наступної функцiї [get_current_user()], яка у тому числi кешує <user>
    async def get_redis(self):
        redis = await aioredis.create_redis_pool(self.cache)
        yield redis
        redis.close()
        await redis.wait_closed()


    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)


    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)


    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


    """ Загальний вигляд JWT у Encoded:
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.\
        SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
        це три роздила, роздiленi ".".
        HEADER:ALGORITHM & TOKEN TYPE
        {"alg": "HS256", "typ": "JWT"}
        PAYLOAD:DATA
        {"sub": "user@example.com","name": "John Doe", "iat": 1516239022}
        VERIFY SIGNATURE
        HMACSHA256(base64UrlEncode(header) + "." + base64UrlEncode(payload),)
        Так от, у словник PAYLOAD:DATA самостiйно додаємо залежностi {"iat": ..., "exp": ..., "scope": ...},
        <email> юзера у цiй схемi сховано за ключем <sub> (типу <subject>). """


    # define a function to generate a new access token
    async def create_access_token(self, data: dict, expires_delta: Optional[float] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(minutes=16)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": "access_token"})
        encoded_access_token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_access_token


    # define a function to generate a new refresh token
    async def create_refresh_token(self, data: dict, expires_delta: Optional[float] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": "refresh_token"})
        encoded_refresh_token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_refresh_token


    async def decode_refresh_token(self, refresh_token: str):
        try:
            # далi у рядку параметр <algorithms=[self.ALGORITHM]> є списком з-за того, що функцiя decode може
            # принiмати декiлька типiв алгоритмiв для декодування (вона так реалiзована)
            payload = jwt.decode(refresh_token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload['scope'] == 'refresh_token':
                email = payload['sub']
                return email
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid scope for token')
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials')


    # розiбрати [token] на атоми та виокремити з нього <user.email>
    # [oauth2_scheme] це вiдповiдна дефолтна схема яку використовує [OAuth2PasswordBearer] - визначена у кодi вище
    async def get_current_user(self, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db),
                               redis: aioredis.Redis = Depends(get_redis)):
        # поки що створюмо [exeption], але вiн чекає слова [raise] :)
        credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                              detail="Could not validate credentials",
                                              headers={"WWW-Authenticate": "Bearer"},)
        
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload['scope'] != 'access_token':
                raise credentials_exception
            email = payload["sub"]
            if email is None:
                raise credentials_exception
        except JWTError as e:
            raise credentials_exception

        # Перевірка, чи є користувач у кеші Redis
        user = await redis.get(email)
        if user:
            print("User from cache")
            return json.loads(user)

        print("User from database")
        user = await rep_users.get_user_by_email(email, db)
        if user is None:
            raise credentials_exception

        # Не забути Помістити користувача в кеш Redis
        await redis.set(email, json.dumps(user), expire=300)
        return user


    async def create_email_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=2)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire})
        token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return token


    async def get_email_from_token(self, token: str):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email = payload["sub"]
            return email
        except JWTError as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Invalid token for email verification")


# створюємо екземпляр класу вiдразу тут, щоб усi <routers> отримали одну й ту саму сутнiсть
auth_service = Auth()