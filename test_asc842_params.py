from datetime import date

from asc842_params import (
    fields_from_rows,
    params_from_extracted_fields,
    parse_date_value,
    parse_money,
    parse_months,
    parse_percent,
    source_labels,
    widget_key,
)


def test_parse_money_and_percent():
    assert parse_money("$4,500/month") == 4500.0
    assert parse_percent("3%") == 3.0
    assert parse_percent("2.5 percent") == 2.5
    assert parse_months("60 months") == 60
    assert parse_months("5 years") == 60


def test_params_follow_extracted_lease():
    fields = {
        "Lease Commencement Date": {"raw_value": "2024-02-01"},
        "Lease Expiration Date": {"raw_value": "2029-01-31"},
        "Base Rent Year 1 (monthly)": {"raw_value": "$4,500 per month"},
        "Annual Escalation Rate or Cap": {"raw_value": "3%"},
        "Number of Renewal Options": {"raw_value": "2"},
        "Renewal Option Term Length": {"raw_value": "5 years"},
        "Early Termination Right": {"raw_value": "Tenant may terminate after year 3"},
        "Early Termination Fee / Penalty": {"raw_value": "$10,000"},
    }
    params = params_from_extracted_fields(fields)
    assert params["commencement_date"] == date(2024, 2, 1)
    assert params["end_date"] == date(2029, 1, 31)
    assert params["monthly_payment"] == 4500.0
    assert params["annual_increase"] == 3.0
    assert params["has_renewal"] is True
    assert params["renewal_months"] == 60
    assert params["has_termination"] is True
    assert params["termination_penalty"] == 10000.0
    assert params["source_rent"] is True


def test_different_lease_changes_rent():
    a = params_from_extracted_fields({
        "Base Rent Year 1 (monthly)": {"value": "5000"},
        "Lease Commencement Date": {"value": "2023-01-01"},
        "Lease Expiration Date": {"value": "2026-01-01"},
    })
    b = params_from_extracted_fields({
        "Base Rent Year 1 (monthly)": {"value": "1800"},
        "Lease Commencement Date": {"value": "2025-06-01"},
        "Lease Expiration Date": {"value": "2030-05-31"},
    })
    assert a["monthly_payment"] != b["monthly_payment"]
    assert a["commencement_date"] != b["commencement_date"]


def test_fields_from_rows():
    mapped = fields_from_rows([
        {"field_name": "Base Rent Year 1 (monthly)", "raw_value": "1200"},
        {"field_name": "Lease Commencement Date", "reviewed_value": "2024-03-01"},
    ])
    params = params_from_extracted_fields(mapped)
    assert params["monthly_payment"] == 1200.0
    assert params["commencement_date"] == date(2024, 3, 1)


def test_reviewed_value_beats_raw_and_skips_not_found():
    fields = {
        "Base Rent Year 1 (monthly)": {
            "raw_value": "$9,999",
            "reviewed_value": "$2,200 per month",
        },
        "Lease Commencement Date": {"raw_value": "NOT FOUND"},
        "Lease Expiration Date": {"reviewed_value": "N/A", "raw_value": "2028-12-31"},
        "Annual Escalation Rate or Cap": {"value": "NOT FOUND"},
    }
    params = params_from_extracted_fields(fields)
    assert params["monthly_payment"] == 2200.0
    assert params["end_date"] == date(2028, 12, 31)
    assert params["source_commencement"] is False
    assert params["source_increase"] is False
    assert "monthly rent" in source_labels(params)
    assert "commencement date" not in source_labels(params)


def test_widget_keys_change_with_lease():
    assert widget_key("lease-a", "monthly") != widget_key("lease-b", "monthly")
    assert widget_key("lease-a", "monthly") == "asc842_lease-a_monthly"


def test_building_1400_conditional_term_becomes_end_date():
    assert parse_date_value("CONDITIONAL: 84 months from the Commencement Date") is None
    assert parse_date_value("2020-07-01 (Target; actual Commencement Date is Delivery of the Premises)") == date(2020, 7, 1)
    params = params_from_extracted_fields({
        "Lease Commencement Date": {
            "raw_value": "2020-07-01 (Target; actual Commencement Date is Delivery of the Premises)",
        },
        "Lease Expiration Date": {
            "raw_value": "CONDITIONAL: 84 months from the Commencement Date",
        },
        "Lease Term (Total Months)": {"raw_value": "84 months"},
        "Base Rent Year 1 (monthly)": {"raw_value": "$139,997.00"},
    })
    assert params["commencement_date"] == date(2020, 7, 1)
    assert params["end_date"] == date(2027, 7, 1)
    assert params["source_end"] is True
    assert params["monthly_payment"] == 139997.0


def test_stoneridge_phased_commencement_uses_phase_one():
    assert parse_date_value(
        "CONDITIONAL: Phase I Premises: November 1, 2008; Phase II Premises: July 1, 2010"
    ) == date(2008, 11, 1)
    params = params_from_extracted_fields({
        "Lease Commencement Date": {
            "raw_value": "CONDITIONAL: Phase I Premises: November 1, 2008; Phase II Premises: July 1, 2010",
        },
        "Lease Expiration Date": {"raw_value": "2015-06-30"},
        "Base Rent Year 1 (monthly)": {"raw_value": "$38,465.00"},
        "Annual Escalation Rate or Cap": {"raw_value": "3%"},
        "Number of Renewal Options": {"raw_value": "1"},
        "Renewal Option Term Length": {"raw_value": "3 or 5 years"},
    })
    assert params["commencement_date"] == date(2008, 11, 1)
    assert params["end_date"] == date(2015, 6, 30)
    assert params["monthly_payment"] == 38465.0
    assert params["source_commencement"] is True
    assert "Phase I" in params["commencement_note"]
    assert params["end_date"] > params["commencement_date"]


def test_end_date_formula_without_separate_term_field():
    params = params_from_extracted_fields({
        "Lease Commencement Date": {"value": "July 1, 2020"},
        "Lease Expiration Date": {"value": "ending 84 months from the Commencement Date"},
    })
    assert params["end_date"] == date(2027, 7, 1)


if __name__ == "__main__":
    test_parse_money_and_percent()
    test_params_follow_extracted_lease()
    test_different_lease_changes_rent()
    test_fields_from_rows()
    test_reviewed_value_beats_raw_and_skips_not_found()
    test_widget_keys_change_with_lease()
    test_building_1400_conditional_term_becomes_end_date()
    test_stoneridge_phased_commencement_uses_phase_one()
    test_end_date_formula_without_separate_term_field()
    print("test_asc842_params.py: all tests passed")
