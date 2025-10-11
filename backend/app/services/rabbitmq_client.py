"""
RabbitMQ client for reliable message queuing and task processing.
"""

import asyncio
import json
import os
from typing import Any, Callable, Dict, Optional

from aio_pika import DeliveryMode, ExchangeType, Message, connect
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractExchange,
    AbstractQueue,
)

from ..utils.logging import get_logger

logger = get_logger("rabbitmq_client")


class RabbitMQClient:
    """RabbitMQ client for message queuing and task processing."""

    def __init__(self):
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchanges: Dict[str, AbstractExchange] = {}
        self.queues: Dict[str, AbstractQueue] = {}
        self.consumers: Dict[str, asyncio.Task] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the RabbitMQ client (called by DI container)."""
        if not self._initialized:
            await self.connect()
            self._initialized = True

    async def cleanup(self):
        """Cleanup resources (called by DI container)."""
        await self.disconnect()
        self._initialized = False

    async def connect(self):
        """Initialize RabbitMQ connection."""
        try:
            self.connection = await connect(self.rabbitmq_url)
            self.channel = await self.connection.channel()

            # Set up default exchanges and queues
            await self._setup_default_infrastructure()

            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_url}")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Close RabbitMQ connections."""
        # Stop all consumers
        for consumer_name, task in self.consumers.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close connection
        if self.connection:
            await self.connection.close()

        logger.info("Disconnected from RabbitMQ")

    async def _setup_default_infrastructure(self):
        """Set up default exchanges and queues."""
        try:
            # Create exchanges
            chat_exchange = await self.channel.declare_exchange(
                "chat_exchange",
                ExchangeType.TOPIC,
                durable=True
            )
            self.exchanges["chat"] = chat_exchange

            task_exchange = await self.channel.declare_exchange(
                "task_exchange",
                ExchangeType.DIRECT,
                durable=True
            )
            self.exchanges["task"] = task_exchange

            # Create queues
            message_queue = await self.channel.declare_queue(
                "chat_messages",
                durable=True,
                arguments={"x-max-priority": 10}
            )
            self.queues["chat_messages"] = message_queue

            ai_processing_queue = await self.channel.declare_queue(
                "ai_processing",
                durable=True,
                arguments={"x-max-priority": 5}
            )
            self.queues["ai_processing"] = ai_processing_queue

            notification_queue = await self.channel.declare_queue(
                "notifications",
                durable=True
            )
            self.queues["notifications"] = notification_queue

            # Bind queues to exchanges
            await message_queue.bind(chat_exchange, "message.*")
            await ai_processing_queue.bind(task_exchange, "ai.process")
            await notification_queue.bind(chat_exchange, "notification.*")

            logger.info("RabbitMQ infrastructure set up successfully")

        except Exception as e:
            logger.error(f"Failed to set up RabbitMQ infrastructure: {e}")
            raise

    async def publish_message(
        self,
        exchange_name: str,
        routing_key: str,
        message: Any,
        priority: int = 0,
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT,
        expiration: Optional[int] = None
    ) -> bool:
        """Publish a message to RabbitMQ."""
        try:
            if exchange_name not in self.exchanges:
                logger.error(f"Exchange {exchange_name} not found")
                return False

            exchange = self.exchanges[exchange_name]

            # Serialize message
            if isinstance(message, (dict, list)):
                body = json.dumps(message).encode()
            elif isinstance(message, str):
                body = message.encode()
            else:
                body = str(message).encode()

            # Create message
            rabbitmq_message = Message(
                body,
                priority=priority,
                delivery_mode=delivery_mode,
                expiration=expiration * 1000 if expiration else None  # Convert to milliseconds
            )

            # Publish message
            await exchange.publish(rabbitmq_message, routing_key=routing_key)
            logger.debug(f"Message published to {exchange_name} with routing key {routing_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False

    async def create_consumer(
        self,
        queue_name: str,
        message_handler: Callable[[str, Dict[str, Any]], None],
        prefetch_count: int = 10
    ) -> bool:
        """Create a consumer for a queue."""
        try:
            if queue_name not in self.queues:
                logger.error(f"Queue {queue_name} not found")
                return False

            queue = self.queues[queue_name]

            # Set prefetch count
            await self.channel.set_qos(prefetch_count=prefetch_count)

            async def process_message(message):
                async with message.process():
                    try:
                        # Deserialize message body
                        body = message.body.decode()
                        try:
                            data = json.loads(body)
                        except json.JSONDecodeError:
                            data = {"raw_message": body}

                        # Call message handler
                        await message_handler(queue_name, data)

                    except Exception as e:
                        logger.error(f"Error processing message from {queue_name}: {e}")
                        raise  # This will nack the message

            # Start consuming
            consume_task = asyncio.create_task(queue.consume(process_message))
            self.consumers[queue_name] = consume_task

            logger.info(f"Started consumer for queue {queue_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create consumer for {queue_name}: {e}")
            return False

    async def stop_consumer(self, queue_name: str):
        """Stop a consumer."""
        if queue_name in self.consumers:
            task = self.consumers[queue_name]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.consumers[queue_name]
            logger.info(f"Stopped consumer for queue {queue_name}")

    # Chatbot-specific methods
    async def queue_user_message(self, session_id: str, message: str, user_id: Optional[str] = None, priority: int = 5) -> bool:
        """Queue a user message for processing."""
        message_data = {
            "type": "user_message",
            "session_id": session_id,
            "message": message,
            "user_id": user_id,
            "timestamp": asyncio.get_event_loop().time()
        }

        return await self.publish_message(
            "chat",
            f"message.user.{session_id}",
            message_data,
            priority=priority
        )

    async def queue_ai_processing(self, session_id: str, message: str, context: Dict[str, Any], priority: int = 3) -> bool:
        """Queue a message for AI processing."""
        processing_data = {
            "type": "ai_processing",
            "session_id": session_id,
            "message": message,
            "context": context,
            "timestamp": asyncio.get_event_loop().time()
        }

        return await self.publish_message(
            "task",
            "ai.process",
            processing_data,
            priority=priority
        )

    async def send_notification(self, notification_type: str, recipient: str, data: Dict[str, Any]) -> bool:
        """Send a notification message."""
        notification_data = {
            "type": notification_type,
            "recipient": recipient,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }

        return await self.publish_message(
            "chat",
            f"notification.{notification_type}",
            notification_data
        )

    async def queue_background_task(self, task_type: str, task_data: Dict[str, Any], delay: Optional[int] = None) -> bool:
        """Queue a background task."""
        task_message = {
            "task_type": task_type,
            "data": task_data,
            "timestamp": asyncio.get_event_loop().time()
        }

        return await self.publish_message(
            "task",
            f"task.{task_type}",
            task_message,
            expiration=delay
        )

    # RPC-style methods
    async def create_rpc_queue(self, queue_name: str) -> Optional[str]:
        """Create a queue for RPC-style communication."""
        try:
            queue = await self.channel.declare_queue(
                queue_name,
                exclusive=True,
                auto_delete=True
            )
            self.queues[queue_name] = queue
            return queue_name
        except Exception as e:
            logger.error(f"Failed to create RPC queue {queue_name}: {e}")
            return None

    async def call_rpc(self, queue_name: str, message: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Make an RPC call and wait for response."""
        try:
            # Create reply queue
            reply_queue = await self.channel.declare_queue(exclusive=True)

            # Create correlation ID
            correlation_id = str(id(message))

            # Create message with reply-to
            body = json.dumps(message).encode()
            rpc_message = Message(
                body,
                reply_to=reply_queue.name,
                correlation_id=correlation_id
            )

            # Publish request
            await self.channel.default_exchange.publish(
                rpc_message,
                routing_key=queue_name
            )

            # Wait for response
            response = None

            async def on_response(message):
                nonlocal response
                if message.correlation_id == correlation_id:
                    response = json.loads(message.body.decode())

            await reply_queue.consume(on_response, timeout=timeout)

            return response

        except Exception as e:
            logger.error(f"RPC call failed: {e}")
            return None

    async def health_check(self) -> bool:
        """Check RabbitMQ health."""
        try:
            if self.connection and not self.connection.is_closed:
                # Try to declare a temporary queue as a health check
                temp_queue = await self.channel.declare_queue(exclusive=True, auto_delete=True)
                await temp_queue.delete()
                return True
            return False
        except Exception:
            return False
