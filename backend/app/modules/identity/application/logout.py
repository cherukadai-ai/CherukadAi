"""Use case: logout — revoke the server-side session."""
from __future__ import annotations

from app.application.base import UseCase
from app.modules.identity.domain.ports import SessionStore


class Logout(UseCase[str, None]):
    def __init__(self, sessions: SessionStore) -> None:
        self._sessions = sessions

    async def execute(self, payload: str) -> None:
        await self._sessions.revoke(payload)
