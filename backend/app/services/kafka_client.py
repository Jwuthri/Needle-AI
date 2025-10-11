"""
Kafka client for message streaming and event processing.
"""

import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from ..utils.logging import get_logger

logger = get_logger("kafka_client")


class KafkaClient:
    """Kafka client for producing and consuming messages."""

    def __init__(self):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.consumer_tasks: Dict[str, asyncio.Task] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the Kafka client (called by DI container)."""
        if not self._initialized:
            await self.connect()
            self._initialized = True

    async def cleanup(self):
        """Cleanup resources (called by DI container)."""
        await self.disconnect()
        self._initialized = False

    async def connect(self):
        """Initialize Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=self._serialize_message,
                key_serializer=self._serialize_key,
                compression_type="gzip",
                retry_backoff_ms=500,
                request_timeout_ms=60000,
                api_version="auto"
            )

            await self.producer.start()
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")

        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    async def disconnect(self):
        """Close Kafka connections."""
        # Stop all consumer tasks
        for task_name, task in self.consumer_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close all consumers
        for consumer in self.consumers.values():
            await consumer.stop()

        # Close producer
        if self.producer:
            await self.producer.stop()

        logger.info("Disconnected from Kafka")

    def _serialize_message(self, message: Any) -> bytes:
        """Serialize message to JSON bytes."""
        if isinstance(message, bytes):
            return message
        if isinstance(message, str):
            return message.encode('utf-8')
        return json.dumps(message).encode('utf-8')

    def _serialize_key(self, key: Any) -> bytes:
        """Serialize key to bytes."""
        if key is None:
            return None
        if isinstance(key, bytes):
            return key
        return str(key).encode('utf-8')

    def _deserialize_message(self, message_bytes: bytes) -> Any:
        """Deserialize message from JSON bytes."""
        try:
            message_str = message_bytes.decode('utf-8')
            return json.loads(message_str)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return message_bytes.decode('utf-8', errors='replace')

    async def produce(self, topic: str, message: Any, key: Optional[str] = None, partition: Optional[int] = None) -> bool:
        """Produce a message to a Kafka topic."""
        try:
            await self.producer.send_and_wait(
                topic=topic,
                value=message,
                key=key,
                partition=partition
            )
            logger.debug(f"Message sent to topic {topic}")
            return True

        except KafkaError as e:
            logger.error(f"Kafka produce error for topic {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error producing to topic {topic}: {e}")
            return False

    async def create_consumer(self, topics: List[str], group_id: str, auto_offset_reset: str = "latest") -> Optional[str]:
        """Create a new Kafka consumer."""
        consumer_id = f"{group_id}_{len(self.consumers)}"

        try:
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                value_deserializer=self._deserialize_message,
                key_deserializer=lambda x: x.decode('utf-8') if x else None,
                enable_auto_commit=True,
                auto_commit_interval_ms=5000
            )

            await consumer.start()
            self.consumers[consumer_id] = consumer
            logger.info(f"Created Kafka consumer {consumer_id} for topics {topics}")
            return consumer_id

        except Exception as e:
            logger.error(f"Failed to create consumer for topics {topics}: {e}")
            return None

    async def start_consuming(self, consumer_id: str, message_handler: Callable[[str, Any, Optional[str]], None]):
        """Start consuming messages with a handler function."""
        if consumer_id not in self.consumers:
            logger.error(f"Consumer {consumer_id} not found")
            return

        consumer = self.consumers[consumer_id]

        async def consume_messages():
            try:
                async for message in consumer:
                    try:
                        await message_handler(message.topic, message.value, message.key)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
            except Exception as e:
                logger.error(f"Consumer {consumer_id} error: {e}")

        task = asyncio.create_task(consume_messages())
        self.consumer_tasks[consumer_id] = task
        logger.info(f"Started consuming for consumer {consumer_id}")

    async def stop_consumer(self, consumer_id: str):
        """Stop a specific consumer."""
        if consumer_id in self.consumer_tasks:
            task = self.consumer_tasks[consumer_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.consumer_tasks[consumer_id]

        if consumer_id in self.consumers:
            await self.consumers[consumer_id].stop()
            del self.consumers[consumer_id]
            logger.info(f"Stopped consumer {consumer_id}")

    # Chatbot-specific methods
    async def publish_chat_event(self, event_type: str, session_id: str, data: Dict[str, Any]) -> bool:
        """Publish a chat-related event."""
        event = {
            "event_type": event_type,
            "session_id": session_id,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }
        return await self.produce("chat_events", event, key=session_id)

    async def publish_user_message(self, session_id: str, message: str, user_id: Optional[str] = None) -> bool:
        """Publish a user message event."""
        return await self.publish_chat_event(
            "user_message",
            session_id,
            {"message": message, "user_id": user_id}
        )

    async def publish_ai_response(self, session_id: str, response: str, model: Optional[str] = None, tokens_used: Optional[int] = None) -> bool:
        """Publish an AI response event."""
        return await self.publish_chat_event(
            "ai_response",
            session_id,
            {
                "response": response,
                "model": model,
                "tokens_used": tokens_used
            }
        )

    async def publish_system_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish a system-level event."""
        event = {
            "event_type": event_type,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }
        return await self.produce("system_events", event)

    async def health_check(self) -> bool:
        """Check Kafka health."""
        try:
            if self.producer:
                # Try to get metadata as a health check
                metadata = await self.producer.client.fetch_metadata()
                return bool(metadata.brokers)
            return False
        except Exception:
            return False
