import re
import redis.asyncio as aioredis
from ipaddress import ip_address, ip_network
from typing import Callable

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi_limiter import FastAPILimiter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


from src.database.db import get_db
from src.routes import auth, birthday_contacts, contacts, search_contacts, users
from src.conf.config import config

# Запуск проекту:
# uvicorn main:app --host localhost --port 8000 --reload
# де <app> - це змiнна з наступного рядка!
app = FastAPI()



# Тут визначається список доменів, які можуть надсилати запити до нашого API
# origins = ["http://localhost:3128", "http://localhost:8080"]
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    #allow_methods=["GET", "POST", "PUT", "DELETE"],
    #allow_headers=["Authorization"],
    allow_methods=["*"],
    allow_headers=["*"],)



# Black list
banned_ips = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),]
    # ip_network("127.0.0.1")]

@app.middleware("http")
async def black_list(request: Request, call_next: Callable):
    client_ip = ip_address(request.client.host)
    # if client_ip in banned_ips:
    #     return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "You are banned"})

    for banned_ip in banned_ips:
        if client_ip in banned_ip:
            # у лекції зазначаться, що <middleware> не вміє повертати json, тож потрiбно це робити за неї
            # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are banned") -> "Internal Server Error"
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "You are banned"})
        
    response = await call_next(request)
    return response



# Окрiм того, яблоки та яблочники не прокатяться
# user_agent_ban_list = [r"Macintosh", r"iPhone", r"iPad", r"AppleWebKit"]
user_agent_ban_list = [r"yandexbot", r"yandex-bot"]

@app.middleware("http")
async def user_agent_ban_middleware(request: Request, call_next: Callable):
    user_agent = request.headers.get("user-agent", "")
    
    for ban_pattern in user_agent_ban_list:
        if re.search(ban_pattern, user_agent, re.IGNORECASE):
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "You are banned"},)

    response = await call_next(request)
    return response



# routed [auth] розташовується вище за всiх
app.include_router(auth.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(search_contacts.router, prefix='/api')
app.include_router(birthday_contacts.router, prefix='/api')
app.include_router(users.router, prefix="/api")


# Ratelimit iнiцiюється тут з тегом "startup", а потiм ще додається його реалiзацiя у src/routes
@app.on_event("startup")
async def startup():
    redis_memory = await aioredis.Redis(
        host=config.REDIS_DOMAIN,
        port=config.REDIS_PORT,
        db=0,
        password=config.REDIS_PASSWORD,)
    await FastAPILimiter.init(redis_memory)


@app.get("/")
def index():
    return {"message": "Contacts Application"}


@app.get("/api/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    try:
        # Make request
        result = await db.execute(text(str("SELECT 1")))
        result = result.fetchone()
        if result is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")