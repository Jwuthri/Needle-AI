"""
WebSocket connection manager for real-time chat functionality.
"""

import asyncio
import json
from typing import Dict, List, Set

from fastapi import WebSocket

from .utils.logging import get_logger

logger = get_logger("websocket_manager")


class WebSocketManager:
    """Manages WebSocket connections for chat sessions."""

    def __init__(self):
        # Maps session_id to list of WebSocket connections
        self.sessions: Dict[str, List[WebSocket]] = {}
        # Maps WebSocket to session_id for quick lookup
        self.connection_to_session: Dict[WebSocket, str] = {}
        # Set of all active connections
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a WebSocket to a chat session."""
        await websocket.accept()

        # Add to active connections
        self.active_connections.add(websocket)
        self.connection_to_session[websocket] = session_id

        # Add to session
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(websocket)

        logger.info(f"WebSocket connected to session {session_id}. Total connections: {len(self.active_connections)}")

        # Notify other clients in the session
        await self.send_message_to_session(
            session_id,
            {
                "type": "user_joined",
                "session_id": session_id,
                "total_connections": len(self.sessions[session_id])
            },
            exclude=websocket
        )

    def disconnect(self, websocket: WebSocket, session_id: str = None):
        """Disconnect a WebSocket from its session."""
        if websocket not in self.active_connections:
            return

        # Remove from active connections
        self.active_connections.discard(websocket)

        # Get session_id if not provided
        if session_id is None:
            session_id = self.connection_to_session.get(websocket)

        if session_id and session_id in self.sessions:
            # Remove from session
            if websocket in self.sessions[session_id]:
                self.sessions[session_id].remove(websocket)

            # Clean up empty session
            if not self.sessions[session_id]:
                del self.sessions[session_id]
                logger.info(f"Cleaned up empty session: {session_id}")
            else:
                # Notify remaining clients
                asyncio.create_task(
                    self.send_message_to_session(
                        session_id,
                        {
                            "type": "user_left",
                            "session_id": session_id,
                            "total_connections": len(self.sessions[session_id])
                        }
                    )
                )

        # Remove from connection mapping
        self.connection_to_session.pop(websocket, None)

        logger.info(f"WebSocket disconnected from session {session_id}. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket connection."""
        if websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending personal message: {e}")
                self.disconnect(websocket)

    async def send_message_to_session(self, session_id: str, message: dict, exclude: WebSocket = None):
        """Send a message to all connections in a session."""
        if session_id not in self.sessions:
            return

        disconnected_websockets = []

        for websocket in self.sessions[session_id]:
            if exclude and websocket == exclude:
                continue

            if websocket in self.active_connections:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to session {session_id}: {e}")
                    disconnected_websockets.append(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket, session_id)

    async def broadcast_message(self, message: dict, exclude_session: str = None):
        """Broadcast a message to all active connections (excluding a specific session)."""
        disconnected_websockets = []

        for websocket in self.active_connections:
            session_id = self.connection_to_session.get(websocket)
            if exclude_session and session_id == exclude_session:
                continue

            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected_websockets.append(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            session_id = self.connection_to_session.get(websocket)
            self.disconnect(websocket, session_id)

    def get_session_info(self, session_id: str) -> dict:
        """Get information about a session."""
        if session_id not in self.sessions:
            return {"session_id": session_id, "connections": 0, "active": False}

        return {
            "session_id": session_id,
            "connections": len(self.sessions[session_id]),
            "active": True
        }

    def get_all_sessions_info(self) -> List[dict]:
        """Get information about all active sessions."""
        return [
            self.get_session_info(session_id)
            for session_id in self.sessions.keys()
        ]

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
