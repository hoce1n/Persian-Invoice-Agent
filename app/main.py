import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.config.logging_config import configure_logging
from app.config.settings import get_settings
from app.core.errors import ErrorCode, MESSAGES_FA

STATIC_DIR = Path(__file__).resolve().parent / "static"

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description="AI Invoice Automation Agent — extract Persian invoice data, generate PDFs, and route approval emails.",
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("Validation error | path=%s | errors=%s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": MESSAGES_FA[ErrorCode.VALIDATION_ERROR],
                    "errors": exc.errors(),
                }
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        logger.exception("Unhandled server error | path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": ErrorCode.UNEXPECTED, "message": MESSAGES_FA[ErrorCode.UNEXPECTED]}},
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_v1_router)
    if STATIC_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return application


app = create_app()

@app.get("/", include_in_schema=False)
async def serve_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/status", include_in_schema=False)
async def serve_status() -> FileResponse:
    return FileResponse(STATIC_DIR / "status.html")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}
