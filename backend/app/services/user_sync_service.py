"""
User synchronization service for syncing Clerk users to database.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security.clerk_auth import ClerkUser
from ..database.models.user import User, UserStatusEnum
from ..database.repositories.user import UserRepository
from ..utils.logging import get_logger

logger = get_logger("user_sync_service")


class UserSyncService:
    """Service for syncing Clerk users to database."""

    @staticmethod
    async def sync_clerk_user(
        db: AsyncSession,
        clerk_user: ClerkUser,
        commit: bool = False
    ) -> User:
        """
        Sync a Clerk user to the database.
        
        Creates the user if they don't exist, updates last_login_at if they do.
        Uses Clerk user ID as the primary key.
        
        Args:
            db: Database session
            clerk_user: Clerk user object from authentication
            commit: Whether to commit the transaction (default: False, relies on endpoint commit)
        
        Returns:
            User: The database User object
        """
        # Check if user exists by Clerk ID
        existing_user = await UserRepository.get_by_id(db, clerk_user.id)
        
        if existing_user:
            # User exists - update last login and sync any changed data
            logger.debug(f"User {clerk_user.id} exists, updating last login")
            
            # Update fields that might have changed in Clerk
            update_data = {
                "last_login_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Update email if changed
            if clerk_user.email and clerk_user.email != existing_user.email:
                logger.info(f"Updating email for user {clerk_user.id}: {existing_user.email} -> {clerk_user.email}")
                update_data["email"] = clerk_user.email
            
            # Update full name if changed
            if clerk_user.full_name and clerk_user.full_name != existing_user.full_name:
                logger.info(f"Updating name for user {clerk_user.id}: {existing_user.full_name} -> {clerk_user.full_name}")
                update_data["full_name"] = clerk_user.full_name
            
            # Update username if changed
            if clerk_user.username and clerk_user.username != existing_user.username:
                logger.info(f"Updating username for user {clerk_user.id}: {existing_user.username} -> {clerk_user.username}")
                update_data["username"] = clerk_user.username
            
            # Update metadata with Clerk data
            clerk_metadata = {
                "clerk_id": clerk_user.id,
                "image_url": clerk_user.image_url,
                "clerk_metadata": clerk_user.metadata,
                "last_synced_at": datetime.utcnow().isoformat()
            }
            update_data["extra_metadata"] = {**existing_user.extra_metadata, **clerk_metadata}
            
            # Apply updates
            for key, value in update_data.items():
                setattr(existing_user, key, value)
            
            await db.flush()
            await db.refresh(existing_user)
            
            if commit:
                await db.commit()
            
            return existing_user
        
        else:
            # User doesn't exist - create new user
            logger.info(f"Creating new user from Clerk: {clerk_user.id} ({clerk_user.email})")
            
            # Prepare user data
            user_data = {
                "id": clerk_user.id,  # Use Clerk ID as primary key
                "email": clerk_user.email,
                "username": clerk_user.username or clerk_user.email.split("@")[0] if clerk_user.email else None,
                "full_name": clerk_user.full_name or None,
                "status": UserStatusEnum.ACTIVE,
                "last_login_at": datetime.utcnow(),
                "extra_metadata": {
                    "clerk_id": clerk_user.id,
                    "image_url": clerk_user.image_url,
                    "clerk_metadata": clerk_user.metadata,
                    "created_from_clerk": True,
                    "first_login_at": datetime.utcnow().isoformat()
                }
            }
            
            # Create user
            new_user = User(**user_data)
            db.add(new_user)
            await db.flush()
            await db.refresh(new_user)
            
            if commit:
                await db.commit()
            
            logger.info(f"Successfully created user {new_user.id}")
            return new_user

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        clerk_user: ClerkUser
    ) -> User:
        """
        Get or create a user from Clerk data.
        
        This is a convenience method that wraps sync_clerk_user.
        
        Args:
            db: Database session
            clerk_user: Clerk user object
        
        Returns:
            User: The database User object
        """
        return await UserSyncService.sync_clerk_user(db, clerk_user, commit=False)

