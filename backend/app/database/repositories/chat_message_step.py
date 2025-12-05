"""
Repository for ChatMessageStep database operations.
"""

from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.chat_message_step import ChatMessageStep
from app.utils.logging import get_logger

logger = get_logger("chat_message_step_repository")


class ChatMessageStepRepository:
    """Repository for managing chat message steps."""

    @staticmethod
    async def create(
        db: AsyncSession,
        message_id: str,
        agent_name: str,
        step_order: int,
        tool_call: Optional[dict] = None,
        structured_output: Optional[dict] = None,
        prediction: Optional[str] = None,
        raw_output: Optional[str] = None,
        **kwargs
    ) -> ChatMessageStep:
        """
        Create a new chat message step.
        
        Args:
            db: Database session
            message_id: ID of the chat message this step belongs to
            agent_name: Name of the agent that produced this step
            step_order: Order of this step in the execution sequence
            tool_call: Tool call data
            structured_output: Structured output (BaseModel serialized to dict)
            prediction: Text output
            raw_output: Raw unprocessed output from agent
            **kwargs: Additional fields
            
        Returns:
            Created ChatMessageStep instance
        """
        step = ChatMessageStep(
            message_id=message_id,
            agent_name=agent_name,
            step_order=step_order,
            tool_call=tool_call,
            structured_output=structured_output,
            prediction=prediction,
            raw_output=raw_output,
            **kwargs
        )
        db.add(step)
        await db.flush()
        logger.debug(f"Created chat message step {step.id} for message {message_id}")
        return step

    @staticmethod
    async def get_by_id(db: AsyncSession, step_id: str) -> Optional[ChatMessageStep]:
        """
        Get a chat message step by ID.
        
        Args:
            db: Database session
            step_id: Step ID
            
        Returns:
            ChatMessageStep instance or None if not found
        """
        result = await db.execute(
            select(ChatMessageStep).where(ChatMessageStep.id == step_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_message_id(
        db: AsyncSession,
        message_id: str,
        order_by_step: bool = True
    ) -> List[ChatMessageStep]:
        """
        Get all steps for a chat message.
        
        Args:
            db: Database session
            message_id: Chat message ID
            order_by_step: Whether to order by step_order
            
        Returns:
            List of ChatMessageStep instances
        """
        query = select(ChatMessageStep).where(ChatMessageStep.message_id == message_id)
        
        if order_by_step:
            query = query.order_by(ChatMessageStep.step_order)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_by_message_id(db: AsyncSession, message_id: str) -> int:
        """
        Delete all steps for a chat message.
        
        Args:
            db: Database session
            message_id: Chat message ID
            
        Returns:
            Number of steps deleted
        """
        steps = await ChatMessageStepRepository.get_by_message_id(db, message_id)
        count = len(steps)
        
        for step in steps:
            await db.delete(step)
        
        await db.flush()
        logger.debug(f"Deleted {count} steps for message {message_id}")
        return count

    @staticmethod
    async def update_status(
        db: AsyncSession,
        step_id: str,
        status: str
    ) -> Optional[ChatMessageStep]:
        """
        Update the status of a chat message step.
        
        Args:
            db: Database session
            step_id: Step ID
            status: New status (accepts any string - success/error/pending/SUCCESS/ERROR/PENDING)
            
        Returns:
            Updated ChatMessageStep instance or None if not found
        """
        step = await ChatMessageStepRepository.get_by_id(db, step_id)
        if step:
            # Normalize to lowercase for consistency
            step.status = status.lower() if status else 'success'
            await db.flush()
            logger.debug(f"Updated step {step_id} status to {step.status}")
        return step

    @staticmethod
    async def update_with_result(
        db: AsyncSession,
        step_id: str,
        status: str,
        structured_output: Optional[dict] = None,
        prediction: Optional[str] = None,
        raw_output: Optional[str] = None
    ) -> Optional[ChatMessageStep]:
        """
        Update a chat message step with tool result data.
        
        Args:
            db: Database session
            step_id: Step ID
            status: New status (success/error/pending)
            structured_output: Structured output from tool (dict)
            prediction: Text output from tool
            raw_output: Raw unprocessed output from agent
            
        Returns:
            Updated ChatMessageStep instance or None if not found
        """
        step = await ChatMessageStepRepository.get_by_id(db, step_id)
        if step:
            step.status = status.lower() if status else 'success'
            if structured_output is not None:
                step.structured_output = structured_output
            if prediction is not None:
                step.prediction = prediction
            if raw_output is not None:
                step.raw_output = raw_output
            await db.flush()
            logger.debug(f"Updated step {step_id} with result data")
        return step

    @staticmethod
    async def bulk_create(
        db: AsyncSession,
        message_id: str,
        steps: List[dict]
    ) -> List[ChatMessageStep]:
        """
        Create multiple steps at once.
        
        Args:
            db: Database session
            message_id: Chat message ID
            steps: List of step data dicts with keys: agent_name, step_order, tool_call, structured_output, prediction, raw_output
            
        Returns:
            List of created ChatMessageStep instances
        """
        created_steps = []
        
        for step_data in steps:
            step = ChatMessageStep(
                message_id=message_id,
                agent_name=step_data['agent_name'],
                step_order=step_data['step_order'],
                tool_call=step_data.get('tool_call'),
                structured_output=step_data.get('structured_output'),
                prediction=step_data.get('prediction'),
                raw_output=step_data.get('raw_output'),
                status=step_data.get('status', 'success')
            )
            db.add(step)
            created_steps.append(step)
        
        await db.flush()
        logger.debug(f"Bulk created {len(created_steps)} steps for message {message_id}")
        return created_steps

