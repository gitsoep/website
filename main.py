from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import secrets
import socket

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://soep.org",
        "https://ipv4.soep.org",
        "https://ipv6.soep.org",
        "https://matomo.soep.org",
    ],
    allow_methods=["GET"],
)
app.mount("/images", StaticFiles(directory="images"), name="images")
templates = Jinja2Templates(directory="templates")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(32)
    request.state.csp_nonce = nonce
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'none'; "
        f"script-src 'nonce-{nonce}'; "
        f"style-src 'nonce-{nonce}'; "
        f"img-src 'self'; "
        f"connect-src https://ipv4.soep.org https://ipv6.soep.org; "
        f"frame-src 'none'; "
        f"frame-ancestors 'none'; "
        f"form-action 'none'; "
        f"base-uri 'none'"
    )
    return response

ERROR_MESSAGES = {
    400: ("Bad Request", "The server could not understand your request."),
    401: ("Unauthorized", "You need to authenticate to access this resource."),
    403: ("Forbidden", "You don't have permission to access this resource."),
    404: ("Not Found", "The page you're looking for doesn't exist."),
    405: ("Method Not Allowed", "This HTTP method is not supported for this endpoint."),
    408: ("Request Timeout", "The server timed out waiting for your request."),
    429: ("Too Many Requests", "You've sent too many requests. Please slow down."),
    500: ("Internal Server Error", "Something went wrong on our end."),
    502: ("Bad Gateway", "The server received an invalid response from an upstream server."),
    503: ("Service Unavailable", "The server is temporarily unable to handle your request."),
    504: ("Gateway Timeout", "The upstream server didn't respond in time."),
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    title, message = ERROR_MESSAGES.get(
        exc.status_code,
        (exc.detail, "An unexpected error occurred."),
    )
    return templates.TemplateResponse("error.html", {
        "request": request,
        "status_code": exc.status_code,
        "title": title,
        "message": message,
    }, status_code=exc.status_code)


@app.get("/.well-known/security.txt", response_class=PlainTextResponse)
async def security_txt():
    with open("static/security.txt") as f:
        return f.read()


def get_client_ip(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    if forwarded := request.headers.get("x-forwarded-for"):
        ip = forwarded.split(",")[0].strip()
    if client_ip := request.headers.get("client-ip"):
        ip = client_ip.strip()
    return ip


@app.get("/favicon.ico", response_class=FileResponse)
async def favicon():
    return FileResponse("images/favicon.ico", media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/ip", response_class=PlainTextResponse)
async def api_ip(request: Request):
    return get_client_ip(request)


@app.get("/headers", response_class=HTMLResponse)
async def headers_page(request: Request):
    return templates.TemplateResponse("headers.html", {
        "request": request,
        "headers": dict(request.headers),
    })


@app.get("/api/headers")
async def api_headers(request: Request):
    return dict(request.headers)
