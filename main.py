from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
