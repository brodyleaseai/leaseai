"""Tests for scanned-PDF text quality and empty-abstract detection."""

from extraction_pipeline import count_found_fields, is_extractable_text


def test_junk_page_glyphs_are_not_extractable():
    junk = ("l " * 80) + "1 2 3 4 5\n" + ("Page 1\n" * 10)
    assert not is_extractable_text(junk)


def test_empty_and_short_text_are_not_extractable():
    assert not is_extractable_text("")
    assert not is_extractable_text("NOT FOUND")
    assert not is_extractable_text("TW Associates LLC")


def test_real_lease_language_is_extractable():
    text = """
    This Triple Net Lease Agreement is made as of January 15, 2024, between
    Auburn Industrial Holdings LLC, as Landlord, and TW Associates LLC, as Tenant,
    for the premises at 420 37th Street, Auburn, Washington. The lease term is
    sixty months commencing February 1, 2024 and expiring January 31, 2029.
    Base rent for year one is four thousand five hundred dollars per month.
    Tenant shall pay all real property taxes, insurance, and common area
    maintenance charges. Tenant may renew for two additional five-year periods
    upon twelve months prior written notice. Security deposit equals two months
    of base rent. Permitted use is warehouse and light industrial operations.
    """
    assert is_extractable_text(text)


def test_count_found_fields_ignores_not_found():
    fields = {
        "Tenant Legal Name": {"value": "TW Associates LLC", "confidence": "HIGH"},
        "Property Civic Address": {"value": "420 37th St, Auburn, Washington", "confidence": "HIGH"},
        "Lease Type": {"value": "NOT FOUND", "confidence": "LOW"},
        "Base Rent Year 1 (monthly)": {"value": "NOT FOUND", "confidence": "LOW"},
        "Permitted Use": {"value": "", "confidence": "LOW"},
    }
    assert count_found_fields(fields) == 2


if __name__ == "__main__":
    test_junk_page_glyphs_are_not_extractable()
    test_empty_and_short_text_are_not_extractable()
    test_real_lease_language_is_extractable()
    test_count_found_fields_ignores_not_found()
    print("test_extraction_quality.py: all tests passed")
