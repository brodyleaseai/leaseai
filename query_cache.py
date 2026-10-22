"""In-process TTL cache for expensive dashboard queries."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Tuple

_STORE: Dict[str, Tuple[float, Any]] = {}


def cache_get(key: str):
    item = _STORE.get(key)
    if not item:
        return None
    expires, value = item
    if expires < time.time():
        _STORE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> Any:
    _STORE[key] = (time.time() + ttl_seconds, value)
    return value


def cached(key: str, ttl_seconds: int, loader: Callable[[], Any]) -> Any:
    hit = cache_get(key)
    if hit is not None:
        return hit
    return cache_set(key, loader(), ttl_seconds)
