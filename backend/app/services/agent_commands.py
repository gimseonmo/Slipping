from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone

from app.services.powerpoint_control import SlideAction


class AgentCommandBus:
    def __init__(self) -> None:
        self._commands: deque[SlideAction] = deque()
        self._condition = asyncio.Condition()
        self.last_poll_at: datetime | None = None

    def has_recent_agent(self) -> bool:
        if self.last_poll_at is None:
            return False
        return datetime.now(timezone.utc) - self.last_poll_at < timedelta(seconds=35)

    async def enqueue(self, action: SlideAction) -> None:
        async with self._condition:
            self._commands.append(action)
            self._condition.notify()

    async def poll(self, timeout: float = 20.0) -> SlideAction | None:
        async with self._condition:
            self.last_poll_at = datetime.now(timezone.utc)
            if not self._commands:
                try:
                    await asyncio.wait_for(self._condition.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            if not self._commands:
                return None
            return self._commands.popleft()


agent_command_bus = AgentCommandBus()
