"""
Authentication Feature Module

Provides JWT-based authentication with user registration, login,
and token management capabilities.
"""

from typing import List, Optional, Dict, Any
from app.services.feature_modules import BaseFeatureModule, FeatureModule, FeatureModuleFactory


class AuthFeatureModule(BaseFeatureModule):
    """Authentication feature module implementation"""
    
    def get_dependencies(self) -> List[str]:
        return [
            "python-jose[cryptography]==3.3.0",
            "passlib[bcrypt]==1.7.4",
            "python-multipart==0.0.6"
        ]
    
    def get_environment_vars(self) -> List[str]:
        return [
            "SECRET_KEY",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "ALGORITHM"
        ]
    
    def generate_service_code(self) -> str:
        return '''"""
Authentication Service

Handles user authentication, token generation, and password management.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import TokenData

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service for user management and JWT tokens"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        # This would typically query your database
        # For now, this is a placeholder
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            token_data = TokenData(username=username)
            return token_data
        except JWTError:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username - implement with your database"""
        # Placeholder - implement with your database logic
        pass
    
    def create_user(self, username: str, email: str, password: str) -> User:
        """Create new user account"""
        hashed_password = self.get_password_hash(password)
        # Placeholder - implement with your database logic
        pass

# Global auth service instance
auth_service = AuthService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""
Authentication Router

Provides authentication endpoints for login, registration, and token management.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.services.auth_service import auth_service
from app.schemas.auth import Token, UserCreate, UserResponse, TokenData
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = auth_service.verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    user = auth_service.get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (not disabled)"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register new user account"""
    try:
        user = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        return UserResponse.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """User login endpoint"""
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return UserResponse.from_orm(current_user)

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return '''"""
Authentication Middleware

Provides authentication middleware for protecting routes.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import auth_service

class AuthenticationMiddleware:
    """Middleware for JWT authentication"""
    
    def __init__(self):
        self.security = HTTPBearer()
    
    async def __call__(self, request: Request, call_next):
        # Skip authentication for public endpoints
        public_paths = ["/docs", "/redoc", "/openapi.json", "/auth/login", "/auth/register"]
        
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Check for authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing"
            )
        
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme"
                )
            
            # Verify token
            token_data = auth_service.verify_token(token)
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Add user info to request state
            request.state.user = token_data.username
            
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        return await call_next(request)
'''
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""
Authentication Schemas

Pydantic models for authentication requests and responses.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    """Base user schema"""
    username: str
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    """Schema for user creation"""
    password: str

class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data schema"""
    username: Optional[str] = None

class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str
'''
    
    def get_models(self) -> List[Dict[str, Any]]:
        return [{
            "name": "User",
            "fields": [
                {"name": "id", "type": "Integer", "constraints": ["primary_key"]},
                {"name": "username", "type": "String(50)", "constraints": ["unique", "required"]},
                {"name": "email", "type": "String(100)", "constraints": ["unique", "required"]},
                {"name": "hashed_password", "type": "String(255)", "constraints": ["required"]},
                {"name": "is_active", "type": "Boolean", "constraints": [], "default": True},
                {"name": "created_at", "type": "DateTime", "constraints": []},
                {"name": "updated_at", "type": "DateTime", "constraints": []}
            ]
        }]
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/auth/register", "method": "POST", "description": "Register new user"},
            {"path": "/auth/login", "method": "POST", "description": "User login"},
            {"path": "/auth/me", "method": "GET", "description": "Get current user"},
            {"path": "/auth/refresh", "method": "POST", "description": "Refresh token"}
        ]


# Register the module
FeatureModuleFactory.register(FeatureModule.AUTH, AuthFeatureModule)
