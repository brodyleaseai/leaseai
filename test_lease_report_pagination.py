from lease_report import generate_lease_abstract_pdf, iter_value_chunks


def test_iter_value_chunks_keeps_short_text():
    assert list(iter_value_chunks("84 months")) == ["84 months"]


def test_iter_value_chunks_splits_long_clause():
    clause = ("Neither Landlord nor Tenant shall be held responsible. " * 80)
    chunks = list(iter_value_chunks(clause, max_chars=200))
    assert len(chunks) > 3
    assert "".join(chunk.replace(" ", "") for chunk in chunks) == clause.replace(" ", "")
    assert all(len(chunk) <= 220 for chunk in chunks)


def test_pdf_builds_with_eighty_fields_and_huge_clause():
    huge = (
        "Neither Landlord nor Tenant shall be held responsible or liable for delays "
        "when caused by acts of God, strikes, lockouts, embargoes, quarantines, "
        "weather, national disasters, inability to obtain labor or materials "
        "(or reasonable substitutes therefor) at reasonable costs, failure of utilities, "
        "governmental restrictions, orders, regulations, national emergencies, "
        "delay in issuance of permits, enemy action, terrorism, riots, fire "
        "or other casualty, and other causes beyond their reasonable control. "
        "Tenant shall not use <hazardous> materials & solvents without consent. "
    ) * 25
    assert len(huge) > 4000

    fields = {}
    for i in range(80):
        fields[f"Field {i+1} Name"] = {
            "value": "NOT FOUND" if i % 5 == 0 else f"Value {i+1}",
            "confidence": "LOW" if i % 5 == 0 else "HIGH",
        }
    fields["Force Majeure Clause"] = {"value": huge, "confidence": "HIGH"}
    fields["CAM Exclusions"] = {
        "value": "Exclusions include original construction costs, capital expenditures, interest, "
                 "principal payments, depreciation, advertising, legal fees, and leasing commissions. " * 20,
        "confidence": "HIGH",
    }

    fields["Lease Commencement Date"] = {
        "value": "2020-07-01 (Target; actual Commencement Date is Delivery of the Premises)",
        "confidence": "MEDIUM",
    }
    fields["Lease Expiration Date"] = {
        "value": "CONDITIONAL: 84 months from the Commencement Date",
        "confidence": "HIGH",
    }
    fields["Lease Term (Total Months)"] = {"value": "84 months", "confidence": "HIGH"}
    fields["Renewal Notice Deadline"] = {
        "value": "Not less than nine (9) months, nor more than twelve (12) months, prior to expiration",
        "confidence": "HIGH",
    }
    fields["Number of Renewal Options"] = {"value": "1", "confidence": "HIGH"}
    fields["Renewal Option Term Length"] = {"value": "3 or 5 years", "confidence": "HIGH"}

    pdf = generate_lease_abstract_pdf(
        {"property_address": "26 North Euclid Ave", "tenant_name": "ARE LLC"},
        fields,
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000


def test_pdf_critical_dates_include_workday_renewal():
    from io import BytesIO

    import pdfplumber

    from test_critical_date_extract import WORKDAY

    fields = {name: {"value": item["raw_value"], "confidence": "HIGH"} for name, item in WORKDAY.items()}
    pdf = generate_lease_abstract_pdf(
        {
            "property_address": "6230 Stoneridge Mall Road, Pleasanton, California",
            "tenant_name": "WORKDAY, INC.",
        },
        fields,
    )
    with pdfplumber.open(BytesIO(pdf)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
    assert "Critical Dates" in text
    assert "Renewal Notice Deadline" in text
    assert "2014-09-30" in text
    assert "Renewal Option Commencement" in text
    assert "Early Termination Right" in text


if __name__ == "__main__":
    test_iter_value_chunks_keeps_short_text()
    test_iter_value_chunks_splits_long_clause()
    test_pdf_builds_with_eighty_fields_and_huge_clause()
    test_pdf_critical_dates_include_workday_renewal()
    print("test_lease_report_pagination.py: all tests passed")
