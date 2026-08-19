from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exception_handlers import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from databases.database import engine
from routers import exception, frontend
from routers.api import post, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(user.router, prefix="/api/users", tags=["Users"])
app.include_router(post.router, prefix="/api/posts", tags=["Posts"])
app.include_router(frontend.router, include_in_schema=False)

# Exceptions
app.add_exception_handler(
    StarletteHTTPException, exception.general_http_exception_handler
)
app.add_exception_handler(
    RequestValidationError, exception.validation_exception_handler
)
