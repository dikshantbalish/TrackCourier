from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BACKEND_ROOT, settings
from app.database.connection import Base, engine
import app.models  # noqa: F401
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.tracking import router as tracking_router

logger = logging.getLogger("shree_balaji.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    logger.info("Database tables are ready")
    yield


app = FastAPI(title="Shree Balaji Couriers API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret.get_secret_value(),
    session_cookie="sbc_admin_session",
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.environment == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


@app.middleware("http")
async def enforce_allowed_mutation_origins(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin:
        request_origin = f"{request.url.scheme}://{request.url.netloc}"
        allowed = {*settings.allowed_origins, request_origin}
        if origin.rstrip("/") not in allowed:
            return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    detail = [
        {
            "loc": item.get("loc", []),
            "msg": item.get("msg", "Invalid value"),
            "type": item.get("type", "value_error"),
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=error)
    return JSONResponse(
        status_code=500,
        content={"detail": "Unable to process the request right now."},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tracking_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.mount(
    "/",
    StaticFiles(directory=BACKEND_ROOT.parent / "frontend", html=True),
    name="frontend",
)
