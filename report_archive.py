"""Persist generated product PDFs and complete CAM workpapers.

The Streamlit session still holds the latest PDF for download/email. This module
writes the same bytes into Supabase Storage and records them in generated_reports
so abstracts and CAM workpapers survive a restart and can be sold/exported as an
audit trail.

Storage failure must not block structured CAM save or in-app download.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

REPORT_KIND_LEASE_ABSTRACT = "LEASE_ABSTRACT"
REPORT_KIND_CAM_WORKPAPER = "CAM_WORKPAPER"
REPORT_KIND_CAM_STATEMENT = "CAM_STATEMENT"
REPORT_KIND_DISPUTE_LETTER = "DISPUTE_LETTER"

REPORTS_BUCKET = "leaseai-reports"
FALLBACK_BUCKET = "leases"


def jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def money(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def iso_date(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def safe_filename(name: Optional[str]) -> str:
    base = os.path.basename(name or "report.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned or 'report'}.pdf"
    return cleaned


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _first_row(result: Any) -> Dict[str, Any]:
    data = getattr(result, "data", result) or []
    if isinstance(data, dict):
        return data
    if data:
        return data[0]
    return {}


def _lease_org(sb, lease_id: Optional[str]) -> Dict[str, Any]:
    if not lease_id:
        return {}
    try:
        result = (
            sb.table("leases")
            .select("id, client_id, property_address, tenant_name")
            .eq("id", lease_id)
            .execute()
        )
        return _first_row(result)
    except Exception:
        return {}


def _ensure_bucket(sb, bucket: str) -> None:
    create = getattr(sb.storage, "create_bucket", None)
    if not callable(create):
        return
    try:
        create(bucket, {"public": False})
    except Exception:
        pass


def _upload_pdf(sb, bucket: str, path: str, pdf_bytes: bytes) -> None:
    sb.storage.from_(bucket).upload(
        path,
        pdf_bytes,
        {"content-type": "application/pdf", "upsert": "true"},
    )


def store_pdf_bytes(
    sb,
    pdf_bytes: bytes,
    *,
    lease_id: Optional[str],
    kind: str,
    filename: str,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """Upload PDF bytes. Tries leaseai-reports, then the leases bucket."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    year_part = str(year or "none")
    lease_part = lease_id or "unassigned"
    path = f"{lease_part}/{kind}/{year_part}/{stamp}_{safe_filename(filename)}"

    last_error = None
    for bucket in (REPORTS_BUCKET, FALLBACK_BUCKET):
        try:
            _ensure_bucket(sb, bucket)
            if bucket == FALLBACK_BUCKET:
                stored_path = f"generated/{path}"
            else:
                stored_path = path
            _upload_pdf(sb, bucket, stored_path, pdf_bytes)
            storage_url = getattr(sb.storage, "storage_url", "") or ""
            file_url = (
                f"{storage_url}/object/{bucket}/{stored_path}"
                if storage_url
                else stored_path
            )
            return {
                "storage_bucket": bucket,
                "storage_path": stored_path,
                "file_url": file_url,
                "pdf_stored": True,
            }
        except Exception as exc:
            last_error = exc
            continue
    return {
        "storage_bucket": None,
        "storage_path": None,
        "file_url": None,
        "pdf_stored": False,
        "storage_error": str(last_error) if last_error else "Upload failed",
    }


