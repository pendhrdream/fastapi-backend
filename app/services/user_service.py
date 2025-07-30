from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status
from datetime import datetime

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserPasswordUpdate
from app.core.security import get_password_hash, verify_password
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        return self.db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()
    
    def create_user(self, user_create: UserCreate) -> User:
        existing_user = self.db.query(User).filter(
            or_(User.email == user_create.email, User.username == user_create.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_create.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            bio=user_create.bio,
            phone=user_create.phone,
            hashed_password=hashed_password,
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"User created: {db_user.username} (ID: {db_user.id})")
        return db_user
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        update_data = user_update.dict(exclude_unset=True)
        
        if "email" in update_data:
            existing_user = self.get_user_by_email(update_data["email"])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        if "username" in update_data:
            existing_user = self.get_user_by_username(update_data["username"])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"User updated: {db_user.username} (ID: {db_user.id})")
        return db_user
    
    def update_password(self, user_id: int, password_update: UserPasswordUpdate) -> bool:
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not verify_password(password_update.current_password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        db_user.hashed_password = get_password_hash(password_update.new_password)
        self.db.commit()
        
        logger.info(f"Password updated for user: {db_user.username} (ID: {db_user.id})")
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username_or_email(username)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User authenticated: {user.username} (ID: {user.id})")
        return user
    
    def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[User], int]:

        query = self.db.query(User)
        
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        total = query.count()
        
        users = query.offset(skip).limit(limit).all()
        
        return users, total
    
    def deactivate_user(self, user_id: int) -> User:
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db_user.is_active = False
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"User deactivated: {db_user.username} (ID: {db_user.id})")
        return db_user
    
    def activate_user(self, user_id: int) -> User:
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        db_user.is_active = True
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"User activated: {db_user.username} (ID: {db_user.id})")
        return db_user
