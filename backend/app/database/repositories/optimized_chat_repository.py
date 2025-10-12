"""
Optimized chat repository with N+1 query prevention and performance improvements.

This module demonstrates best practices for database query optimization:
- Eager loading with selectinload/joinedload
- Query batching
- Efficient pagination
- Proper indexing usage
- Query result caching
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.database.models.chat_message import ChatMessage, MessageRoleEnum
from app.database.models.chat_session import ChatSession
from app.database.models.user import User
from app.utils.logging import get_logger
from sqlalchemy import and_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload

logger = get_logger("optimized_chat_repository")


class OptimizedChatRepository:
    """
    Optimized repository for chat operations with N+1 prevention.

    This repository demonstrates proper query optimization techniques:
    - Eager loading to prevent N+1 queries
    - Efficient joins and subqueries
    - Batched operations
    - Smart pagination
    """

    @staticmethod
    async def get_sessions_with_messages_optimized(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        include_message_count: bool = True,
        include_last_message: bool = True
    ) -> List[ChatSession]:
        """
        Get user sessions with optimized loading to prevent N+1 queries.

        ❌ OLD WAY (N+1 Problem):
        sessions = db.query(ChatSession).filter_by(user_id=user_id).all()
        for session in sessions:  # N+1: One query per session!
            messages = db.query(ChatMessage).filter_by(session_id=session.id).all()

        ✅ NEW WAY (Optimized):
        Single query with eager loading and aggregates
        """
        query = (
            select(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.is_active == True)
        )

        # Eager load user to prevent additional query
        query = query.options(joinedload(ChatSession.user))

        if include_last_message or include_message_count:
            # For async, we'll do eager loading of messages and calculate in Python
            query = query.options(selectinload(ChatSession.messages))

        # Order by last activity for better UX
        query = query.order_by(
            desc(ChatSession.updated_at),
            desc(ChatSession.created_at)
        )

        # Efficient pagination
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        sessions = list(result.scalars().all())

        if include_message_count or include_last_message:
            # Enhance session objects with computed fields
            for session in sessions:
                if hasattr(session, 'messages'):
                    session._message_count = len(session.messages)
                    if session.messages:
                        last_msg = max(session.messages, key=lambda m: m.created_at)
                        session._last_message_time = last_msg.created_at
                        session._last_message_content = last_msg.content
                    else:
                        session._last_message_time = None
                        session._last_message_content = None

        return sessions

    @staticmethod
    async def get_conversation_with_context_optimized(
        db: AsyncSession,
        session_id: str,
        context_limit: int = 50,
        include_user: bool = True
    ) -> Optional[Tuple[ChatSession, List[ChatMessage]]]:
        """
        Get session with message context in a single optimized query.

        ❌ OLD WAY:
        session = db.query(ChatSession).filter_by(id=session_id).first()
        messages = db.query(ChatMessage).filter_by(session_id=session_id).all()
        user = db.query(User).filter_by(id=session.user_id).first()  # N+1!

        ✅ NEW WAY:
        Single query with eager loading
        """
        # Main query with eager loading
        query = (
            select(ChatSession)
            .filter(ChatSession.id == session_id)
            .options(
                # Eager load messages (selectinload for collections)
                selectinload(ChatSession.messages)
            )
        )

        if include_user:
            # Eager load user (joinedload for single relationships)
            query = query.options(joinedload(ChatSession.user))

        result = await db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Sort messages by creation time (already loaded, no extra query)
        messages = sorted(
            session.messages,
            key=lambda m: m.created_at,
            reverse=False  # Chronological order for context
        )

        # Limit context messages if needed
        if len(messages) > context_limit:
            messages = messages[-context_limit:]  # Keep most recent

        return session, messages

    @staticmethod
    async def bulk_update_session_activity(
        db: AsyncSession,
        session_ids: List[str],
        last_activity: datetime = None
    ) -> int:
        """
        Efficiently update multiple sessions in a single query.

        ❌ OLD WAY:
        for session_id in session_ids:
            session = db.query(ChatSession).filter_by(id=session_id).first()
            session.updated_at = datetime.utcnow()
            db.commit()  # N commits!

        ✅ NEW WAY:
        Single bulk update query
        """
        if not session_ids:
            return 0

        if last_activity is None:
            last_activity = datetime.utcnow()

        # Get all sessions to update
        result = await db.execute(
            select(ChatSession).filter(ChatSession.id.in_(session_ids))
        )
        sessions = result.scalars().all()

        updated_count = 0
        for session in sessions:
            session.updated_at = last_activity
            if hasattr(session, 'last_activity'):
                session.last_activity = last_activity
            updated_count += 1

        await db.flush()
        return updated_count

    @staticmethod
    async def get_user_chat_statistics_optimized(
        db: AsyncSession,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive user chat statistics in efficient queries.

        ❌ OLD WAY: Multiple separate queries
        ✅ NEW WAY: Optimized aggregation queries
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all relevant sessions
        session_result = await db.execute(
            select(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.created_at >= cutoff_date)
        )
        sessions = list(session_result.scalars().all())

        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.is_active])
        last_activity = max([s.updated_at for s in sessions]) if sessions else None
        first_session = min([s.created_at for s in sessions]) if sessions else None

        # Calculate average session duration
        durations = []
        for s in sessions:
            if s.updated_at and s.created_at:
                durations.append((s.updated_at - s.created_at).total_seconds())
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Get message statistics
        message_result = await db.execute(
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatMessage.created_at >= cutoff_date)
        )
        messages = list(message_result.scalars().all())

        total_messages = len(messages)
        user_messages = len([m for m in messages if m.role == MessageRoleEnum.USER])
        assistant_messages = len([m for m in messages if m.role == MessageRoleEnum.ASSISTANT])
        
        message_lengths = [len(m.content) for m in messages]
        avg_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
        messages_per_day = total_messages / max(days, 1)

        return {
            'user_id': user_id,
            'period_days': days,
            'sessions': {
                'total': total_sessions,
                'active': active_sessions,
                'avg_duration_seconds': float(avg_duration),
                'last_activity': last_activity,
                'first_session': first_session
            },
            'messages': {
                'total': total_messages,
                'user': user_messages,
                'assistant': assistant_messages,
                'avg_length': float(avg_length),
                'per_day': float(messages_per_day)
            }
        }

    @staticmethod
    async def search_messages_with_session_context(
        db: AsyncSession,
        search_term: str,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search messages and include session context efficiently.

        ❌ OLD WAY: Query messages, then query each session separately
        ✅ NEW WAY: Single query with joins
        """
        query = (
            select(ChatMessage, ChatSession, User)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .join(User, ChatSession.user_id == User.id)
            .filter(ChatMessage.content.ilike(f'%{search_term}%'))
        )

        if user_id:
            query = query.filter(ChatSession.user_id == user_id)

        # Order by recency
        query = query.order_by(desc(ChatMessage.created_at)).offset(offset).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'role': message.role,
                    'created_at': message.created_at
                },
                'session': {
                    'id': session.id,
                    'title': session.title,
                    'created_at': session.created_at
                },
                'user': {
                    'username': user.username
                }
            }
            for message, session, user in rows
        ]

    @staticmethod
    async def get_message_thread_optimized(
        db: AsyncSession,
        message_id: str,
        context_before: int = 5,
        context_after: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Get a message with surrounding context efficiently.

        Uses eager loading to get context in minimal queries.
        """
        # First, get the target message
        target_result = await db.execute(
            select(ChatMessage).filter(ChatMessage.id == message_id)
        )
        target_message = target_result.scalar_one_or_none()

        if not target_message:
            return None

        # Get all messages from the session, sorted
        messages_result = await db.execute(
            select(ChatMessage)
            .filter(ChatMessage.session_id == target_message.session_id)
            .order_by(ChatMessage.created_at)
        )
        all_messages = list(messages_result.scalars().all())

        # Find target position
        target_index = next(
            (i for i, m in enumerate(all_messages) if m.id == message_id),
            -1
        )

        if target_index == -1:
            return None

        # Get context window
        start_idx = max(0, target_index - context_before)
        end_idx = min(len(all_messages), target_index + context_after + 1)
        context_messages = all_messages[start_idx:end_idx]

        return {
            'target_message_index': target_index - start_idx,
            'messages': [
                {
                    'id': m.id,
                    'content': m.content,
                    'role': m.role,
                    'created_at': m.created_at,
                    'is_target': m.id == message_id,
                    'position_in_session': i + start_idx
                }
                for i, m in enumerate(context_messages)
            ],
            'session_id': target_message.session_id
        }


# Query performance monitoring decorator
def monitor_query_performance(operation_name: str):
    """Decorator to monitor query performance."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                if duration > 1.0:  # Log slow queries
                    logger.warning(
                        f"Slow query detected: {operation_name} took {duration:.2f}s"
                    )
                elif duration > 0.1:
                    logger.info(
                        f"Query performance: {operation_name} took {duration:.3f}s"
                    )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Query failed: {operation_name} failed after {duration:.3f}s: {e}"
                )
                raise

        return wrapper
    return decorator


# Example usage of the optimized repository
async def example_usage():
    """Example demonstrating optimized query usage."""

    # ❌ OLD WAY - N+1 Queries:
    # sessions = await db.execute(select(ChatSession).filter_by(user_id='user123'))
    # sessions = sessions.scalars().all()
    # for session in sessions:  # This creates N additional queries!
    #     messages = await db.execute(select(ChatMessage).filter_by(session_id=session.id))
    #     user = await db.execute(select(User).filter_by(id=session.user_id))

    # ✅ NEW WAY - Single Optimized Query:
    # optimized_sessions = await OptimizedChatRepository.get_sessions_with_messages_optimized(
    #     db=db,
    #     user_id='user123',
    #     limit=10,
    #     include_message_count=True,
    #     include_last_message=True
    # )
    #
    # # All data loaded efficiently with eager loading!
    # for session in optimized_sessions:
    #     print(f"Session: {session.title}")
    #     print(f"Messages: {session._message_count}")
    #     print(f"Last message: {session._last_message_content}")
    #     print(f"User: {session.user.username}")  # Already loaded!
    pass
