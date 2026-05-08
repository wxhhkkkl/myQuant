from fastapi import Request
from fastapi.responses import JSONResponse
from jinja2 import TemplateNotFound


async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "detail": str(request.url)},
    )


async def server_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred."},
    )
