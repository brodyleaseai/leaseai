"""Turn governing rent-schedule text into monthly ASC 842 cash flows."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from dateutil.relativedelta import relativedelta

from amendment_clause_links import implied_schedule_rsf, parse_rate_periods, parse_rsf

SCHEDULE_ROW = re.compile(
    r"Year\s+\d+\s+\((?P<start>[^–\-\n]+)[–\-](?P<end>[^)]+)\):\s*"
    r"(?:\$?(?P<rate>[\d,.]+)/RSF/year\s*=\s*)?\$?(?P<monthly>[\d,.]+)/month",
    re.IGNORECASE,
)
SIMPLE_MONTHLY = re.compile(
    r"\$\s?([\d,]+(?:\.\d{1,2})?)\s*(?:per\s+month|/month|monthly)",
    re.IGNORECASE,
)
PREFIX_RSF = re.compile(
    r"on\s+(\d{1,3}(?:,\d{3})+|\d+)\s+RSF",
    re.IGNORECASE,
)


def parse_date(value: Any) -> Optional[datetime]:
    """Parse ISO, US, or 'October 1, 2028' dates."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return datetime(value.year, value.month, value.day)
    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return None
    if re.match(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    cleaned = text.replace(",", "")
    for fmt in ("%B %d %Y", "%b %d %Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(cleaned[:32], fmt)
        except ValueError:
            continue
    return None


def iso_date(value: Any) -> Optional[str]:
    parsed = parse_date(value)
    return parsed.strftime("%Y-%m-%d") if parsed else None


def _money(value: str) -> float:
    return float(str(value).replace(",", "").replace("$", "").strip())


def parse_schedule_rows(text: str) -> List[Dict[str, Any]]:
    """Parse `Year N (start–end): $rate/RSF/year = $monthly/month` rows."""
    rows: List[Dict[str, Any]] = []
    for match in SCHEDULE_ROW.finditer(text or ""):
        start = parse_date(match.group("start"))
        end = parse_date(match.group("end"))
        if not start or not end:
            continue
        monthly = _money(match.group("monthly"))
        rate = match.group("rate")
        rows.append(
            {
                "start": start,
                "end": end,
                "monthly": monthly,
                "annual_rate": _money(rate) if rate else None,
            }
        )
    return rows


def parse_simple_monthly(text: str) -> Optional[float]:
    match = SIMPLE_MONTHLY.search(text or "")
    if not match:
        return None
    amount = _money(match.group(1))
    return amount if amount > 0 else None


def schedule_rsf(text: str) -> Optional[int]:
    prefix = PREFIX_RSF.search(text or "")
    if prefix:
        try:
            return int(prefix.group(1).replace(",", ""))
        except ValueError:
            pass
    return implied_schedule_rsf(text) or parse_rsf(text)


def rows_from_rate_table(text: str, rsf: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fallback when the clause is a raw $/RSF table instead of a Year N schedule."""
    billed = rsf or parse_rsf(text)
    if not billed:
        return []
    rows = []
    for period in parse_rate_periods(text):
        start = parse_date(period["start"])
        end = parse_date(period["end"])
        if not start or not end:
            continue
        rows.append(
            {
                "start": start,
                "end": end,
                "monthly": round(billed * period["annual_rate"] / 12.0, 2),
                "annual_rate": period["annual_rate"],
            }
        )
    return rows


def expand_monthly_payments(
    rows: Iterable[Dict[str, Any]],
    start_on: Optional[Any] = None,
    end_on: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """One payment on the first of each month in each row, inclusive of the start month."""
    floor = parse_date(start_on)
    ceiling = parse_date(end_on)
    payments: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        current = row["start"]
        end = row["end"]
        monthly = float(row["monthly"])
        while current <= end:
            key = current.strftime("%Y-%m-%d")
            if (floor is None or current >= floor) and (ceiling is None or current <= ceiling):
                if key not in seen:
                    payments.append({"date": key, "amount": round(monthly, 2)})
                    seen.add(key)
            current = current + relativedelta(months=1)
    payments.sort(key=lambda item: item["date"])
    return payments


def payments_from_schedule_text(
    text: str,
    start_on: Optional[Any] = None,
    end_on: Optional[Any] = None,
    rsf: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows = parse_schedule_rows(text)
    if not rows:
        rows = rows_from_rate_table(text, rsf=rsf)
    if not rows:
        monthly = parse_simple_monthly(text)
        start = parse_date(start_on)
        end = parse_date(end_on)
        if monthly and start and end:
            rows = [{"start": start, "end": end, "monthly": monthly, "annual_rate": None}]
    return expand_monthly_payments(rows, start_on=start_on, end_on=end_on)


def escalate_flat_payments(
    monthly: float,
    start_on: Any,
    end_on: Any,
    annual_increase: float = 0.0,
) -> List[Dict[str, Any]]:
    """Year-1 rent plus a flat annual increase — the existing calculator path."""
    start = parse_date(start_on)
    end = parse_date(end_on)
    if not start or not end or monthly <= 0:
        return []
    payments = []
    current = start
    amount = float(monthly)
    month = 0
    while current <= end:
        if annual_increase and month > 0 and month % 12 == 0:
            amount *= 1 + annual_increase
        payments.append({"date": current.strftime("%Y-%m-%d"), "amount": round(amount, 2)})
        current = current + relativedelta(months=1)
        month += 1
    return payments


def overlay_payments(
    base: Iterable[Dict[str, Any]],
    overlay: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Keep the continuous base curve; overlay parsed amendment amounts by date."""
    by_date = {row["date"]: dict(row) for row in base or []}
    for row in overlay or []:
        by_date[row["date"]] = dict(row)
    return [by_date[key] for key in sorted(by_date)]


def remaining_payments(
    payments: Iterable[Dict[str, Any]],
    from_date: Any,
) -> List[Dict[str, Any]]:
    cutoff = parse_date(from_date)
    if not cutoff:
        return list(payments)
    key = cutoff.strftime("%Y-%m-%d")
    return [row for row in payments if row["date"] >= key]


def first_monthly(payments: Iterable[Dict[str, Any]]) -> float:
    rows = list(payments)
    return float(rows[0]["amount"]) if rows else 0.0
