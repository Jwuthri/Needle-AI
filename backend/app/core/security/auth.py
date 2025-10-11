"""
Authentication and authorization for NeedleAi.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from app.config import Settings, get_settings
from app.database.repositories import ApiKeyRepository, UserRepository
from app.exceptions import UnauthorizedError, ValidationError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password_strength(password: str, settings: Settings) -> bool:
    """Validate password meets security requirements."""
    if len(password) < settings.min_password_length:
        raise ValidationError(f"Password must be at least {settings.min_password_length} characters long")

    if settings.require_numbers and not re.search(r'\d', password):
        raise ValidationError("Password must contain at least one number")

    if settings.require_uppercase and not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter")

    if settings.require_special_chars and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character")

    return True


class AuthManager:
    """Authentication and authorization manager."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Data to encode in the token
            expires_delta: Optional custom expiration time

        Returns:
            JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token data

        Raises:
            UnauthorizedError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Token has expired")
        except jwt.JWTError:
            raise UnauthorizedError("Invalid token")

    def create_api_key(self, user_id: str, name: Optional[str] = None) -> str:
        """
        Create an API key for a user.

        Args:
            user_id: User identifier
            name: Optional name for the API key

        Returns:
            API key string
        """
        data = {
            "user_id": user_id,
            "type": "api_key",
            "name": name,
            "created_at": datetime.utcnow().isoformat()
        }

        # API keys don't expire by default
        return self.create_access_token(data, expires_delta=timedelta(days=365))

    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Verify an API key.

        Args:
            api_key: API key string

        Returns:
            API key data

        Raises:
            UnauthorizedError: If API key is invalid
        """
        payload = self.verify_token(api_key)

        if payload.get("type") != "api_key":
            raise UnauthorizedError("Invalid API key format")

        return payload


class DatabaseAuthProvider:
    """Database-backed authentication provider for production use."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository()
        self.api_key_repo = ApiKeyRepository()
        self.auth_manager = AuthManager(get_settings())
        self.settings = get_settings()

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            User data if authenticated, None otherwise
        """
        user = self.user_repo.get_by_username(self.db, username)
        if not user or not user.is_active:
            return None

        if not self.auth_manager.verify_password(password, user.password_hash):
            return None

        # Update last login
        self.user_repo.update_last_login(self.db, user.id)

        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser
        }

    async def authenticate_by_email(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with email and password.

        Args:
            email: Email address
            password: Password

        Returns:
            User data if authenticated, None otherwise
        """
        user = self.user_repo.get_by_email(self.db, email)
        if not user or not user.is_active:
            return None

        if not self.auth_manager.verify_password(password, user.password_hash):
            return None

        # Update last login
        self.user_repo.update_last_login(self.db, user.id)

        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser
        }

    async def create_user(
        self,
        username: str,
        password: str,
        email: str,
        full_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user.

        Args:
            username: Username
            password: Plain password
            email: Email address
            full_name: Optional full name

        Returns:
            User data

        Raises:
            ValidationError: If user data is invalid
        """
        # Validate password strength
        validate_password_strength(password, self.settings)

        # Check if user already exists
        if self.user_repo.get_by_username(self.db, username):
            raise ValidationError("Username already exists")

        if self.user_repo.get_by_email(self.db, email):
            raise ValidationError("Email already exists")

        # Create user
        user = self.user_repo.create(
            db=self.db,
            username=username,
            email=email,
            password_hash=self.auth_manager.get_password_hash(password),
            full_name=full_name,
            is_active=True
        )

        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active
        }

    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify an API key.

        Args:
            api_key: API key string

        Returns:
            API key data if valid, None otherwise
        """
        try:
            # First try to decode as JWT
            self.auth_manager.verify_api_key(api_key)

            # Verify against database
            db_key = self.api_key_repo.get_by_key_hash(
                self.db,
                self.auth_manager.get_password_hash(api_key)
            )

            if not db_key or not db_key.is_active:
                return None

            # Update last used
            self.api_key_repo.update_last_used(self.db, db_key.id)

            return {
                "api_key_id": str(db_key.id),
                "user_id": str(db_key.user_id),
                "name": db_key.name,
                "permissions": db_key.permissions or {}
            }
        except UnauthorizedError:
            return None

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Create an API key for a user.

        Args:
            user_id: User ID
            name: API key name
            permissions: Optional permissions dict

        Returns:
            API key data including the actual key
        """
        # Generate the API key
        key_data = {
            "user_id": user_id,
            "type": "api_key",
            "name": name,
            "created_at": datetime.utcnow().isoformat()
        }

        api_key = self.auth_manager.create_api_key(user_id, name)

        # Store in database
        db_key = self.api_key_repo.create(
            db=self.db,
            user_id=int(user_id),
            name=name,
            key_hash=self.auth_manager.get_password_hash(api_key),
            permissions=permissions or {}
        )

        return {
            "api_key_id": str(db_key.id),
            "api_key": api_key,  # Only returned once!
            "name": name
        }


# Auth provider factory
def get_auth_provider(db: Session) -> DatabaseAuthProvider:
    """Get a database auth provider instance."""
    return DatabaseAuthProvider(db)
