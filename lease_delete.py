"""Delete one or more leases and their related rows."""

from __future__ import annotations

from typing import Iterable, List, Sequence

# Delete children first. Tables that do not exist are skipped.
# CASCADE covers many of these, but extracted_fields / critical_dates
# may not have an ON DELETE FK in every environment.
CHILD_TABLES = (
    "extracted_fields",
    "critical_dates",
    "export_history",
    "lease_processing_status",
    "lease_clause_history",
    "amendment_relationships",
    "amendment_clauses",
    "amendments",
    "asc842_calculations",
    "cam_line_items",
    "cam_dispute_history",
    "cam_statement_uploads",
    "cam_provisions",
    "cam_reconciliations",
    "lease_anomalies",
)


def _ids(lease_ids: Iterable) -> List[str]:
    return [str(lease_id) for lease_id in lease_ids if lease_id]


def _delete_from(supabase_client, table: str, column: str, lease_ids: Sequence[str]) -> None:
    try:
        supabase_client.table(table).delete().in_(column, list(lease_ids)).execute()
    except Exception as exc:
        message = str(exc).lower()
        if "does not exist" in message or "could not find" in message or "42p01" in message:
            return
        raise


def delete_leases(supabase_client, lease_ids: Iterable) -> int:
    """Permanently delete leases and related records. Returns the count requested."""
    ids = _ids(lease_ids)
    if not ids:
        return 0

    for table in CHILD_TABLES:
        _delete_from(supabase_client, table, "lease_id", ids)

    try:
        supabase_client.table("lease_comparisons").delete().in_("lease_a_id", ids).execute()
        supabase_client.table("lease_comparisons").delete().in_("lease_b_id", ids).execute()
    except Exception:
        pass

    supabase_client.table("leases").delete().in_("id", ids).execute()
    return len(ids)


def delete_lease(supabase_client, lease_id) -> int:
    return delete_leases(supabase_client, [lease_id])
