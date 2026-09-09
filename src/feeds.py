"""Bounded public-feed requests with a per-process TTL cache."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Callable

import httpx


class FeedClient:
    def __init__(self, fetch: Callable[[str], str] | None = None) -> None:
        self._fetch = fetch or self._request
        self._cache: dict[str, tuple[float, str, str]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _request(url: str) -> str:
        with httpx.stream(
            "GET", url, timeout=15, headers={"User-Agent": "mcp-space-defense-osint/0.1"}
        ) as response:
            response.raise_for_status()
            chunks = bytearray()
            for chunk in response.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > 2_000_000:
                    raise ValueError("Feed exceeds two-megabyte budget")
            return chunks.decode("utf-8")

    def get(self, url: str, ttl: int = 300) -> tuple[str, str, bool]:
        with self._lock:
            cached = self._cache.get(url)
            if cached and time.monotonic() - cached[0] < ttl:
                return cached[1], cached[2], True
            payload = self._fetch(url)
            retrieved_at = datetime.now(timezone.utc).isoformat()
            self._cache[url] = (time.monotonic(), payload, retrieved_at)
            return payload, retrieved_at, False

    def json(self, url: str, ttl: int = 300) -> tuple[object, str, bool]:
        payload, retrieved_at, cached = self.get(url, ttl)
        return json.loads(payload), retrieved_at, cached
