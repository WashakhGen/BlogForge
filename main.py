from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.settings import settings
from databases.database import engine
from routers import exception, frontend
from routers.api import post, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown
    await engine.dispose()


# media/profile_pics is gitignored and only created lazily on first upload;
Path(settings.PROFILE_PICS_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(user.router, prefix="/api/users", tags=["Users"])
app.include_router(post.router, prefix="/api/posts", tags=["Posts"])
app.include_router(frontend.router)

# Exceptions
app.add_exception_handler(
    StarletteHTTPException, exception.general_http_exception_handler
)
app.add_exception_handler(
    RequestValidationError, exception.validation_exception_handler
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"

    if "Referrer-Policy" not in response.headers:
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if request.url.hostname not in ("localhost", "127.0.0.1"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )

    return response