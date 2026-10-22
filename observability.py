"""
Sentry error tracking and structured JSON logs for production.
Safe to import when Sentry is not installed or not configured.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Optional

_initialized = False


def init_observability() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    dsn = os.getenv("SENTRY_DSN") or getattr(
        __import__("config", fromlist=["SENTRY_DSN"]), "SENTRY_DSN", ""
    )
    if dsn and not str(dsn).startswith("https://your-sentry"):
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=dsn,
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                environment=os.getenv("LEASEAI_ENV", "production"),
            )
            log_event("observability", "Sentry initialized")
        except Exception as exc:
            log_event("observability", f"Sentry not started: {exc}", level="warning")


def log_event(
    event_type: str,
    message: str,
    level: str = "info",
    **fields: Any,
) -> None:
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "event": event_type,
        "message": message,
        **fields,
    }
    line = json.dumps(payload, default=str)
    logger = logging.getLogger("leaseai")
    if level == "error":
        logger.error(line)
    elif level == "warning":
        logger.warning(line)
    else:
        logger.info(line)


def capture_exception(exc: Exception, **fields: Any) -> None:
    log_event("exception", str(exc), level="error", traceback=traceback.format_exc(), **fields)
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def persist_log(supabase_client, event_type: str, message: str, user_id: Optional[str] = None, **fields) -> None:
    log_event(event_type, message, **fields)
    if not supabase_client:
        return
    try:
        supabase_client.table("application_logs").insert({
            "event_type": event_type,
            "message": message,
            "user_id": user_id,
            "details": fields,
        }).execute()
    except Exception:
        pass
