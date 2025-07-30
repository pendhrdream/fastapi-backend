import time
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    
    def __init__(self, app, calls_per_minute: int = None):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.window_size = 60  # 1 minute in seconds
        
        # Try to connect to Redis
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()  # Test connection
            self.use_redis = True
            logger.info("Rate limiting using Redis backend")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting, using in-memory storage: {e}")
            self.use_redis = False
            self.memory_store: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next):

        if self._should_skip_rate_limit(request):
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        
        if not await self._is_allowed(client_id):
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.calls_per_minute} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        
        remaining = await self._get_remaining_calls(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _should_skip_rate_limit(self, request: Request) -> bool:

        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _get_client_id(self, request: Request) -> str:

        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    async def _is_allowed(self, client_id: str) -> bool:

        current_time = int(time.time())
        
        if self.use_redis:
            return await self._redis_is_allowed(client_id, current_time)
        else:
            return self._memory_is_allowed(client_id, current_time)
    
    async def _redis_is_allowed(self, client_id: str, current_time: int) -> bool:

        try:
            pipe = self.redis_client.pipeline()
            
            pipe.zremrangebyscore(client_id, 0, current_time - self.window_size)
            
            pipe.zcard(client_id)
            
            pipe.zadd(client_id, {str(current_time): current_time})
            
            pipe.expire(client_id, self.window_size)
            
            results = pipe.execute()
            current_requests = results[1]
            
            return current_requests < self.calls_per_minute
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return True
    
    def _memory_is_allowed(self, client_id: str, current_time: int) -> bool:

        if client_id not in self.memory_store:
            self.memory_store[client_id] = {"requests": [], "last_cleanup": current_time}
        
        client_data = self.memory_store[client_id]
        
        if current_time - client_data["last_cleanup"] > 10:
            client_data["requests"] = [
                req_time for req_time in client_data["requests"]
                if current_time - req_time < self.window_size
            ]
            client_data["last_cleanup"] = current_time
        
        if len(client_data["requests"]) >= self.calls_per_minute:
            return False
        
        client_data["requests"].append(current_time)
        return True
    
    async def _get_remaining_calls(self, client_id: str) -> int:

        current_time = int(time.time())
        
        if self.use_redis:
            try:
                current_requests = self.redis_client.zcount(
                    client_id, 
                    current_time - self.window_size, 
                    current_time
                )
                return max(0, self.calls_per_minute - current_requests)
            except Exception:
                return self.calls_per_minute
        else:
            if client_id in self.memory_store:
                valid_requests = [
                    req_time for req_time in self.memory_store[client_id]["requests"]
                    if current_time - req_time < self.window_size
                ]
                return max(0, self.calls_per_minute - len(valid_requests))
            return self.calls_per_minute


def create_rate_limit_middleware(calls_per_minute: Optional[int] = None):

    def middleware_factory(app):
        return RateLimitMiddleware(app, calls_per_minute)
    
    return middleware_factory
