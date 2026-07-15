from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import secrets


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

DEFAULT_ANALYTICS_HTML = """<script nonce="__CSP_NONCE__">
  window.op=window.op||function(){var n=[];return new Proxy(function(){arguments.length&&n.push([].slice.call(arguments))},{get:function(t,r){return"q"===r?n:function(){n.push([r].concat([].slice.call(arguments)))}} ,has:function(t,r){return"q"===r}}) }();
  window.op('init', {
    apiUrl: 'https://openpanel.soep.org/api',
    clientId: '92828103-e7ec-4acd-8584-26da574d1014',
    trackScreenViews: true,
    trackOutgoingLinks: true,
    trackAttributes: true,
    // sessionReplay: {
    //   enabled: true,
    // },
  });
</script>
<script src="https://soep.org/static/op1.js" nonce="__CSP_NONCE__" defer async></script>"""
ANALYTICS_HTML = os.getenv("ANALYTICS_HTML", DEFAULT_ANALYTICS_HTML)
ANALYTICS_ENABLED = env_bool("ENABLE_ANALYTICS", default=False) or os.getenv("ANALYTICS_HTML") is not None
VERSION = os.getenv("APP_VERSION", "0.1.3")

def analytics_html(nonce: str) -> str:
    return ANALYTICS_HTML.replace("__CSP_NONCE__", nonce)

with open("static/security.txt") as _f:
    SECURITY_TXT = _f.read()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=512)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://soep.org",
        "https://ipv4.soep.org",
        "https://ipv6.soep.org",
    ],
    allow_methods=["GET"],
)
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.globals["analytics_enabled"] = ANALYTICS_ENABLED
templates.env.globals["analytics_html"] = analytics_html
templates.env.globals["version"] = VERSION


@app.middleware("http")
async def security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(32)
    request.state.csp_nonce = nonce
    response = await call_next(request)
    if request.url.path.startswith("/images/"):
        response.headers.setdefault("Cache-Control", "public, max-age=86400, immutable")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=(), interest-cohort=()"
    )
    response.headers["Content-Security-Policy"] = (
        f"default-src 'none'; "
        f"script-src 'nonce-{nonce}'; "
        f"style-src 'nonce-{nonce}'; "
        f"img-src 'self'; "
        f"connect-src https://ipv4.soep.org https://ipv6.soep.org https://openpanel.soep.org; "
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
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": exc.status_code,
            "title": title,
            "message": message,
        },
        status_code=exc.status_code,
    )


@app.get("/.well-known/security.txt", response_class=PlainTextResponse)
async def security_txt():
    return SECURITY_TXT


@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"


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
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/dash", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dash.html")


@app.get("/matrix", response_class=HTMLResponse)
async def matrix_page(request: Request):
    return templates.TemplateResponse(request=request, name="matrix.html")


@app.get("/api/ip", response_class=PlainTextResponse)
async def api_ip(request: Request):
    return get_client_ip(request)


@app.get("/headers", response_class=HTMLResponse)
async def headers_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="headers.html",
        context={"headers": dict(request.headers)},
    )


@app.get("/api/headers")
async def api_headers(request: Request) -> dict[str, str]:
    return dict(request.headers)
