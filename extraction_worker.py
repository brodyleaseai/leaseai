"""
Optional background worker for queued lease extractions.
Run: python extraction_worker.py
"""

from __future__ import annotations

import time
from datetime import datetime

from supabase import create_client

import config
from extraction_pipeline import LeaseExtractionPipeline
from extraction_timeout import ExtractionTimeoutError, run_extraction_with_timeout
from observability import init_observability, log_event, persist_log


def main():
    init_observability()
    sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    pipeline = LeaseExtractionPipeline()
    log_event("worker", "Extraction worker started")

    while True:
        try:
            jobs = (
                sb.table("extraction_jobs")
                .select("*")
                .eq("status", "QUEUED")
                .order("created_at")
                .limit(1)
                .execute()
            )
            if not jobs.data:
                time.sleep(5)
                continue

            job = jobs.data[0]
            sb.table("extraction_jobs").update({
                "status": "PROCESSING",
                "started_at": datetime.utcnow().isoformat(),
            }).eq("id", job["id"]).execute()

            try:
                lease_id, _fields = run_extraction_with_timeout(
                    pipeline,
                    pdf_path=job.get("pdf_path"),
                    client_id=job.get("client_id"),
                    supabase_client=sb,
                    filename=job.get("filename"),
                )
                sb.table("extraction_jobs").update({
                    "status": "COMPLETE",
                    "lease_id": lease_id,
                    "finished_at": datetime.utcnow().isoformat(),
                }).eq("id", job["id"]).execute()
                persist_log(sb, "extraction_complete", f"Job {job['id']} done", lease_id=lease_id)
            except ExtractionTimeoutError as exc:
                sb.table("extraction_jobs").update({
                    "status": "FAILED",
                    "error_message": str(exc),
                    "finished_at": datetime.utcnow().isoformat(),
                }).eq("id", job["id"]).execute()
                persist_log(sb, "extraction_timeout", str(exc), level="error")
            except Exception as exc:
                sb.table("extraction_jobs").update({
                    "status": "FAILED",
                    "error_message": str(exc),
                    "finished_at": datetime.utcnow().isoformat(),
                }).eq("id", job["id"]).execute()
                persist_log(sb, "extraction_failed", str(exc), level="error")
        except KeyboardInterrupt:
            log_event("worker", "Extraction worker stopped")
            return
        except Exception as exc:
            log_event("worker", f"Loop error: {exc}", level="error")
            time.sleep(5)


if __name__ == "__main__":
    main()
