# FastAPI Backend Demo

A comprehensive FastAPI backend application demonstrating professional development practices and code quality standards.

##  Features

### Core Functionality
- **JWT Authentication & Authorization** - Secure user authentication with role-based access control
- **User Management** - Complete CRUD operations with proper validation and security
- **Database Integration** - SQLAlchemy with PostgreSQL/SQLite support and proper relationships
- **Input Validation** - Comprehensive Pydantic schemas with custom validators
- **Error Handling** - Structured error responses with proper HTTP status codes
- **Rate Limiting** - Redis-backed rate limiting with in-memory fallback
- **Logging** - Structured logging with file outputs and different log levels
- **API Documentation** - Auto-generated OpenAPI docs with detailed descriptions

### Security Features
- Password hashing with bcrypt
- JWT token-based authentication
- CORS middleware configuration
- Trusted host middleware
- Input sanitization and validation
- Rate limiting to prevent abuse

### Code Quality
- Type hints throughout the codebase
- Comprehensive docstrings
- Clean architecture with separation of concerns
- Service layer pattern
- Dependency injection
- Comprehensive test suite
- Error handling and logging

##  Project Structure

```
fastapi-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application setup
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── security.py        # Security utilities (JWT, password hashing)
│   │   └── logging.py         # Logging configuration
│   ├── database/
│   │   └── database.py        # Database configuration and session management
│   ├── models/
│   │   ├── user.py           # User SQLAlchemy model
│   │   └── post.py           # Post SQLAlchemy model
│   ├── schemas/
│   │   ├── user.py           # User Pydantic schemas
│   │   └── post.py           # Post Pydantic schemas
│   ├── services/
│   │   └── user_service.py   # User business logic
│   ├── api/
│   │   ├── dependencies.py   # API dependencies and auth
│   │   └── v1/
│   │       ├── auth.py       # Authentication endpoints
│   │       └── users.py      # User management endpoints
│   └── middleware/
│       └── rate_limit.py     # Rate limiting middleware
├── tests/
│   └── test_auth.py          # Authentication tests
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables example
└── README.md               # This file
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, SQLite used by default)
- Redis (optional, for rate limiting)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd fastapi-backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
# Edit .env file with your configuration
```

### 5. Run the Application
```bash
# Development mode
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the main module
python app/main.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./app.db` |
| `SECRET_KEY` | JWT secret key | Auto-generated |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | `30` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |
| `DEBUG` | Debug mode | `True` |

### Database Setup

#### SQLite (Default)
No additional setup required. Database file will be created automatically.

#### PostgreSQL
1. Install PostgreSQL
2. Create a database
3. Update `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

#### Redis (Optional)
For distributed rate limiting:
1. Install Redis
2. Update `REDIS_URL` in `.env`

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

##  Authentication

### Register a New User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"
  }'
```

### Use Authentication Token
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Test Coverage
The test suite includes:
- Authentication endpoint tests
- User registration and login
- Token operations
- Input validation
- Error handling
- Edge cases and security scenarios

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - Register new user
- `POST /login` - User login
- `POST /login/oauth` - OAuth2 compatible login
- `POST /refresh` - Refresh access token
- `GET /me` - Get current user info
- `POST /logout` - User logout
- `POST /verify-token` - Verify token validity

### Users (`/api/v1/users`)
- `GET /` - List users (admin only)
- `GET /me` - Get current user profile
- `GET /{user_id}` - Get user by ID
- `PUT /me` - Update current user
- `PUT /{user_id}` - Update user (admin or self)
- `PUT /me/password` - Update password
- `POST /{user_id}/activate` - Activate user (admin only)
- `POST /{user_id}/deactivate` - Deactivate user (admin only)

### Utility
- `GET /` - API information
- `GET /health` - Health check
- `GET /api/info` - API metadata

## Security Features

### Password Security
- Minimum 8 characters
- Must contain uppercase, lowercase, digit, and special character
- Bcrypt hashing with salt

### JWT Tokens
- Configurable expiration time
- Secure secret key
- Token refresh capability

### Rate Limiting
- Configurable requests per minute
- Redis-backed for distributed systems
- In-memory fallback
- Rate limit headers in responses

### Input Validation
- Pydantic schemas with custom validators
- Email format validation
- Username pattern validation
- Phone number format validation

## Deployment

### Docker (Recommended)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use PostgreSQL for production database
- Set up Redis for rate limiting
- Configure proper environment variables
- Use HTTPS in production
- Set up monitoring and logging aggregation
- Configure backup strategies

