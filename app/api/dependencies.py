
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid

from app.database.database import get_db
from app.core.security import verify_token, create_credentials_exception
from app.services.user_service import UserService
from app.models.user import User
from app.core.logging import get_logger, log_request_info

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)


def get_user_service(db: Session = Depends(get_db)) -> UserService:

    return UserService(db)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_service: UserService = Depends(get_user_service)
) -> User:

    if not credentials:
        raise create_credentials_exception()
    
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise create_credentials_exception()
    
    user = user_service.get_user_by_id(int(user_id))
    if user is None:
        raise create_credentials_exception()
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not verified"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:

    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    user_service: UserService = Depends(get_user_service)
) -> Optional[User]:

    if not credentials:
        return None
    
    try:
        # Verify token
        user_id = verify_token(credentials.credentials)
        if user_id is None:
            return None
        
        # Get user from database
        user = user_service.get_user_by_id(int(user_id))
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception as e:
        logger.warning(f"Optional authentication failed: {e}")
        return None


class CommonQueryParams:
    
    def __init__(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None
    ):
        self.page = max(1, page)
        self.per_page = min(max(1, per_page), 100)  # Limit to 100 items per page
        self.search = search.strip() if search else None
        self.skip = (self.page - 1) * self.per_page


def get_pagination_params(
    page: int = 1,
    per_page: int = 20
) -> CommonQueryParams:

    return CommonQueryParams(page=page, per_page=per_page)


def get_search_params(
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None
) -> CommonQueryParams:

    return CommonQueryParams(page=page, per_page=per_page, search=search)


async def log_request(request: Request) -> str:

    request_id = str(uuid.uuid4())
    log_request_info(
        request_id=request_id,
        method=request.method,
        url=str(request.url)
    )
    return request_id


def validate_user_access(
    target_user_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:

    # Users can access their own data, superusers can access any data
    if current_user.id != target_user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user's data"
        )
    return True


def validate_post_ownership(
    post_author_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:

    if current_user.id != post_author_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this post"
        )
    return True
