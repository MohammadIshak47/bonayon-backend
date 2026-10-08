import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppErrorBase

log = logging.getLogger("bonayon")

DESCRIPTION = (
    "Climate-smart crop planning and risk advisory for Bangladesh. Engines are transparent rule-based scoring with "
    "prototype assumptions (see app/core/agronomy.py). Data-based advisory, not a guarantee — consult your local "
    "agriculture officer for critical decisions."
)


def create_app() -> FastAPI:
    app = FastAPI(title="Bonayon API", version="0.1.0", description=DESCRIPTION)
    app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins, allow_methods=["*"], allow_headers=["*"])
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Reference"])
    def health() -> dict:
        return {"status": "ok"}

    @app.exception_handler(AppErrorBase)
    async def domain_error(_: Request, exc: AppErrorBase) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error", exc_info=exc)  # stack trace stays in server logs, never in the response
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    return app


app = create_app()
