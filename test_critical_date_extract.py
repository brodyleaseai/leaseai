from datetime import date

from critical_date_extract import (
    critical_dates_from_fields,
    parse_calendar_date,
    parse_count,
    records_for_database,
    _notice_window,
)


BUILDING_1400 = {
    "Lease Commencement Date": {
        "raw_value": "2020-07-01 (Target; actual Commencement Date is Delivery of the Premises)",
    },
    "Rent Commencement Date": {
        "raw_value": "CONDITIONAL: 5 months after the Commencement Date",
    },
    "Lease Expiration Date": {
        "raw_value": "CONDITIONAL: 84 months from the Commencement Date",
    },
    "Lease Term (Total Months)": {"raw_value": "84 months"},
    "Renewal Notice Deadline": {
        "raw_value": "At least 12 months and not more than 15 months prior to the expiration of the Base Term",
    },
    "Expansion Option": {
        "raw_value": "Yes — Prior Premises of 11,884 rentable square feet are added on September 1, 2021",
    },
}


def test_parse_skips_conditional_formulas():
    assert parse_calendar_date("CONDITIONAL: 84 months from the Commencement Date") is None
    assert parse_calendar_date("2020-07-01 (Target; actual Delivery)") == date(2020, 7, 1)
    assert parse_calendar_date("September 1, 2021") == date(2021, 9, 1)


def test_building_1400_critical_dates():
    rows = critical_dates_from_fields(BUILDING_1400)
    by_type = {row["date_type"]: row for row in rows}
    assert by_type["Lease Commencement"]["date_value"] == "2020-07-01"
    assert by_type["Rent Commencement"]["date_value"] == "2020-12-01"
    assert by_type["Lease Expiration"]["date_value"] == "2027-07-01"
    assert by_type["Renewal Notice Deadline"]["date_value"] == "2026-07-01"
    assert by_type["Renewal Notice Window Opens"]["date_value"] == "2026-04-01"
    assert by_type["Expansion Option Deadline"]["date_value"] == "2021-09-01"
    assert [row["date_value"] for row in rows] == sorted(row["date_value"] for row in rows)


WORKDAY = {
    "Lease Commencement Date": {
        "raw_value": "CONDITIONAL: Phase I Premises: November 1, 2008; Phase II Premises: July 1, 2010",
    },
    "Rent Commencement Date": {
        "raw_value": "CONDITIONAL: Phase I Premises: November 1, 2008; Phase II Premises: July 1, 2010",
    },
    "Lease Expiration Date": {"raw_value": "2015-06-30"},
    "Free Rent Period (months)": {"raw_value": "3 months"},
    "Number of Renewal Options": {"raw_value": "1"},
    "Renewal Option Term Length": {"raw_value": "3 or 5 years"},
    "Renewal Notice Deadline": {
        "raw_value": "Not less than nine (9) months, nor more than twelve (12) months, prior to the date on which the Extension Term will commence",
    },
    "Early Termination Right": {"raw_value": "Yes, effective June 30, 2010"},
    "Termination Notice Period": {"raw_value": "No later than July 31, 2009"},
    "Expansion Option": {"raw_value": "Yes, for 6210 and 6230 Stoneridge"},
    "Right of First Offer": {"raw_value": "Yes, for 6210 Stoneridge"},
}


def test_written_notice_window_and_counts():
    assert parse_count("nine (9)") == 9
    assert parse_count("twelve (12)") == 12
    assert _notice_window(
        "Not less than nine (9) months, nor more than twelve (12) months, prior to the Extension Term"
    ) == (12, 9)


def test_workday_renewal_and_option_dates():
    rows = critical_dates_from_fields(WORKDAY)
    by_type = {row["date_type"]: row for row in rows}
    assert by_type["Lease Expiration"]["date_value"] == "2015-06-30"
    assert by_type["Renewal Notice Window Opens"]["date_value"] == "2014-06-30"
    assert by_type["Renewal Notice Deadline"]["date_value"] == "2014-09-30"
    assert by_type["Renewal Option Commencement"]["date_value"] == "2015-06-30"
    assert "3 or 5 years" in by_type["Renewal Option Commencement"]["description"]
    assert by_type["Early Termination Right"]["date_value"] == "2010-06-30"
    assert by_type["Termination Notice Deadline"]["date_value"] == "2009-07-31"
    assert by_type["Free Rent Ends"]["date_value"] == "2009-02-01"
    assert by_type["Expansion Option"]["date_value"] == "See notes"
    assert by_type["Right of First Offer"]["date_value"] == "See notes"
    saved = records_for_database("lease-1", rows)
    assert all(row["date_value"] != "See notes" for row in saved)
    assert any(row["date_type"] == "Renewal Notice Deadline" for row in saved)


def test_empty_fields_return_no_dates():
    assert critical_dates_from_fields({}) == []
    assert critical_dates_from_fields([
        {"field_name": "Lease Expiration Date", "raw_value": "NOT FOUND"},
    ]) == []


if __name__ == "__main__":
    test_parse_skips_conditional_formulas()
    test_building_1400_critical_dates()
    test_written_notice_window_and_counts()
    test_workday_renewal_and_option_dates()
    test_empty_fields_return_no_dates()
    print("test_critical_date_extract.py: all tests passed")
