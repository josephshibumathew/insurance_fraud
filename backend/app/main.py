"""Backend FastAPI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

import logging
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.base import Base, import_models
from app.db.session import engine
from app.middleware.auth_middleware import AuthMiddleware
from app.utils.metrics import observe_request, render_metrics

settings = get_settings()
logger = logging.getLogger("fraud-api")
activity_logger = logging.getLogger("fraud-activity")


def configure_logging() -> None:
	logs_dir = Path(settings.logs_dir)
	logs_dir.mkdir(parents=True, exist_ok=True)

	formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")

	root_logger = logging.getLogger()
	root_logger.setLevel(logging.INFO)
	if not root_logger.handlers:
		stream_handler = logging.StreamHandler()
		stream_handler.setFormatter(formatter)
		root_logger.addHandler(stream_handler)

	def ensure_file_handler(logger_name: str, file_name: str) -> None:
		target_logger = logging.getLogger(logger_name)
		target_logger.setLevel(logging.INFO)
		log_path = logs_dir / file_name
		if any(isinstance(handler, logging.FileHandler) and Path(getattr(handler, "baseFilename", "")) == log_path for handler in target_logger.handlers):
			return
		file_handler = logging.FileHandler(log_path, encoding="utf-8")
		file_handler.setFormatter(formatter)
		target_logger.addHandler(file_handler)

	ensure_file_handler("fraud-api", settings.api_log_file)
	ensure_file_handler("fraud-activity", settings.activity_log_file)
	ensure_file_handler("uvicorn.error", settings.system_log_file)
	ensure_file_handler("uvicorn.access", settings.api_log_file)


configure_logging()


class RequestIDLoggingMiddleware(BaseHTTPMiddleware):
	async def dispatch(self, request: Request, call_next):
		request_id = request.headers.get(settings.request_id_header) or str(uuid.uuid4())
		request.state.request_id = request_id
		started = time.perf_counter()
		response = await call_next(request)
		elapsed_ms = (time.perf_counter() - started) * 1000
		response.headers[settings.request_id_header] = request_id
		user_info = getattr(request.state, "user", None) or {}
		user_id = user_info.get("id")
		user_role = user_info.get("role")
		client_host = request.client.host if request.client else "unknown"
		logger.info(
			"request_id=%s method=%s path=%s status=%s duration_ms=%.2f user_id=%s role=%s client_ip=%s",
			request_id,
			request.method,
			request.url.path,
			response.status_code,
			elapsed_ms,
			user_id,
			user_role,
			client_host,
		)
		activity_logger.info(
			"event=api_request request_id=%s method=%s path=%s status=%s user_id=%s role=%s duration_ms=%.2f",
			request_id,
			request.method,
			request.url.path,
			response.status_code,
			user_id,
			user_role,
			elapsed_ms,
		)
		observe_request(request.method, request.url.path, response.status_code, elapsed_ms / 1000.0)
		return response


class RateLimitMiddleware(BaseHTTPMiddleware):
	def __init__(self, app, max_per_minute: int):
		super().__init__(app)
		self.max_per_minute = max_per_minute
		self.windows: dict[str, deque[float]] = defaultdict(deque)

	async def dispatch(self, request: Request, call_next):
		key = request.client.host if request.client else "unknown"
		now = time.time()
		bucket = self.windows[key]
		while bucket and now - bucket[0] > 60:
			bucket.popleft()
		if len(bucket) >= self.max_per_minute:
			return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
		bucket.append(now)
		return await call_next(request)


class HTTPSRequiredMiddleware(BaseHTTPMiddleware):
	async def dispatch(self, request: Request, call_next):
		if settings.require_https:
			proto = request.headers.get("x-forwarded-proto", request.url.scheme)
			if proto != "https":
				return JSONResponse(status_code=400, content={"detail": "HTTPS is required"})
		return await call_next(request)


app = FastAPI(
	title=settings.app_name,
	description=settings.app_description,
	version=settings.app_version,
	docs_url="/docs",
	redoc_url="/redoc",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.backend_cors_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
app.add_middleware(RequestIDLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, max_per_minute=settings.rate_limit_per_minute)
app.add_middleware(HTTPSRequiredMiddleware)
app.add_middleware(AuthMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
	return JSONResponse(
		status_code=exc.status_code,
		content={"detail": exc.message, "request_id": getattr(request.state, "request_id", None)},
	)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	return JSONResponse(
		status_code=422,
		content={
			"detail": "Validation error",
			"errors": exc.errors(),
			"request_id": getattr(request.state, "request_id", None),
		},
	)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
	logger.exception("Unhandled error request_id=%s", getattr(request.state, "request_id", None))
	return JSONResponse(
		status_code=500,
		content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", None)},
	)


@app.on_event("startup")
def on_startup() -> None:
	import_models()
	Base.metadata.create_all(bind=engine)


app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/metrics")
def metrics_endpoint():
	content = render_metrics()
	return Response(content=content, media_type="text/plain; version=0.0.4")

