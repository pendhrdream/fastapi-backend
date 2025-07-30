import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app
from app.database.database import get_db, Base
from app.models.user import User
from app.core.security import get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "TestPass123!",
        "bio": "Test user bio",
        "phone": "+1234567890"
    }


@pytest.fixture
def existing_user(test_user_data):
    db = TestingSessionLocal()
    
    db.query(User).filter(User.email == test_user_data["email"]).delete()
    db.commit()
    
    hashed_password = get_password_hash(test_user_data["password"])
    db_user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        full_name=test_user_data["full_name"],
        hashed_password=hashed_password,
        bio=test_user_data["bio"],
        phone=test_user_data["phone"],
        is_active=True,
        is_verified=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    yield db_user
    
    db.query(User).filter(User.id == db_user.id).delete()
    db.commit()
    db.close()


class TestUserRegistration:
    
    def test_register_new_user_success(self, test_user_data):
        db = TestingSessionLocal()
        db.query(User).filter(User.email == test_user_data["email"]).delete()
        db.commit()
        db.close()
        
        response = client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "hashed_password" not in data
        assert "id" in data
        assert data["is_active"] is True
        assert data["is_verified"] is False
    
    def test_register_duplicate_email(self, existing_user, test_user_data):
        response = client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Email already registered" in data["detail"]
    
    def test_register_duplicate_username(self, existing_user, test_user_data):
        new_user_data = test_user_data.copy()
        new_user_data["email"] = "different@example.com"
        
        response = client.post("/api/v1/auth/register", json=new_user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Username already taken" in data["detail"]
    
    def test_register_invalid_email(self, test_user_data):
        invalid_data = test_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_errors" in data
    
    def test_register_weak_password(self, test_user_data):
        weak_passwords = [
            "weak",
            "weakpassword",
            "WeakPassword",
            "WeakPassword123",
        ]
        
        for weak_password in weak_passwords:
            invalid_data = test_user_data.copy()
            invalid_data["password"] = weak_password
            invalid_data["email"] = f"test{weak_password}@example.com"
            invalid_data["username"] = f"user{weak_password}"
            
            response = client.post("/api/v1/auth/register", json=invalid_data)
            assert response.status_code == 422
    
    def test_register_invalid_username(self, test_user_data):
        invalid_usernames = [
            "ab",
            "a" * 51,
            "user@name",
            "user name",
        ]
        
        for invalid_username in invalid_usernames:
            invalid_data = test_user_data.copy()
            invalid_data["username"] = invalid_username
            invalid_data["email"] = f"{invalid_username}@example.com"
            
            response = client.post("/api/v1/auth/register", json=invalid_data)
            assert response.status_code == 422


class TestUserLogin:
    
    def test_login_success_with_username(self, existing_user, test_user_data):
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        assert data["user"]["username"] == test_user_data["username"]
    
    def test_login_success_with_email(self, existing_user, test_user_data):
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user_data["email"]
    
    def test_login_invalid_credentials(self, existing_user, test_user_data):
        login_data = {
            "username": test_user_data["username"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Incorrect username or password" in data["detail"]
    
    def test_login_nonexistent_user(self):
        login_data = {
            "username": "nonexistent",
            "password": "password"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "Incorrect username or password" in data["detail"]
    
    def test_login_inactive_user(self, existing_user, test_user_data):
        db = TestingSessionLocal()
        existing_user.is_active = False
        db.commit()
        
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 403
        data = response.json()
        assert "Inactive user" in data["detail"]
        
        existing_user.is_active = True
        db.commit()
        db.close()


class TestOAuthLogin:

    def test_oauth_login_success(self, existing_user, test_user_data):
        form_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login/oauth", data=form_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_oauth_login_invalid_credentials(self, existing_user, test_user_data):
        form_data = {
            "username": test_user_data["username"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login/oauth", data=form_data)
        
        assert response.status_code == 401


class TestTokenOperations:
    
    def get_auth_headers(self, existing_user, test_user_data):
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_current_user_info(self, existing_user, test_user_data):
        headers = self.get_auth_headers(existing_user, test_user_data)
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
    
    def test_refresh_token(self, existing_user, test_user_data):
        headers = self.get_auth_headers(existing_user, test_user_data)
        
        response = client.post("/api/v1/auth/refresh", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_verify_token(self, existing_user, test_user_data):
        headers = self.get_auth_headers(existing_user, test_user_data)
        
        response = client.post("/api/v1/auth/verify-token", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["username"] == test_user_data["username"]
    
    def test_logout(self, existing_user, test_user_data):
        headers = self.get_auth_headers(existing_user, test_user_data)
        
        response = client.post("/api/v1/auth/logout", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out" in data["message"]
    
    def test_invalid_token(self):
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]
    
    def test_missing_token(self):
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]


class TestErrorHandling:
    
    def test_malformed_request_body(self):
        response = client.post("/api/v1/auth/register", json={"invalid": "data"})
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_errors" in data
    
    def test_missing_required_fields(self):
        incomplete_data = {
            "email": "test@example.com"
        }
        
        response = client.post("/api/v1/auth/register", json=incomplete_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "validation_errors" in data
    
    @patch('app.services.user_service.UserService.create_user')
    def test_database_error_handling(self, mock_create_user, test_user_data):
        mock_create_user.side_effect = Exception("Database error")
        
        response = client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Registration failed" in data["detail"]
