from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_user_service, get_current_active_user, get_current_superuser,
    get_search_params, CommonQueryParams, validate_user_access
)
from app.services.user_service import UserService
from app.schemas.user import (
    User, UserUpdate, UserPasswordUpdate, UserList, UserProfile
)
from app.models.user import User as UserModel
from app.core.logging import get_logger
import math

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=UserList)
async def get_users(
    params: CommonQueryParams = Depends(get_search_params),
    is_active: bool = Query(None, description="Filter by active status"),
    current_user: UserModel = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):

    users, total = user_service.get_users(
        skip=params.skip,
        limit=params.per_page,
        search=params.search,
        is_active=is_active
    )
    
    pages = math.ceil(total / params.per_page) if total > 0 else 1
    
    logger.info(f"Users list requested by {current_user.username}, returned {len(users)} users")
    
    return UserList(
        users=users,
        total=total,
        page=params.page,
        per_page=params.per_page,
        pages=pages
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):

    # Get post count for the user
    posts_count = len(current_user.posts) if current_user.posts else 0
    
    profile_data = current_user.to_dict()
    profile_data["posts_count"] = posts_count
    
    return UserProfile(**profile_data)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):

    # Validate access
    validate_user_access(user_id, current_user)
    
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"User {user_id} accessed by {current_user.username}")
    return user


@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):

    validate_user_access(user_id, current_user)
    
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get post count for the user
    posts_count = len(user.posts) if user.posts else 0
    
    profile_data = user.to_dict()
    profile_data["posts_count"] = posts_count
    
    logger.info(f"User profile {user_id} accessed by {current_user.username}")
    return UserProfile(**profile_data)


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):

    updated_user = user_service.update_user(current_user.id, user_update)
    logger.info(f"User {current_user.username} updated their profile")
    return updated_user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):

    # Validate access
    validate_user_access(user_id, current_user)
    
    updated_user = user_service.update_user(user_id, user_update)
    logger.info(f"User {user_id} updated by {current_user.username}")
    return updated_user


@router.put("/me/password")
async def update_current_user_password(
    password_update: UserPasswordUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):

    user_service.update_password(current_user.id, password_update)
    logger.info(f"Password updated for user {current_user.username}")
    
    return {
        "message": "Password updated successfully",
        "detail": "Please use your new password for future logins"
    }


@router.post("/{user_id}/deactivate", response_model=User)
async def deactivate_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    updated_user = user_service.deactivate_user(user_id)
    logger.info(f"User {user_id} deactivated by {current_user.username}")
    return updated_user


@router.post("/{user_id}/activate", response_model=User)
async def activate_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):

    updated_user = user_service.activate_user(user_id)
    logger.info(f"User {user_id} activated by {current_user.username}")
    return updated_user


@router.get("/search/{query}", response_model=List[User])
async def search_users(
    query: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    current_user: UserModel = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):

    if len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters long"
        )
    
    users, _ = user_service.get_users(
        skip=0,
        limit=limit,
        search=query.strip()
    )
    
    logger.info(f"User search '{query}' by {current_user.username}, returned {len(users)} results")
    return users


@router.get("/stats/summary")
async def get_user_stats(
    current_user: UserModel = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):

    # Get total users
    all_users, total_users = user_service.get_users(skip=0, limit=1)
    
    # Get active users
    active_users, total_active = user_service.get_users(skip=0, limit=1, is_active=True)
    
    # Get inactive users
    inactive_users, total_inactive = user_service.get_users(skip=0, limit=1, is_active=False)
    
    stats = {
        "total_users": total_users,
        "active_users": total_active,
        "inactive_users": total_inactive,
        "activation_rate": round((total_active / total_users * 100), 2) if total_users > 0 else 0
    }
    
    logger.info(f"User stats requested by {current_user.username}")
    return stats
