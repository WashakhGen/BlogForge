
from fastapi import Request, status
from fastapi.exception_handlers import RequestValidationError, http_exception_handler
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

templates = Jinja2Templates(directory="templates")




### Exception Handlers

async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    
    if request.url.path.startswith("/api"):
        return await http_exception_handler(
            request,
            exception,
        )

    message = (
            exception.detail
            if exception.detail
            else "An error occurred while processing your request.Please check your request and try again."
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

# validation Error

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(
            request,
            exc,    
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message":"Invalid request, Please check your request and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )