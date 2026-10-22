"""Run lease extraction with a hard timeout (default 5 minutes)."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout


class ExtractionTimeoutError(TimeoutError):
    pass


def run_extraction_with_timeout(pipeline, **kwargs):
    timeout = int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "300"))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(pipeline.process_lease, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            raise ExtractionTimeoutError(
                f"Lease extraction exceeded {timeout} seconds and was stopped."
            ) from exc
