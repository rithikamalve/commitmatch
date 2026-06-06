"""
In-process WebSocket manager for local/demo use.
Replaces API Gateway when running locally — no AWS setup needed.
"""
import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        print(f"[WS] Client connected — {len(self._connections)} active")

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        print(f"[WS] Client disconnected — {len(self._connections)} active")

    async def broadcast(self, event: dict) -> None:
        if not self._connections:
            return
        data = json.dumps(event)
        dead: Set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections.discard(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


# Singleton — imported by push.py and main.py
manager = ConnectionManager()
