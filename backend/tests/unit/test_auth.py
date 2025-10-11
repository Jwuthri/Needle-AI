"""
Unit tests for authentication and authorization.
"""

from datetime import timedelta

import pytest
from app.core.security.auth import (
    AuthManager,
    DatabaseAuthProvider,
    validate_password_strength,
)
from app.exceptions import UnauthorizedError, ValidationError


class TestAuthManager:
    """Test AuthManager class."""

    def test_password_hashing(self, test_settings):
        """Test password hashing and verification."""
        auth_manager = AuthManager(test_settings)
        password = "testpassword123"

        # Hash password
        hashed = auth_manager.get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 20  # bcrypt hash should be long

        # Verify correct password
        assert auth_manager.verify_password(password, hashed)

        # Verify incorrect password
        assert not auth_manager.verify_password("wrongpassword", hashed)

    def test_jwt_token_creation_and_verification(self, test_settings):
        """Test JWT token creation and verification."""
        auth_manager = AuthManager(test_settings)

        data = {
            "user_id": "123",
            "username": "testuser",
            "email": "test@example.com"
        }

        # Create token
        token = auth_manager.create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 50  # JWT should be long

        # Verify token
        payload = auth_manager.verify_token(token)
        assert payload["user_id"] == "123"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_expired_token_verification(self, test_settings):
        """Test that expired tokens are rejected."""
        auth_manager = AuthManager(test_settings)

        data = {"user_id": "123"}

        # Create token with very short expiration
        token = auth_manager.create_access_token(
            data,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Should raise UnauthorizedError
        with pytest.raises(UnauthorizedError, match="Token has expired"):
            auth_manager.verify_token(token)

    def test_invalid_token_verification(self, test_settings):
        """Test that invalid tokens are rejected."""
        auth_manager = AuthManager(test_settings)

        # Invalid token
        with pytest.raises(UnauthorizedError, match="Invalid token"):
            auth_manager.verify_token("invalid-token")

    def test_api_key_creation_and_verification(self, test_settings):
        """Test API key creation and verification."""
        auth_manager = AuthManager(test_settings)

        user_id = "123"
        name = "test-api-key"

        # Create API key
        api_key = auth_manager.create_api_key(user_id, name)
        assert isinstance(api_key, str)
        assert len(api_key) > 50

        # Verify API key
        payload = auth_manager.verify_api_key(api_key)
        assert payload["user_id"] == user_id
        assert payload["type"] == "api_key"
        assert payload["name"] == name

    def test_invalid_api_key_verification(self, test_settings):
        """Test invalid API key verification."""
        auth_manager = AuthManager(test_settings)

        # Create a regular token (not API key)
        token = auth_manager.create_access_token({"user_id": "123"})

        # Should raise UnauthorizedError
        with pytest.raises(UnauthorizedError, match="Invalid API key format"):
            auth_manager.verify_api_key(token)


class TestPasswordValidation:
    """Test password validation functions."""

    def test_password_length_validation(self, test_settings):
        """Test password length validation."""
        test_settings.min_password_length = 8

        # Valid length
        assert validate_password_strength("12345678", test_settings)

        # Too short
        with pytest.raises(ValidationError, match="at least 8 characters"):
            validate_password_strength("1234567", test_settings)

    def test_password_number_requirement(self, test_settings):
        """Test password number requirement."""
        test_settings.min_password_length = 8
        test_settings.require_numbers = True
        test_settings.require_uppercase = False
        test_settings.require_special_chars = False

        # Valid with number
        assert validate_password_strength("password1", test_settings)

        # No number
        with pytest.raises(ValidationError, match="at least one number"):
            validate_password_strength("password", test_settings)

    def test_password_uppercase_requirement(self, test_settings):
        """Test password uppercase requirement."""
        test_settings.min_password_length = 8
        test_settings.require_numbers = False
        test_settings.require_uppercase = True
        test_settings.require_special_chars = False

        # Valid with uppercase
        assert validate_password_strength("Password", test_settings)

        # No uppercase
        with pytest.raises(ValidationError, match="at least one uppercase"):
            validate_password_strength("password", test_settings)

    def test_password_special_chars_requirement(self, test_settings):
        """Test password special characters requirement."""
        test_settings.min_password_length = 8
        test_settings.require_numbers = False
        test_settings.require_uppercase = False
        test_settings.require_special_chars = True

        # Valid with special char
        assert validate_password_strength("password!", test_settings)

        # No special char
        with pytest.raises(ValidationError, match="at least one special character"):
            validate_password_strength("password", test_settings)

    def test_password_all_requirements(self, test_settings):
        """Test password with all requirements."""
        test_settings.min_password_length = 12
        test_settings.require_numbers = True
        test_settings.require_uppercase = True
        test_settings.require_special_chars = True

        # Valid complex password
        assert validate_password_strength("MyPassword123!", test_settings)

        # Missing requirements
        with pytest.raises(ValidationError):
            validate_password_strength("mypassword", test_settings)


@pytest.mark.asyncio
class TestDatabaseAuthProvider:
    """Test DatabaseAuthProvider class."""

    async def test_authenticate_user_success(self, test_db_session, user_repository, test_settings):
        """Test successful user authentication."""
        # Create a test user
        auth_manager = AuthManager(test_settings)
        password = "testpass123"
        hashed_password = auth_manager.get_password_hash(password)

        user = user_repository.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash=hashed_password,
            full_name="Test User",
            is_active=True
        )
        await test_db_session.commit()

        # Test authentication
        auth_provider = DatabaseAuthProvider(test_db_session)
        result = await auth_provider.authenticate_user("testuser", password)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["full_name"] == "Test User"
        assert result["is_active"] is True

    async def test_authenticate_user_wrong_password(self, test_db_session, user_repository, test_settings):
        """Test user authentication with wrong password."""
        # Create a test user
        auth_manager = AuthManager(test_settings)
        password = "testpass123"
        hashed_password = auth_manager.get_password_hash(password)

        user = user_repository.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash=hashed_password,
            full_name="Test User",
            is_active=True
        )
        await test_db_session.commit()

        # Test authentication with wrong password
        auth_provider = DatabaseAuthProvider(test_db_session)
        result = await auth_provider.authenticate_user("testuser", "wrongpassword")

        assert result is None

    async def test_authenticate_user_nonexistent(self, test_db_session, test_settings):
        """Test authentication of nonexistent user."""
        auth_provider = DatabaseAuthProvider(test_db_session)
        result = await auth_provider.authenticate_user("nonexistent", "password")

        assert result is None

    async def test_authenticate_user_inactive(self, test_db_session, user_repository, test_settings):
        """Test authentication of inactive user."""
        # Create an inactive test user
        auth_manager = AuthManager(test_settings)
        password = "testpass123"
        hashed_password = auth_manager.get_password_hash(password)

        user = user_repository.create(
            db=test_db_session,
            username="testuser",
            email="test@example.com",
            password_hash=hashed_password,
            full_name="Test User",
            is_active=False  # Inactive
        )
        await test_db_session.commit()

        # Test authentication
        auth_provider = DatabaseAuthProvider(test_db_session)
        result = await auth_provider.authenticate_user("testuser", password)

        assert result is None

    async def test_create_user_success(self, test_db_session, test_settings):
        """Test successful user creation."""
        auth_provider = DatabaseAuthProvider(test_db_session)

        result = await auth_provider.create_user(
            username="newuser",
            password="MyPassword123!",
            email="newuser@example.com",
            full_name="New User"
        )

        assert result["username"] == "newuser"
        assert result["email"] == "newuser@example.com"
        assert result["full_name"] == "New User"
        assert result["is_active"] is True
        assert "user_id" in result

    async def test_create_user_weak_password(self, test_db_session, test_settings):
        """Test user creation with weak password."""
        auth_provider = DatabaseAuthProvider(test_db_session)

        # Weak password should raise ValidationError
        with pytest.raises(ValidationError):
            await auth_provider.create_user(
                username="newuser",
                password="weak",
                email="newuser@example.com",
                full_name="New User"
            )

    async def test_create_user_duplicate_username(self, test_db_session, user_repository, test_settings):
        """Test user creation with duplicate username."""
        # Create existing user
        user = user_repository.create(
            db=test_db_session,
            username="existinguser",
            email="existing@example.com",
            password_hash="hashed",
            full_name="Existing User"
        )
        await test_db_session.commit()

        # Try to create user with same username
        auth_provider = DatabaseAuthProvider(test_db_session)

        with pytest.raises(ValidationError, match="Username already exists"):
            await auth_provider.create_user(
                username="existinguser",
                password="MyPassword123!",
                email="new@example.com",
                full_name="New User"
            )

    async def test_create_user_duplicate_email(self, test_db_session, user_repository, test_settings):
        """Test user creation with duplicate email."""
        # Create existing user
        user = user_repository.create(
            db=test_db_session,
            username="existinguser",
            email="existing@example.com",
            password_hash="hashed",
            full_name="Existing User"
        )
        await test_db_session.commit()

        # Try to create user with same email
        auth_provider = DatabaseAuthProvider(test_db_session)

        with pytest.raises(ValidationError, match="Email already exists"):
            await auth_provider.create_user(
                username="newuser",
                password="MyPassword123!",
                email="existing@example.com",
                full_name="New User"
            )
