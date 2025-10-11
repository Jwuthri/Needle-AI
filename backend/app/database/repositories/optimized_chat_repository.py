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
from sqlalchemy.orm import Session, joinedload, selectinload

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
    def get_sessions_with_messages_optimized(
        db: Session,
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
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.is_active == True)
        )

        # Eager load user to prevent additional query
        query = query.options(joinedload(ChatSession.user))

        if include_last_message or include_message_count:
            # Create a subquery for message statistics
            message_stats = (
                db.query(
                    ChatMessage.session_id,
                    func.count(ChatMessage.id).label('message_count'),
                    func.max(ChatMessage.created_at).label('last_message_time'),
                    # Get last message content efficiently
                    func.first_value(ChatMessage.content)
                    .over(
                        partition_by=ChatMessage.session_id,
                        order_by=desc(ChatMessage.created_at)
                    ).label('last_message_content')
                )
                .group_by(ChatMessage.session_id)
                .subquery()
            )

            # Join with message statistics
            query = (
                query.outerjoin(
                    message_stats,
                    ChatSession.id == message_stats.c.session_id
                )
                .add_columns(
                    message_stats.c.message_count,
                    message_stats.c.last_message_time,
                    message_stats.c.last_message_content
                )
            )

        # Order by last activity for better UX
        query = query.order_by(
            desc(ChatSession.updated_at),
            desc(ChatSession.created_at)
        )

        # Efficient pagination
        results = query.offset(offset).limit(limit).all()

        if include_message_count or include_last_message:
            # Enhance session objects with computed fields
            sessions = []
            for row in results:
                if isinstance(row, tuple):
                    session, msg_count, last_msg_time, last_msg_content = row
                    # Add computed attributes to session object
                    session._message_count = msg_count or 0
                    session._last_message_time = last_msg_time
                    session._last_message_content = last_msg_content
                else:
                    session = row
                sessions.append(session)
            return sessions
        else:
            return results

    @staticmethod
    def get_conversation_with_context_optimized(
        db: Session,
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
            db.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .options(
                # Eager load messages (selectinload for collections)
                selectinload(ChatSession.messages)
                .options(
                    # Load message metadata efficiently
                    selectinload(ChatMessage.extra_metadata) if hasattr(ChatMessage, 'metadata') else None
                )
            )
        )

        if include_user:
            # Eager load user (joinedload for single relationships)
            query = query.options(joinedload(ChatSession.user))

        session = query.first()

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
    def bulk_update_session_activity(
        db: Session,
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

        updated_count = (
            db.query(ChatSession)
            .filter(ChatSession.id.in_(session_ids))
            .update(
                {
                    ChatSession.updated_at: last_activity,
                    ChatSession.last_activity: last_activity
                },
                synchronize_session=False  # Faster for bulk updates
            )
        )

        return updated_count

    @staticmethod
    def get_user_chat_statistics_optimized(
        db: Session,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive user chat statistics in efficient queries.

        ❌ OLD WAY: Multiple separate queries
        ✅ NEW WAY: Optimized aggregation queries
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Single query for session statistics
        session_stats = (
            db.query(
                func.count(ChatSession.id).label('total_sessions'),
                func.count().filter(ChatSession.is_active == True).label('active_sessions'),
                func.max(ChatSession.updated_at).label('last_activity'),
                func.min(ChatSession.created_at).label('first_session'),
                # Session duration statistics
                func.avg(
                    func.extract('epoch', ChatSession.updated_at - ChatSession.created_at)
                ).label('avg_session_duration')
            )
            .filter(ChatSession.user_id == user_id)
            .filter(ChatSession.created_at >= cutoff_date)
            .first()
        )

        # Single query for message statistics
        message_stats = (
            db.query(
                func.count(ChatMessage.id).label('total_messages'),
                func.count().filter(ChatMessage.role == MessageRoleEnum.USER).label('user_messages'),
                func.count().filter(ChatMessage.role == MessageRoleEnum.ASSISTANT).label('assistant_messages'),
                func.avg(func.length(ChatMessage.content)).label('avg_message_length'),
                # Messages per day
                func.count(ChatMessage.id) / func.greatest(days, 1).label('messages_per_day')
            )
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .filter(ChatSession.user_id == user_id)
            .filter(ChatMessage.created_at >= cutoff_date)
            .first()
        )

        return {
            'user_id': user_id,
            'period_days': days,
            'sessions': {
                'total': session_stats.total_sessions or 0,
                'active': session_stats.active_sessions or 0,
                'avg_duration_seconds': float(session_stats.avg_session_duration or 0),
                'last_activity': session_stats.last_activity,
                'first_session': session_stats.first_session
            },
            'messages': {
                'total': message_stats.total_messages or 0,
                'user': message_stats.user_messages or 0,
                'assistant': message_stats.assistant_messages or 0,
                'avg_length': float(message_stats.avg_message_length or 0),
                'per_day': float(message_stats.messages_per_day or 0)
            }
        }

    @staticmethod
    def search_messages_with_session_context(
        db: Session,
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
            db.query(
                ChatMessage,
                ChatSession.title.label('session_title'),
                ChatSession.created_at.label('session_created'),
                User.username.label('username'),
                # Rank results by relevance
                func.ts_rank_cd(
                    func.to_tsvector('english', ChatMessage.content),
                    func.plainto_tsquery('english', search_term)
                ).label('relevance_rank')
            )
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .join(User, ChatSession.user_id == User.id)
            .filter(
                ChatMessage.content.ilike(f'%{search_term}%')
            )
        )

        if user_id:
            query = query.filter(ChatSession.user_id == user_id)

        # Order by relevance and recency
        results = (
            query.order_by(
                desc(text('relevance_rank')),
                desc(ChatMessage.created_at)
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                'message': {
                    'id': row.ChatMessage.id,
                    'content': row.ChatMessage.content,
                    'role': row.ChatMessage.role,
                    'created_at': row.ChatMessage.created_at
                },
                'session': {
                    'id': row.ChatMessage.session_id,
                    'title': row.session_title,
                    'created_at': row.session_created
                },
                'user': {
                    'username': row.username
                },
                'relevance_score': float(row.relevance_rank or 0)
            }
            for row in results
        ]

    @staticmethod
    def get_message_thread_optimized(
        db: Session,
        message_id: str,
        context_before: int = 5,
        context_after: int = 5
    ) -> Dict[str, Any]:
        """
        Get a message with surrounding context efficiently.

        Uses window functions to get context in a single query.
        """
        # First, get the target message to find its position
        target_message = (
            db.query(
                ChatMessage.id,
                ChatMessage.session_id,
                ChatMessage.created_at,
                # Calculate position in conversation
                func.row_number()
                .over(
                    partition_by=ChatMessage.session_id,
                    order_by=ChatMessage.created_at
                ).label('position')
            )
            .filter(ChatMessage.id == message_id)
            .first()
        )

        if not target_message:
            return None

        # Get context messages using the position
        context_query = (
            db.query(
                ChatMessage,
                func.row_number()
                .over(
                    partition_by=ChatMessage.session_id,
                    order_by=ChatMessage.created_at
                ).label('position')
            )
            .filter(ChatMessage.session_id == target_message.session_id)
            .filter(
                and_(
                    # Position range for context
                    text('row_number() OVER (PARTITION BY session_id ORDER BY created_at)') >=
                    target_message.position - context_before,
                    text('row_number() OVER (PARTITION BY session_id ORDER BY created_at)') <=
                    target_message.position + context_after
                )
            )
            .order_by(ChatMessage.created_at)
            .all()
        )

        messages = []
        target_index = -1

        for i, (message, position) in enumerate(context_query):
            is_target = message.id == message_id
            if is_target:
                target_index = i

            messages.append({
                'id': message.id,
                'content': message.content,
                'role': message.role,
                'created_at': message.created_at,
                'is_target': is_target,
                'position_in_session': position
            })

        return {
            'target_message_index': target_index,
            'messages': messages,
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
    # sessions = db.query(ChatSession).filter_by(user_id='user123').all()
    # for session in sessions:  # This creates N additional queries!
    #     messages = db.query(ChatMessage).filter_by(session_id=session.id).all()
    #     user = db.query(User).filter_by(id=session.user_id).first()

    # ✅ NEW WAY - Single Optimized Query:
    # optimized_sessions = OptimizedChatRepository.get_sessions_with_messages_optimized(
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
