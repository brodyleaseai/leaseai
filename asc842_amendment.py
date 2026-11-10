"""ASC 842 / IFRS 16 measurement from the Amendment Resolution Graph.

Clients do not upload a restated lease PDF. This module reads the governing
rent schedule as of a date and either:

* measures the original lease at commencement, or
* remeasures at the amendment effective date (ASC 842-10-25-11 / IFRS 16.45).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from amendment_clause_links import parse_rsf
from amendment_graph_helpers import lease_client_name
from amendment_report import build_amendment_resolution_model
from report_sources import clause_source, format_source_line
from asc842_cashflows import (
    escalate_flat_payments,
    first_monthly,
    iso_date,
    overlay_payments,
    parse_date,
    payments_from_schedule_text,
    remaining_payments,
    schedule_rsf,
)
from asc842_engine import ASC842ComplianceEngine

RENT_CLAUSES = {"Base Rent", "Rent Schedule", "Rent Escalations"}
SCOPE_CLAUSES = {"Premises Description", "Expansion of Premises", "Premises"}
TERM_CLAUSES = {
    "Lease Term",
    "Lease Expiration Date",
    "Expiration Date",
    "Lease End Date",
    "Commencement Date",
    "Lease Commencement Date",
}
ACCOUNTING_CLAUSES = RENT_CLAUSES | SCOPE_CLAUSES | TERM_CLAUSES

KIND_INITIAL = "INITIAL"
KIND_CONSIDERATION = "CONSIDERATION"
KIND_PARTIAL_TERMINATION = "PARTIAL_TERMINATION"
KIND_SCOPE_INCREASE = "SCOPE_INCREASE"
KIND_TERM_CHANGE = "TERM_CHANGE"
KIND_NONE = "NO_ACCOUNTING_CHANGE"

MODE_COMMENCEMENT = "commencement"
MODE_REMEASUREMENT = "remeasurement"


def clause_map(model: Optional[dict]) -> Dict[str, dict]:
    return {
        clause.get("clause_type"): clause
        for clause in (model or {}).get("clauses") or []
        if clause.get("clause_type")
    }


def _clause_text(clause: Optional[dict], key: str) -> str:
    if not clause:
        return ""
    return str(clause.get(key) or "").strip()


def _amendment_when(amendment: dict) -> Optional[str]:
    return iso_date(
        amendment.get("effective_date")
        or amendment.get("amendment_date")
        or amendment.get("effective_from")
        or amendment.get("created_at")
    )


def _row_when(row: dict) -> Optional[str]:
    return iso_date(
        row.get("effective_from")
        or row.get("effective_date")
        or row.get("amendment_date")
        or row.get("created_at")
    )


def _version_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _history_rank(row: dict) -> tuple:
    when = parse_date(_row_when(row))
    return (_version_int(row.get("version_number")), when or datetime.min)


def history_as_of(rows: Optional[Iterable[dict]], as_of: Any) -> List[dict]:
    """Keep versions in force on as_of and mark the latest of each type current."""
    cutoff = parse_date(as_of)
    kept: List[dict] = []
    for row in rows or []:
        when = parse_date(_row_when(row))
        if cutoff and when and when > cutoff:
            continue
        kept.append(dict(row))
    latest: Dict[str, int] = {}
    for index, row in enumerate(kept):
        name = row.get("clause_type")
        if not name:
            continue
        prior = latest.get(name)
        if prior is None or _history_rank(row) >= _history_rank(kept[prior]):
            latest[name] = index
    for index, row in enumerate(kept):
        row["is_current"] = latest.get(row.get("clause_type")) == index
    return kept


def amendments_as_of(amendments: Optional[Iterable[dict]], as_of: Any) -> List[dict]:
    cutoff = parse_date(as_of)
    kept = []
    for amendment in amendments or []:
        when = parse_date(_amendment_when(amendment))
        if cutoff and when and when > cutoff:
            continue
        kept.append(amendment)
    return kept


def clauses_as_of(rows: Optional[Iterable[dict]], as_of: Any) -> List[dict]:
    cutoff = parse_date(as_of)
    kept = []
    for row in rows or []:
        when = parse_date(_row_when(row))
        if cutoff and when and when > cutoff:
            continue
        kept.append(row)
    return kept


def resolution_as_of(
    lease: Optional[dict],
    amendments: Optional[Iterable[dict]],
    history_rows: Optional[Iterable[dict]],
    as_of: Any,
    amendment_clauses: Optional[Iterable[dict]] = None,
    prepared_for: Optional[str] = None,
) -> Dict[str, Any]:
    as_of_iso = iso_date(as_of)
    return build_amendment_resolution_model(
        lease,
        amendments_as_of(amendments, as_of),
        history_as_of(history_rows, as_of),
        as_of=as_of_iso,
        prepared_for=prepared_for,
        amendment_clauses=clauses_as_of(amendment_clauses, as_of),
    )


def _rsf_from_clause(clause: Optional[dict], key: str) -> Optional[int]:
    text = _clause_text(clause, key)
    return schedule_rsf(text) or parse_rsf(text)


def premises_rsf(model: Optional[dict], key: str = "governing_value") -> Optional[int]:
    clauses = clause_map(model)
    for name in ("Premises Description", "Expansion of Premises", "Premises", "Rent Schedule"):
        value = _rsf_from_clause(clauses.get(name), key)
        if value:
            return value
    return None


def rent_schedule_text(model: Optional[dict], key: str = "governing_value") -> str:
    clauses = clause_map(model)
    schedule = clauses.get("Rent Schedule")
    if schedule and _clause_text(schedule, key):
        return _clause_text(schedule, key)
    return _clause_text(clauses.get("Base Rent"), key)


def latest_accounting_effective_date(model: Optional[dict]) -> Optional[str]:
    latest = None
    for clause in (model or {}).get("changed_clauses") or (model or {}).get("clauses") or []:
        if clause.get("clause_type") not in ACCOUNTING_CLAUSES:
            continue
        when = iso_date(clause.get("effective_from") or clause.get("governing_amendment_date"))
        if when and (latest is None or when > latest):
            latest = when
    for amendment in (model or {}).get("amendments") or []:
        when = _amendment_when(amendment)
        if when and (latest is None or when > latest):
            latest = when
    return latest


def classify_modification(
    current_model: Optional[dict],
    prior_model: Optional[dict] = None,
) -> Dict[str, Any]:
    """Decide how the as-of governing file changes measurement."""
    current = current_model or {}
    prior = prior_model or {}
    amendments = list(current.get("amendments") or [])
    modification_date = latest_accounting_effective_date(current)
    current_rsf = premises_rsf(current, "governing_value")
    prior_rsf = premises_rsf(prior, "governing_value") or premises_rsf(current, "original_value")
    current_rent = rent_schedule_text(current, "governing_value")
    prior_rent = rent_schedule_text(prior, "governing_value") or rent_schedule_text(
        current, "original_value"
    )
    scope_ratio = 0.0
    kind = KIND_NONE
    if not amendments:
        kind = KIND_INITIAL
    elif current_rsf and prior_rsf and current_rsf < prior_rsf:
        kind = KIND_PARTIAL_TERMINATION
        scope_ratio = (prior_rsf - current_rsf) / float(prior_rsf)
    elif current_rsf and prior_rsf and current_rsf > prior_rsf:
        kind = KIND_SCOPE_INCREASE
    elif current_rent and prior_rent and current_rent != prior_rent:
        kind = KIND_CONSIDERATION
    else:
        changed = {
            clause.get("clause_type")
            for clause in current.get("changed_clauses") or []
        }
        if changed & TERM_CLAUSES:
            kind = KIND_TERM_CHANGE
        elif changed & ACCOUNTING_CLAUSES:
            kind = KIND_CONSIDERATION
        elif amendments:
            kind = KIND_CONSIDERATION

    clauses = clause_map(current)
    cite_clause = clauses.get("Rent Schedule") or clauses.get("Base Rent")
    cite = clause_source(cite_clause, "governing") if cite_clause else {}
    return {
        "kind": kind,
        "modification_date": modification_date,
        "amendments_applied": len(amendments),
        "prior_rsf": prior_rsf,
        "governing_rsf": current_rsf,
        "scope_reduction_ratio": round(scope_ratio, 6),
        "surrendered_rsf": (prior_rsf - current_rsf) if prior_rsf and current_rsf and current_rsf < prior_rsf else 0,
        "prior_schedule": prior_rent,
        "governing_schedule": current_rent,
        "governing_source": format_source_line(cite) if cite_clause else "",
        "governing_source_document": cite.get("document") or "",
        "governing_source_excerpt": cite.get("excerpt") or "",
        "is_modification": kind not in {KIND_INITIAL, KIND_NONE} or bool(amendments),
    }


def payments_for_model(
    model: Optional[dict],
    *,
    key: str = "governing_value",
    start_on: Optional[Any] = None,
    end_on: Optional[Any] = None,
    fallback_monthly: float = 0.0,
    fallback_increase: float = 0.0,
) -> List[Dict[str, Any]]:
    text = rent_schedule_text(model, key)
    rsf = premises_rsf(model, key)
    payments = payments_from_schedule_text(text, start_on=start_on, end_on=end_on, rsf=rsf)
    if payments:
        return payments
    if fallback_monthly and start_on and end_on:
        return escalate_flat_payments(
            fallback_monthly, start_on, end_on, annual_increase=fallback_increase
        )
    return []


def day_before(value: Any) -> Optional[str]:
    parsed = parse_date(value)
    if not parsed:
        return None
    return (parsed - timedelta(days=1)).strftime("%Y-%m-%d")


def build_measurement(
    lease: Optional[dict],
    amendments: Optional[Iterable[dict]],
    history_rows: Optional[Iterable[dict]],
    *,
    as_of: Any,
    mode: str = MODE_REMEASUREMENT,
    amendment_clauses: Optional[Iterable[dict]] = None,
    commencement_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    fallback_monthly: float = 0.0,
    fallback_increase: float = 0.0,
    prepared_for: Optional[str] = None,
) -> Dict[str, Any]:
    """Build original and (if requested) as-amended cash flows from the graph."""
    current = resolution_as_of(
        lease,
        amendments,
        history_rows,
        as_of,
        amendment_clauses=amendment_clauses,
        prepared_for=prepared_for,
    )
    classification = classify_modification(current)
    modification_date = classification["modification_date"] or iso_date(as_of)
    prior = current
    if modification_date:
        prior_as_of = day_before(modification_date)
        prior = resolution_as_of(
            lease,
            amendments,
            history_rows,
            prior_as_of,
            amendment_clauses=amendment_clauses,
            prepared_for=prepared_for,
        )
        classification = classify_modification(current, prior)

    start = commencement_date or iso_date(as_of)
    finish = end_date
    fallback = []
    if fallback_monthly and start and finish:
        fallback = escalate_flat_payments(
            fallback_monthly, start, finish, annual_increase=fallback_increase
        )
    base_original = payments_for_model(
        current,
        key="original_value",
        start_on=start,
        end_on=finish,
        fallback_monthly=fallback_monthly,
        fallback_increase=fallback_increase,
    )
    prior_governing = payments_for_model(
        prior if mode == MODE_REMEASUREMENT else current,
        key="governing_value",
        start_on=start,
        end_on=finish,
        fallback_monthly=fallback_monthly,
        fallback_increase=fallback_increase,
    )
    original_payments = overlay_payments(fallback, overlay_payments(base_original, prior_governing))
    revised_full = overlay_payments(
        fallback,
        payments_for_model(
            current,
            key="governing_value",
            start_on=start,
            end_on=finish,
            fallback_monthly=fallback_monthly,
            fallback_increase=fallback_increase,
        ),
    )
    revised_payments = remaining_payments(revised_full, modification_date or as_of)
    return {
        "mode": mode,
        "as_of": iso_date(as_of),
        "current_model": current,
        "prior_model": prior,
        "classification": classification,
        "modification_date": modification_date,
        "original_payments": original_payments,
        "revised_payments": revised_payments,
        "first_revised_monthly": first_monthly(revised_payments),
        "first_original_monthly": first_monthly(original_payments),
        "amendments": current.get("amendments") or [],
    }


def _engine_data(
    base: Dict[str, Any],
    payments: List[Dict[str, Any]],
    start: Any,
    end: Any,
    discount_rate: float,
) -> Dict[str, Any]:
    data = dict(base)
    data["explicit_payments"] = payments
    data["commencement_date"] = iso_date(start)
    data["end_date"] = iso_date(end) or (payments[-1]["date"] if payments else iso_date(start))
    data["monthly_payment"] = first_monthly(payments) or float(base.get("monthly_payment") or 0)
    data["discount_rate"] = discount_rate
    data["annual_rent_increases"] = 0.0
    return data


def run_amended_calculation(
    original_lease_data: Dict[str, Any],
    revised_payments: List[Dict[str, Any]],
    *,
    modification_date: Any,
    revised_discount_rate: Optional[float] = None,
    scope_reduction_ratio: float = 0.0,
    classification: Optional[dict] = None,
) -> Dict[str, Any]:
    """Roll the pre-mod schedule to the effective date, then remeasure remaining payments."""
    original = dict(original_lease_data)
    original_engine = ASC842ComplianceEngine(original)
    original_results = original_engine.run_full_calculation()
    carrying = original_engine.balances_as_of(modification_date)

    ratio = max(0.0, min(float(scope_reduction_ratio or 0.0), 0.999999))
    derecognized_liability = round(carrying["liability"] * ratio, 2)
    derecognized_rou = round(carrying["rou"] * ratio, 2)
    remaining_liability = round(carrying["liability"] - derecognized_liability, 2)
    remaining_rou = round(carrying["rou"] - derecognized_rou, 2)
    gain_loss = round(derecognized_liability - derecognized_rou, 2)

    rate = (
        revised_discount_rate
        if revised_discount_rate is not None
        else float(original.get("discount_rate") or 0.05)
    )
    revised_data = _engine_data(
        original,
        revised_payments,
        modification_date,
        revised_payments[-1]["date"] if revised_payments else modification_date,
        rate,
    )
    # Remeasurement does not re-capitalize commencement costs.
    revised_data["initial_direct_costs"] = 0.0
    revised_data["lease_incentives"] = 0.0
    revised_data["prepayments"] = 0.0
    revised_engine = ASC842ComplianceEngine(revised_data)
    new_liability = revised_engine.calculate_initial_lease_liability()
    rou_adjustment = round(new_liability - remaining_liability, 2)
    new_rou = round(remaining_rou + rou_adjustment, 2)
    revised_engine.set_remeasured_balances(new_liability, new_rou)
    subsequent = revised_engine.run_full_calculation()

    kind = (classification or {}).get("kind") or (
        KIND_PARTIAL_TERMINATION if ratio else KIND_CONSIDERATION
    )
    modification_entry = {
        "entry_type": "LEASE_MODIFICATION",
        "date": iso_date(modification_date),
        "description": (
            f"ASC 842 / IFRS 16 remeasurement ({kind}) as of {iso_date(modification_date)}"
        ),
        "lines": _modification_lines(
            remaining_liability,
            new_liability,
            remaining_rou,
            new_rou,
            derecognized_liability,
            derecognized_rou,
            gain_loss,
        ),
    }

    return {
        "measurement_kind": kind,
        "modification_date": iso_date(modification_date),
        "scope_reduction_ratio": ratio,
        "carrying": carrying,
        "partial_termination": {
            "derecognized_liability": derecognized_liability,
            "derecognized_rou": derecognized_rou,
            "remaining_liability": remaining_liability,
            "remaining_rou": remaining_rou,
            "gain_loss": gain_loss,
        },
        "remeasured_liability": new_liability,
        "remeasured_rou": new_rou,
        "rou_adjustment": rou_adjustment,
        "liability_adjustment": round(new_liability - remaining_liability, 2),
        "revised_discount_rate": rate,
        "original_results": original_results,
        "subsequent_results": subsequent,
        "modification_journal_entry": modification_entry,
        "classification": classification or {},
        "warnings": list(original_engine.warnings) + list(revised_engine.warnings),
        "errors": list(original_engine.errors) + list(revised_engine.errors),
    }


def _modification_lines(
    remaining_liability: float,
    new_liability: float,
    remaining_rou: float,
    new_rou: float,
    derecognized_liability: float,
    derecognized_rou: float,
    gain_loss: float,
) -> List[Dict[str, float]]:
    lines: List[Dict[str, Any]] = []
    if derecognized_liability or derecognized_rou:
        if derecognized_liability:
            lines.append(
                {
                    "account": "Lease Liability",
                    "debit": derecognized_liability,
                    "credit": 0,
                }
            )
        if derecognized_rou:
            lines.append(
                {
                    "account": "ROU Asset - Lease",
                    "debit": 0,
                    "credit": derecognized_rou,
                }
            )
        if gain_loss > 0:
            lines.append(
                {
                    "account": "Gain on Lease Modification",
                    "debit": 0,
                    "credit": gain_loss,
                }
            )
        elif gain_loss < 0:
            lines.append(
                {
                    "account": "Loss on Lease Modification",
                    "debit": abs(gain_loss),
                    "credit": 0,
                }
            )
    delta_l = round(new_liability - remaining_liability, 2)
    if abs(delta_l) < 1:
        delta_l = 0.0
    if delta_l > 0:
        lines.append({"account": "ROU Asset - Lease", "debit": delta_l, "credit": 0})
        lines.append({"account": "Lease Liability", "debit": 0, "credit": delta_l})
    elif delta_l < 0:
        lines.append({"account": "Lease Liability", "debit": abs(delta_l), "credit": 0})
        lines.append({"account": "ROU Asset - Lease", "debit": 0, "credit": abs(delta_l)})
    if not lines:
        lines.append(
            {
                "account": "No remeasurement adjustment",
                "debit": 0,
                "credit": 0,
            }
        )
    return lines


def latest_amendment_date(amendments: Optional[Iterable[dict]]) -> Optional[str]:
    dates = [_amendment_when(item) for item in amendments or []]
    dates = [item for item in dates if item]
    return max(dates) if dates else None


def amendment_counts_by_lease(supabase) -> Dict[str, int]:
    """How many amendment rows each lease has, for selectbox labels."""
    try:
        rows = supabase.table("amendments").select("lease_id").execute().data or []
    except Exception:
        return {}
    counts: Dict[str, int] = {}
    for row in rows:
        lease_id = str(row.get("lease_id") or "")
        if lease_id:
            counts[lease_id] = counts.get(lease_id, 0) + 1
    return counts


def enrich_lease_client(supabase, lease: Optional[dict]) -> Dict[str, Any]:
    """Attach clients.name when the lease query did not join it."""
    lease = dict(lease or {})
    client = lease.get("clients")
    if isinstance(client, list) and client:
        client = client[0]
    if isinstance(client, dict) and (client.get("name") or client.get("company_name")):
        return lease
    client_id = lease.get("client_id")
    if not client_id:
        return lease
    try:
        rows = (
            supabase.table("clients")
            .select("name, company_name")
            .eq("id", client_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            lease["clients"] = rows[0]
    except Exception:
        pass
    return lease


def _normalize_amendment_row(row: dict) -> dict:
    normalized = dict(row or {})
    if not normalized.get("amendment_id") and normalized.get("id"):
        normalized["amendment_id"] = normalized["id"]
    return normalized


def _amendments_from_table(supabase, lease_id: str) -> List[dict]:
    rows = (
        supabase.table("amendments")
        .select("id, lease_id, amendment_number, amendment_date, effective_date, status, extracted_data")
        .eq("lease_id", lease_id)
        .order("amendment_number")
        .execute()
        .data
        or []
    )
    return [_normalize_amendment_row(row) for row in rows]


def load_amendment_bundle(supabase, lease_id: str) -> Dict[str, Any]:
    """Load the resolution-graph inputs for one lease. Missing tables stay empty."""
    load_error = None
    lease = {}
    try:
        rows = supabase.table("leases").select("*").eq("id", lease_id).limit(1).execute().data or []
        lease = enrich_lease_client(supabase, rows[0] if rows else {})
    except Exception as exc:
        lease = {}
        load_error = str(exc)
    amendments: List[dict] = []
    try:
        amendments = [
            _normalize_amendment_row(row)
            for row in (
                supabase.rpc("get_amendment_chain", {"p_lease_id": lease_id}).execute().data or []
            )
        ]
    except Exception as exc:
        load_error = str(exc)
        amendments = []
    if not amendments:
        try:
            amendments = _amendments_from_table(supabase, lease_id)
        except Exception as exc:
            load_error = load_error or str(exc)
    history: List[dict] = []
    try:
        history = (
            supabase.table("lease_clause_history").select("*").eq("lease_id", lease_id).execute().data
            or []
        )
    except Exception:
        history = []
    clauses: List[dict] = []
    for amendment in amendments:
        amendment_id = amendment.get("amendment_id") or amendment.get("id")
        if not amendment_id:
            continue
        try:
            clauses.extend(
                supabase.table("amendment_clauses")
                .select("*")
                .eq("amendment_id", amendment_id)
                .execute()
                .data
                or []
            )
        except Exception:
            pass
        try:
            full = (
                supabase.table("amendments")
                .select("extracted_data, effective_date")
                .eq("id", amendment_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if full:
                amendment["extracted_data"] = full[0].get("extracted_data")
                if full[0].get("effective_date") and not amendment.get("effective_date"):
                    amendment["effective_date"] = full[0]["effective_date"]
        except Exception:
            pass
    return {
        "lease": lease,
        "amendments": amendments,
        "history": history,
        "amendment_clauses": clauses,
        "load_error": load_error,
    }


def summarize_amendments(amendments: Iterable[dict]) -> List[str]:
    labels = []
    for amendment in amendments:
        number = amendment.get("amendment_number") or "?"
        when = _amendment_when(amendment) or amendment.get("amendment_date") or ""
        labels.append(f"Amendment No. {number} ({when})".strip())
    return labels


def public_measurement_preview(measurement: Dict[str, Any]) -> Dict[str, Any]:
    classification = measurement.get("classification") or {}
    revised = measurement.get("revised_payments") or []
    return {
        "mode": measurement.get("mode"),
        "as_of": measurement.get("as_of"),
        "modification_date": measurement.get("modification_date"),
        "kind": classification.get("kind"),
        "amendments": summarize_amendments(measurement.get("amendments") or []),
        "prior_rsf": classification.get("prior_rsf"),
        "governing_rsf": classification.get("governing_rsf"),
        "surrendered_rsf": classification.get("surrendered_rsf"),
        "scope_reduction_ratio": classification.get("scope_reduction_ratio"),
        "first_original_monthly": measurement.get("first_original_monthly"),
        "first_revised_monthly": measurement.get("first_revised_monthly"),
        "revised_payment_count": len(revised),
        "governing_schedule": classification.get("governing_schedule"),
        "governing_source": classification.get("governing_source"),
        "governing_source_document": classification.get("governing_source_document"),
        "governing_source_excerpt": classification.get("governing_source_excerpt"),
        "is_modification": classification.get("is_modification"),
    }