def persist_generated_report(
    sb,
    *,
    lease_id: Optional[str],
    kind: str,
    pdf_bytes: bytes,
    filename: str,
    user_id: Optional[str] = None,
    reconciliation_id: Optional[str] = None,
    reconciliation_year: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Insert a generated_reports row and upload the PDF when storage is available."""
    lease = _lease_org(sb, lease_id)
    stored = store_pdf_bytes(
        sb,
        pdf_bytes,
        lease_id=lease_id,
        kind=kind,
        filename=filename,
        year=reconciliation_year,
    )
    record = {
        "lease_id": lease_id,
        "client_id": lease.get("client_id"),
        "reconciliation_id": reconciliation_id,
        "report_kind": kind,
        "reconciliation_year": reconciliation_year,
        "filename": safe_filename(filename),
        "storage_bucket": stored.get("storage_bucket") or REPORTS_BUCKET,
        "storage_path": stored.get("storage_path") or "",
        "file_url": stored.get("file_url"),
        "file_size_bytes": len(pdf_bytes),
        "content_sha256": sha256_bytes(pdf_bytes),
        "content_type": "application/pdf",
        "metadata": jsonable(metadata or {}),
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if not stored.get("pdf_stored"):
        record["metadata"] = jsonable(
            {
                **(metadata or {}),
                "storage_error": stored.get("storage_error"),
            }
        )
    row: Dict[str, Any] = {}
    try:
        result = sb.table("generated_reports").insert(record).execute()
        row = _first_row(result)
    except Exception as exc:
        stored["storage_error"] = stored.get("storage_error") or str(exc)
    return {
        "generated_report_id": row.get("id"),
        "pdf_stored": bool(stored.get("pdf_stored")),
        "storage_bucket": stored.get("storage_bucket"),
        "storage_path": stored.get("storage_path"),
        "file_url": stored.get("file_url"),
        "storage_error": stored.get("storage_error"),
        "filename": record["filename"],
        "content_sha256": record["content_sha256"],
        "file_size_bytes": record["file_size_bytes"],
    }


def download_stored_pdf(sb, bucket: str, path: str) -> Optional[bytes]:
    if not bucket or not path:
        return None
    try:
        data = sb.storage.from_(bucket).download(path)
    except Exception:
        return None
    if data is None:
        return None
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, dict):
        inner = data.get("data") or data.get("body")
        if isinstance(inner, (bytes, bytearray)):
            return bytes(inner)
    return None


def fetch_stored_report(
    sb,
    *,
    reconciliation_id: Optional[str] = None,
    report_id: Optional[str] = None,
    lease_id: Optional[str] = None,
    kind: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    query = sb.table("generated_reports").select("*")
    if report_id:
        query = query.eq("id", report_id)
    elif reconciliation_id:
        query = query.eq("reconciliation_id", reconciliation_id)
    elif lease_id and kind:
        query = query.eq("lease_id", lease_id).eq("report_kind", kind)
    else:
        return None
    try:
        if hasattr(query, "order"):
            query = query.order("created_at", desc=True)
        result = query.execute()
    except Exception:
        return None
    rows = getattr(result, "data", None) or []
    if not rows:
        return None
    row = rows[0]
    pdf_bytes = download_stored_pdf(
        sb, row.get("storage_bucket") or "", row.get("storage_path") or ""
    )
    return {"row": row, "pdf_bytes": pdf_bytes}


def line_item_record(
    reconciliation_id: str, item: Dict[str, Any], index: int
) -> Dict[str, Any]:
    amount = money(item.get("landlord_amount") if item.get("landlord_amount") is not None else item.get("amount")) or 0.0
    challenge = bool(item.get("should_challenge") or item.get("is_excluded") or item.get("is_disputed"))
    variance = item.get("variance_amount")
    if variance is None:
        variance = item.get("variance")
    return {
        "reconciliation_id": reconciliation_id,
        "line_number": item.get("line_number") or index + 1,
        "category": item.get("category"),
        "description": item.get("description") or item.get("item") or item.get("name"),
        "landlord_amount": amount,
        "calculated_amount": money(item.get("calculated_amount")),
        "variance_amount": money(variance),
        "is_disputed": bool(item.get("is_disputed") or challenge),
        "is_excluded": bool(item.get("is_excluded")),
        "is_over_cap": bool(item.get("is_over_cap")),
        "dispute_reason": item.get("dispute_reason") or item.get("exclusion_reason"),
        "recommended_action": item.get("recommended_action")
        or ("CHALLENGE" if challenge else "ACCEPT"),
        "should_challenge": challenge,
    }


def _schema_gap(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in ("column", "schema cache", "does not exist", "pgrst", "generated_reports")
    )


CORE_RECON_KEYS = (
    "lease_id",
    "reconciliation_year",
    "statement_date",
    "landlord_total_charges",
    "landlord_tenant_share",
    "calculated_total_charges",
    "calculated_tenant_share",
    "variance_amount",
    "variance_percentage",
    "status",
    "dispute_status",
    "uploaded_by",
    "uploaded_at",
    "updated_at",
)


def _upsert_reconciliation(sb, record: Dict[str, Any]):
    try:
        return (
            sb.table("cam_reconciliations")
            .upsert(record, on_conflict="lease_id,reconciliation_year")
            .execute()
        )
    except Exception as exc:
        if not _schema_gap(exc):
            raise
        slim = {key: record[key] for key in CORE_RECON_KEYS if key in record}
        return (
            sb.table("cam_reconciliations")
            .upsert(slim, on_conflict="lease_id,reconciliation_year")
            .execute()
        )


def replace_line_items(
    sb, reconciliation_id: str, line_items: List[Dict[str, Any]]
) -> int:
    sb.table("cam_line_items").delete().eq("reconciliation_id", reconciliation_id).execute()
    rows = [
        line_item_record(reconciliation_id, item, index)
        for index, item in enumerate(line_items or [])
    ]
    if not rows:
        return 0
    try:
        sb.table("cam_line_items").insert(rows).execute()
    except Exception as exc:
        if not _schema_gap(exc):
            raise
        slim_rows = [
            {key: value for key, value in row.items() if key != "should_challenge"}
            for row in rows
        ]
        sb.table("cam_line_items").insert(slim_rows).execute()
    return len(rows)

def cam_reconciliation_record(
    lease_id: str,
    results: Dict[str, Any],
    user_id: Optional[str],
) -> Dict[str, Any]:
    remaining = money(results.get("lease_remaining_due"))
    variance = money(results.get("variance")) or 0.0
    if abs(variance) >= 100 or (remaining is not None and remaining > 0):
        dispute_status = "CHALLENGE_DRAFTED"
        status = "DISCREPANCY_FOUND"
    else:
        dispute_status = "NOT_DISPUTED"
        status = "UNDER_REVIEW"
    allowable = money(
        results.get("allowable_building_charges")
        if results.get("allowable_building_charges") is not None
        else results.get("calculated_total_charges")
    )
    return {
        "lease_id": lease_id,
        "reconciliation_year": int(results["recon_year"]),
        "statement_date": iso_date(results.get("statement_date")),
        "landlord_total_charges": money(results.get("landlord_total")),
        "landlord_tenant_share": money(results.get("tenant_share_billed")),
        "calculated_total_charges": allowable,
        "calculated_tenant_share": money(results.get("calculated_share")),
        "variance_amount": variance,
        "variance_percentage": money(results.get("variance_percentage")),
        "estimated_cam_paid": money(results.get("estimated_cam_paid")),
        "landlord_trueup_billed": money(results.get("landlord_trueup_billed")),
        "lease_remaining_due": remaining,
        "excluded_building_charges": money(results.get("excluded_building_charges")) or 0.0,
        "allowable_building_charges": allowable,
        "cam_cap_applied": bool(results.get("cam_cap_applied")),
        "calculation_steps": jsonable(results.get("calculations") or []),
        "status": status,
        "dispute_status": dispute_status,
        "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def persist_cam_reconciliation(
    sb,
    *,
    lease_id: str,
    results: Dict[str, Any],
    line_items: Optional[List[Dict[str, Any]]] = None,
    pdf_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Upsert the lease-year CAM workpaper, replace line items, archive the PDF."""
    record = cam_reconciliation_record(lease_id, results, user_id)
    saved = _upsert_reconciliation(sb, record)
    recon = _first_row(saved)
    recon_id = recon.get("id")
    if not recon_id:
        lookup = (
            sb.table("cam_reconciliations")
            .select("id")
            .eq("lease_id", lease_id)
            .eq("reconciliation_year", record["reconciliation_year"])
            .execute()
        )
        recon_id = _first_row(lookup).get("id")
        recon = {**recon, **_first_row(lookup)}

    line_count = replace_line_items(sb, recon_id, line_items or [])

    report_info: Dict[str, Any] = {
        "generated_report_id": None,
        "pdf_stored": False,
        "file_url": None,
        "storage_path": None,
        "storage_bucket": None,
    }
    if pdf_bytes:
        year = record["reconciliation_year"]
        report_info = persist_generated_report(
            sb,
            lease_id=lease_id,
            kind=REPORT_KIND_CAM_WORKPAPER,
            pdf_bytes=pdf_bytes,
            filename=filename or f"CAM_Workpaper_{year}.pdf",
            user_id=user_id,
            reconciliation_id=recon_id,
            reconciliation_year=year,
            metadata={
                "estimated_cam_paid": record.get("estimated_cam_paid"),
                "lease_remaining_due": record.get("lease_remaining_due"),
                "landlord_trueup_billed": record.get("landlord_trueup_billed"),
                "cam_cap_applied": record.get("cam_cap_applied"),
                "variance_amount": record.get("variance_amount"),
            },
        )
        patch = {
            "reconciliation_report_url": report_info.get("file_url")
            or report_info.get("storage_path"),
            "generated_report_id": report_info.get("generated_report_id"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            sb.table("cam_reconciliations").update(patch).eq("id", recon_id).execute()
        except Exception as exc:
            if not _schema_gap(exc):
                raise
            slim_patch = {
                "reconciliation_report_url": patch["reconciliation_report_url"],
            }
            sb.table("cam_reconciliations").update(slim_patch).eq("id", recon_id).execute()

    return {
        "reconciliation_id": recon_id,
        "line_item_count": line_count,
        "generated_report_id": report_info.get("generated_report_id"),
        "pdf_stored": bool(report_info.get("pdf_stored")),
        "file_url": report_info.get("file_url"),
        "storage_path": report_info.get("storage_path"),
        "storage_bucket": report_info.get("storage_bucket"),
        "storage_error": report_info.get("storage_error"),
        "estimated_cam_paid": record.get("estimated_cam_paid"),
        "lease_remaining_due": record.get("lease_remaining_due"),
    }


SCHEMA_HINT = (
    "Database tables for the reports archive may not be set up yet. "
    "In the Supabase SQL Editor run database_schema_cam_reconciliation.sql "
    "then database_schema_generated_reports.sql."
)
