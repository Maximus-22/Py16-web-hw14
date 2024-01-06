from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from ipaddress import ip_address, ip_network


# Black list
banned_ips = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),]
    # ip_network("127.0.0.1")]


class BlackListMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host

        # Проверка, является ли запрос тестовым
        if client_ip == "testclient":
            return await call_next(request)

        # Ваш код для проверки бана по IP

        for banned_ip in banned_ips:
            if ip_address(client_ip) in banned_ip:
                return JSONResponse(status_code=403, content={"detail": "You are banned"})

        response = await call_next(request)
        return response