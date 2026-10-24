import secrets

from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse

SESSION_TOKEN = secrets.token_urlsafe(32)
COOKIE_NAME = "nebula_session"

def _valid(supplied):
    return secrets.compare_digest(
        (supplied or "").encode("utf-8"),
        SESSION_TOKEN.encode("utf-8"),
    )

def make_guard(port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}
    
    class LocalGuard:
        def __init__(self, app):
            self.app = app
            
        async def __call__(self, scope, receive, send):
            # Let lifespan events through
            if scope["type"] == "lifespan":
                return await self.app(scope, receive, send)
            
            if scope["type"] != "http":
                await send({"type": "websocket.close", "code": 1008})
                return
            
            headers = Headers(scope=scope)
            
            async def deny():
                await PlainTextResponse("Forbidden", status_code=403)(scope, receive, send)
            
            # blocks the DNS re-building
            if headers.get("host") not in allowed_hosts:
                return await deny()
            
            # blocks other websites from calling via fetch
            origin = headers.get("origin")
            if origin and origin not in allowed_origins:
                return await deny()
            
            request = Request(scope)
            
            # trade URL token for a cookie then clean the URL
            if _valid(request.query_params.get("token")):
                response = RedirectResponse(request.url.path, status_code=303)
                response.set_cookie(
                    COOKIE_NAME, SESSION_TOKEN,
                    httponly=True, samesite="strict",
                )
                return await response(scope, receive, send)
            
            supplied = (
                request.cookies.get(COOKIE_NAME)
                or headers.get("x-nebula-token")
            )
            if not _valid(supplied):
                return await deny()
            
            
            await self.app(scope, receive, send)
            
    return LocalGuard
    
    