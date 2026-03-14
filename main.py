from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import socket

app = FastAPI()
app.mount("/images", StaticFiles(directory="images"), name="images")
templates = Jinja2Templates(directory="templates")

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


def get_client_ip(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    if forwarded := request.headers.get("x-forwarded-for"):
        ip = forwarded.split(",")[0].strip()
    if client_ip := request.headers.get("client-ip"):
        ip = client_ip.strip()
    return ip


def resolve_addresses(hostname: str) -> dict[str, str | None]:
    ipv4 = None
    ipv6 = None
    try:
        results = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in results:
            if family == socket.AF_INET and ipv4 is None:
                ipv4 = sockaddr[0]
            elif family == socket.AF_INET6 and ipv6 is None:
                ipv6 = sockaddr[0]
    except socket.gaierror:
        pass
    return {"ipv4": ipv4, "ipv6": ipv6}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    client_ip = get_client_ip(request)

    addresses = resolve_addresses(socket.gethostname())
    server_ipv4 = addresses["ipv4"] or "not available"
    server_ipv6 = addresses["ipv6"] or "not available"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "client_ip": client_ip,
        "server_ipv4": server_ipv4,
        "server_ipv6": server_ipv6,
    })


@app.get("/api/ip")
async def api_ip(request: Request):
    return {"ip": get_client_ip(request)}


@app.get("/headers", response_class=HTMLResponse)
async def headers_page(request: Request):
    return templates.TemplateResponse("headers.html", {
        "request": request,
        "headers": dict(request.headers),
    })


@app.get("/api/headers")
async def api_headers(request: Request):
    return dict(request.headers)
