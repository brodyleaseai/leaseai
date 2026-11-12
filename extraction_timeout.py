"""Run lease extraction with a hard timeout (default 5 minutes).

Uses a daemon thread instead of ThreadPoolExecutor so bulk upload can
queue work without nested executor deadlocks.
"""

from __future__ import annotations

import os
import threading


class ExtractionTimeoutError(TimeoutError):
    pass


def run_extraction_with_timeout(pipeline, **kwargs):
    timeout = int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "300"))
    holder = {}

    def target():
        try:
            holder["result"] = pipeline.process_lease(**kwargs)
        except Exception as exc:
            holder["error"] = exc

    worker = threading.Thread(target=target, daemon=True, name="lease-extraction")
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise ExtractionTimeoutError(
            f"Lease extraction exceeded {timeout} seconds and was stopped."
        )
    if "error" in holder:
        raise holder["error"]
    return holder["result"]
