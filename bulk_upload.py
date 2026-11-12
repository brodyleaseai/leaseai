"""Bulk lease upload queue.

Streamlit reruns and a single long request cannot be trusted to finish
three GPT extractions. Copy file bytes into a queue immediately, then
process one lease per run so the remaining files are not dropped.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Callable, Dict, Iterable, List, Optional


def snapshot_uploaded_files(uploaded_files: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    """Copy name + bytes so the Streamlit file uploader can clear on rerun."""
    jobs: List[Dict[str, Any]] = []
    for uploaded in uploaded_files or []:
        if hasattr(uploaded, "getvalue"):
            data = uploaded.getvalue()
        elif hasattr(uploaded, "read"):
            data = uploaded.read()
        else:
            data = uploaded
        name = getattr(uploaded, "name", None) or f"lease-{len(jobs) + 1}.pdf"
        jobs.append({"filename": name, "data": data})
    return jobs


def queue_bulk_jobs(session: dict, uploaded_files, client_id: str) -> List[Dict[str, Any]]:
    jobs = snapshot_uploaded_files(uploaded_files)
    for job in jobs:
        job["client_id"] = client_id
    session["bulk_jobs"] = jobs
    session["bulk_job_index"] = 0
    session["bulk_upload_results"] = []
    return jobs


def next_bulk_job(session: dict) -> Optional[Dict[str, Any]]:
    jobs = session.get("bulk_jobs") or []
    index = int(session.get("bulk_job_index") or 0)
    if index >= len(jobs):
        return None
    return jobs[index]


def record_bulk_result(session: dict, result: dict) -> None:
    session.setdefault("bulk_upload_results", []).append(result)
    session["bulk_job_index"] = int(session.get("bulk_job_index") or 0) + 1


def bulk_queue_finished(session: dict) -> bool:
    jobs = session.get("bulk_jobs") or []
    if not jobs:
        return False
    return int(session.get("bulk_job_index") or 0) >= len(jobs)


def clear_bulk_queue(session: dict) -> None:
    session["bulk_jobs"] = []
    session["bulk_job_index"] = 0


def process_one_job(
    job: dict,
    *,
    supabase_factory: Callable,
    pipeline_factory: Optional[Callable] = None,
    run_extract: Optional[Callable] = None,
    increment_usage: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Extract one queued PDF. Failures are returned, not raised."""
    filename = job.get("filename") or "lease.pdf"
    client_id = job.get("client_id")
    file_data = job.get("data") or b""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_data)
            tmp_path = tmp_file.name

        if pipeline_factory is None:
            from extraction_pipeline import LeaseExtractionPipeline

            pipeline_factory = LeaseExtractionPipeline
        if run_extract is None:
            from extraction_timeout import run_extraction_with_timeout

            run_extract = run_extraction_with_timeout
        if increment_usage is None:
            from usage_limits import increment_usage as increment_usage_fn

            increment_usage = increment_usage_fn

        supabase = supabase_factory()
        pipeline = pipeline_factory()
        property_address = os.path.splitext(filename)[0].replace("_", " ")
        lease_id, extracted_fields = run_extract(
            pipeline,
            pdf_path=tmp_path,
            client_id=client_id,
            supabase_client=supabase,
            property_address=property_address,
            tenant_name="To be reviewed",
            filename=filename,
        )
        increment_usage(supabase, client_id)
        return {
            "filename": filename,
            "status": "success",
            "lease_id": lease_id,
            "field_count": len(extracted_fields or {}),
            "message": f"Extracted {len(extracted_fields or {})} fields",
        }
    except Exception as exc:
        return {
            "filename": filename,
            "status": "error",
            "lease_id": None,
            "field_count": 0,
            "message": str(exc),
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def drain_bulk_queue(session: dict, process_job: Callable[[dict], dict]) -> List[dict]:
    """Process every remaining job. Used by tests; Streamlit drains one per rerun."""
    while next_bulk_job(session) is not None:
        record_bulk_result(session, process_job(next_bulk_job(session)))
    return session.get("bulk_upload_results") or []
