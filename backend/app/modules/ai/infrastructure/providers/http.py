"""Shared HTTP transport used by provider adapters."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from app.modules.ai.domain.exceptions import AIProviderError, AITimeoutError


class ProviderHTTPClient:
    def __init__(self, *, timeout_seconds: float, max_retries: int) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries

    async def post(
        self, url: str, *, headers: Mapping[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(url, headers=dict(headers), json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self._max_retries:
                        await asyncio.sleep(0.25 * (2**attempt))
                        continue
                if response.is_error:
                    raise AIProviderError(
                        f"AI provider returned HTTP {response.status_code}.",
                        code="provider_http_error",
                        retryable=response.status_code == 429 or response.status_code >= 500,
                    )
                return response.json()
            except httpx.TimeoutException as exc:
                if attempt < self._max_retries:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise AITimeoutError() from exc
            except httpx.RequestError as exc:
                if attempt < self._max_retries:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise AIProviderError(
                    "AI provider could not be reached.", code="provider_unavailable", retryable=True
                ) from exc
        raise AIProviderError("AI provider request failed.", code="provider_error")
