"""
Real-time notifications via WebSocket.
Provides basic connection management and broadcast utilities.
"""
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Realtime"])


class ConnectionManager:
    """Simple WebSocket connection manager."""

    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)
        logger.info(f"WebSocket connected (total={len(self.active)})")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)
        logger.info(f"WebSocket disconnected (total={len(self.active)})")

    async def broadcast(self, message: dict):
        payload = json.dumps(message)
        for connection in list(self.active):
            try:
                await connection.send_text(payload)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications."""
    await manager.connect(websocket)
    try:
        await manager.broadcast({"type": "presence", "active": len(manager.active)})
        while True:
            _ = await websocket.receive_text()  # Keep-alive / optional client pings
            await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:  # pragma: no cover
        logger.error(f"WebSocket error: {exc}", exc_info=True)
        manager.disconnect(websocket)
