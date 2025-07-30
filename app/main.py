from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import uuid

from app.core.config import settings
from app.core.logging import setup_logging, get_logger, log_error
from app.database.database import create_tables
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.v1 import auth, users

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
    A comprehensive FastAPI backend demonstrating best practices in:
    
    * **Authentication & Authorization**: JWT-based auth with role-based access
    * **Database Operations**: SQLAlchemy with proper relationships and migrations
    * **Input Validation**: Pydantic schemas with comprehensive validation
    * **Error Handling**: Structured error responses with proper HTTP status codes
    * **Logging**: Structured logging with different levels and file outputs
    * **Rate Limiting**: Redis-backed rate limiting with fallback to in-memory
    * **Security**: CORS, trusted hosts, password hashing, and input sanitization
    * **API Documentation**: Auto-generated OpenAPI docs with detailed descriptions
    * **Testing**: Comprehensive test suite with fixtures and mocking
    * **Code Quality**: Type hints, docstrings, and clean architecture
    
    ## Authentication
    
    Most endpoints require authentication. Use the `/auth/login` endpoint to get an access token,
    then include it in the `Authorization` header as `Bearer <token>`.
    
    ## Rate Limiting
    
    API requests are rate-limited to prevent abuse. Current limit: {rate_limit} requests per minute.
    Rate limit headers are included in responses.
    
    ## Error Handling
    
    All errors return structured JSON responses with appropriate HTTP status codes and detailed messages.
    """.format(rate_limit=settings.RATE_LIMIT_PER_MINUTE),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

app.add_middleware(RateLimitMiddleware, calls_per_minute=settings.RATE_LIMIT_PER_MINUTE)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Add request ID for tracking
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.warning(
        f"HTTP {exc.status_code} error: {exc.detail} | "
        f"Path: {request.url.path} | Request ID: {request_id}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": request.url.path
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.warning(
        f"Validation error: {exc.errors()} | "
        f"Path: {request.url.path} | Request ID: {request_id}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "Request validation failed",
            "validation_errors": exc.errors(),
            "request_id": request_id,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    log_error(exc, {
        "path": request.url.path,
        "method": request.method,
        "request_id": request_id
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "request_id": request_id,
            "path": request.url.path
        }
    )


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")
    # Add any cleanup logic here
    logger.info("Application shutdown completed")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "timestamp": time.time()
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "api_v1": settings.API_V1_STR,
        "features": [
            "JWT Authentication",
            "User Management",
            "Post Management",
            "Rate Limiting",
            "Input Validation",
            "Error Handling",
            "Structured Logging",
            "API Documentation"
        ]
    }


app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["Users"]
)


@app.get("/api/info", tags=["Info"])
async def api_info():
    return {
        "api_version": "v1",
        "project_name": settings.PROJECT_NAME,
        "project_version": settings.PROJECT_VERSION,
        "debug_mode": settings.DEBUG,
        "rate_limit": f"{settings.RATE_LIMIT_PER_MINUTE} requests/minute",
        "cors_origins": settings.BACKEND_CORS_ORIGINS,
        "features": {
            "authentication": "JWT Bearer tokens",
            "rate_limiting": "Redis-backed with in-memory fallback",
            "validation": "Pydantic schemas",
            "logging": "Structured logging with file output",
            "database": "SQLAlchemy with SQLite/PostgreSQL support",
            "documentation": "OpenAPI 3.0 with Swagger UI"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
