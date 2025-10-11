"""
LLM and AI-related background tasks for NeedleAi.
"""

import asyncio
from typing import Any, Dict, List

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.llm.factory import get_llm_client
from app.utils.logging import get_logger

logger = get_logger("llm_tasks")
settings = get_settings()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_completion_async(self, prompt: str, model: str = None, **kwargs) -> Dict[str, Any]:
    """
    Generate LLM completion asynchronously.

    Args:
        prompt: Input prompt for the LLM
        model: Model to use (optional, uses default if not specified)
        **kwargs: Additional parameters for LLM generation

    Returns:
        Dict containing completion result and metadata
    """
    try:
        logger.info(f"Starting async completion generation for task {self.request.id}")

        # Update task progress
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Initializing LLM...'})

        # Get LLM client
        llm_client = get_llm_client(
            provider=settings.llm_provider,
            settings=settings
        )

        self.update_state(state='PROGRESS', meta={'current': 25, 'total': 100, 'status': 'Generating completion...'})

        # Generate completion (run async code in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            completion_result = loop.run_until_complete(
                llm_client.generate_completion(
                    prompt=prompt,
                    **kwargs
                )
            )
        finally:
            loop.close()

        self.update_state(state='PROGRESS', meta={'current': 100, 'total': 100, 'status': 'Completion generated!'})

        logger.info(f"Completed async generation for task {self.request.id}")

        return {
            "task_id": self.request.id,
            "completion": completion_result,
            "model": model or settings.default_model,
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Error in async completion generation: {str(exc)}")

        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {self.request.id} (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=exc, countdown=60)

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed",
            "retries": self.request.retries
        }


@celery_app.task(bind=True, max_retries=2)
def batch_process_messages(self, messages: List[Dict[str, Any]], model: str = None) -> Dict[str, Any]:
    """
    Process multiple messages in batch for efficiency.

    Args:
        messages: List of message dictionaries to process
        model: Model to use for processing

    Returns:
        Dict with processing results and statistics
    """
    try:
        logger.info(f"Starting batch processing of {len(messages)} messages")

        results = []
        failed_count = 0

        # Get LLM client
        llm_client = get_llm_client(
            provider=settings.llm_provider,
            settings=settings
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            for i, message in enumerate(messages):
                try:
                    # Update progress
                    progress = int((i / len(messages)) * 100)
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': i,
                            'total': len(messages),
                            'progress': progress,
                            'status': f'Processing message {i+1}/{len(messages)}'
                        }
                    )

                    # Process message
                    result = loop.run_until_complete(
                        llm_client.generate_completion(
                            prompt=message.get("content", ""),
                            max_tokens=message.get("max_tokens", 150),
                            temperature=message.get("temperature", 0.7)
                        )
                    )

                    results.append({
                        "index": i,
                        "message_id": message.get("id"),
                        "result": result,
                        "status": "success"
                    })

                except Exception as msg_error:
                    logger.error(f"Error processing message {i}: {str(msg_error)}")
                    failed_count += 1
                    results.append({
                        "index": i,
                        "message_id": message.get("id"),
                        "error": str(msg_error),
                        "status": "failed"
                    })

        finally:
            loop.close()

        logger.info(f"Batch processing completed: {len(messages) - failed_count} succeeded, {failed_count} failed")

        return {
            "task_id": self.request.id,
            "total_messages": len(messages),
            "successful": len(messages) - failed_count,
            "failed": failed_count,
            "results": results,
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Error in batch processing: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed"
        }


@celery_app.task(bind=True, max_retries=2)
def update_embeddings(self, texts: List[str], namespace: str = "default") -> Dict[str, Any]:
    """
    Update embeddings in vector database for given texts.

    Args:
        texts: List of texts to generate embeddings for
        namespace: Namespace to store embeddings in

    Returns:
        Dict with update results and statistics
    """
    try:
        logger.info(f"Updating embeddings for {len(texts)} texts in namespace: {namespace}")

        # This would integrate with your vector database
        # For now, returning a mock response

        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': 'Generating embeddings...'}
        )

        # Simulate embedding generation time
        import time
        time.sleep(2)

        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': 'Embeddings updated!'}
        )

        return {
            "task_id": self.request.id,
            "updated_count": len(texts),
            "namespace": namespace,
            "status": "completed"
        }

    except Exception as exc:
        logger.error(f"Error updating embeddings: {str(exc)}")

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)

        return {
            "task_id": self.request.id,
            "error": str(exc),
            "status": "failed"
        }
