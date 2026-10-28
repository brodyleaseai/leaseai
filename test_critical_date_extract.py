from datetime import date

from critical_date_extract import critical_dates_from_fields, parse_calendar_date


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
    assert by_type["Expansion Option Deadline"]["date_value"] == "2021-09-01"
    assert [row["date_value"] for row in rows] == sorted(row["date_value"] for row in rows)


def test_empty_fields_return_no_dates():
    assert critical_dates_from_fields({}) == []
    assert critical_dates_from_fields([
        {"field_name": "Lease Expiration Date", "raw_value": "NOT FOUND"},
    ]) == []


if __name__ == "__main__":
    test_parse_skips_conditional_formulas()
    test_building_1400_critical_dates()
    test_empty_fields_return_no_dates()
    print("test_critical_date_extract.py: all tests passed")
