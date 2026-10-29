from lease_field_recovery import (
    apply_lease_escalation,
    clip_postal_address,
    extract_labeled_address,
    merge_extracted_fields,
    parse_basic_provisions,
    recover_lease_fields,
    resolve_annual_escalation,
)
from extraction_pipeline import LeaseExtractionPipeline


ARE_EXCERPT = """
LEASE AGREEMENT
THIS LEASE AGREEMENT (this “Lease”) is made as of this 3 day of October, 2019, between ARE-MA REGION NO 59,
LLC, a Delaware limited liability company (“Landlord”), and CAMP4 THERAPEUTICS CORPORATION, a Delaware
corporation (“Tenant”).
BASIC LEASE PROVISIONS
Address of Building: Building 1400, One Kendall Square, Cambridge, MA 02139
Premises: That portion of the Building in the Project (each as defined below) containing approximately
18,876 rentable square feet, consisting of (i) Suite 14-202 containing approximately 9,772 rentable
square feet, (li) Suite 14-203 containing approximately 5,045 rentable square feet, and
(iii) Suite 14-309 containing approximately 4,059 rentable square feet
Building: The building in the Project currently known and numbered as 1400, One Kendall Square,
Cambridge, Massachusetts
Project: The project commonly known as One Kendall Square
Base Rent: $89.00 per rentable square foot of the Premises per year, subject to adjustment as provided in
Section 4 below.
Rentable Area of Premises: 18,876 rentable square feet
Rentable Area of Project: 815,467 rentable square feet
Rentable Area of Building: 133,989 rentable square feet
Building’s Share of Project: 16.43%
Tenant’s Share: 14.09%
Security Deposit: $1,286,000
Target Commencement Date: July 1, 2020
Rent Adjustment Percentage: 3%
Base Term: Beginning on the Commencement Date and ending 84 months from the Commencement Date.
Permitted Use: Research and development laboratory, related office and other related uses consistent with the
character of the Project
Landlord's Notice Address: 26 North Euclid Avenue Pasadena, CA 91101
Tenant's Notice Address: One Kendall Square, Building 1400 Suite 14-201 Cambridge, MA 02139
Attention: Lease Administrator
The following Exhibits and Addenda are attached hereto and incorporated herein by this reference:
The “Commencement Date” shall be the date Landlord Delivers the Premises to Tenant. The “Rent Commencement Date”
shall be the date that is 5 months after the Commencement Date.
This Lease and Tenant’s interest and rights hereunder are hereby made and shall be subject and
subordinate at all times to the lien of any Mortgage, and Tenant agrees upon demand to execute instruments of attornment
provided any such instruments contain appropriate non-disturbance provisions.
Security Deposit shall be in the form of an unconditional and irrevocable letter of credit
Tenant shall be deemed to have elected arbitration as described in Section 39(b). An Arbitrator shall determine Market Rate.
The Premises shall be expanded to include the Prior Premises, and the Prior Premises containing approximately
11,884 rentable square feet. Commencing on September 1, 2021 (the “Prior Premises Commencement Date”)
In addition to Base Rent, Tenant agrees to pay to Landlord as additional rent Tenant’s Share of Operating Expenses.
"""


REQUIRED_ARE_FIELDS = [
    "Landlord Legal Name",
    "Tenant Legal Name",
    "Property Civic Address",
    "Premises Square Footage (RSF)",
    "Building Total Square Footage",
    "Suite / Unit Number",
    "Floor(s) Occupied",
    "Lease Commencement Date",
    "Rent Commencement Date",
    "Lease Expiration Date",
    "Lease Term (Total Months)",
    "Base Rent Year 1 (monthly)",
    "Base Rent Year 2 (monthly)",
    "Base Rent Year 3 (monthly)",
    "Base Rent Year 4 (monthly)",
    "Base Rent Year 5 (monthly)",
    "Full Rent Schedule (all years)",
    "Free Rent Period (months)",
    "Annual Escalation Rate or Cap",
    "Security Deposit Amount",
    "SNDA Agreement Required",
    "Expansion Option",
]


def test_basic_provisions_parse_are_labels():
    basic = parse_basic_provisions(ARE_EXCERPT)
    assert "One Kendall Square" in basic["Address of Building"]
    assert "18,876" in basic["Rentable Area of Premises"]
    assert "$89.00" in basic["Base Rent"]
    assert "July 1, 2020" in basic["Target Commencement Date"]
    assert basic["Rent Adjustment Percentage"].startswith("3")


def test_recover_are_terms_that_the_report_missed():
    recovered = recover_lease_fields(ARE_EXCERPT)
    assert recovered["Landlord Legal Name"]["value"].startswith("ARE-MA REGION NO 59")
    assert recovered["Tenant Legal Name"]["value"].startswith("CAMP4 THERAPEUTICS")
    assert "Cambridge" in recovered["Property Civic Address"]["value"]
    tenant_addr = recovered.get("Tenant Registered Address", {}).get("value", "")
    assert "Cambridge" in tenant_addr
    assert "14-201" in tenant_addr
    assert "Lease Administrator" in tenant_addr
    assert "Commencement Date" not in tenant_addr
    assert "pipes" not in tenant_addr.lower()
    assert "EXHIBIT" not in tenant_addr
    assert len(tenant_addr) < 160
    assert recovered["Base Rent Year 1 (monthly)"]["value"] == "$139,997.00"
    assert recovered["Base Rent Year 2 (monthly)"]["value"] == "$144,196.91"
    assert recovered["Free Rent Period (months)"]["value"] == "5 months"
    assert "2020-07-01" in recovered["Lease Commencement Date"]["value"]
    assert "5 months after" in recovered["Rent Commencement Date"]["value"]
    assert "84 months" in recovered["Lease Expiration Date"]["value"]
    assert recovered["Lease Term (Total Months)"]["value"] == "84 months"
    assert recovered["Annual Escalation Rate or Cap"]["value"] == "3%"
    assert recovered["Security Deposit Amount"]["value"] == "$1,286,000"
    assert "Floor 2" in recovered["Floor(s) Occupied"]["value"]
    assert "Floor 3" in recovered["Floor(s) Occupied"]["value"]
    assert "14-202" in recovered["Suite / Unit Number"]["value"]
    assert recovered["SNDA Agreement Required"]["value"].startswith("Yes")
    assert "11,884" in recovered["Expansion Option"]["value"]
    for name in REQUIRED_ARE_FIELDS:
        assert name in recovered, name
        assert recovered[name]["value"] != "NOT FOUND", name


def test_merge_overwrites_not_found_model_values():
    pipeline = LeaseExtractionPipeline.__new__(LeaseExtractionPipeline)
    pipeline.lease_fields = [
        "Lease Commencement Date",
        "Base Rent Year 1 (monthly)",
        "Permitted Use",
        "Building Class",
    ]
    model = {
        "Lease Commencement Date": {"value": "NOT FOUND", "confidence": "LOW"},
        "Base Rent Year 1 (monthly)": {"value": "NOT FOUND", "confidence": "LOW"},
        "Permitted Use": {"value": "Research and development laboratory", "confidence": "HIGH"},
    }
    merged = pipeline.complete_extracted_fields(ARE_EXCERPT, model)
    assert "2020-07-01" in merged["Lease Commencement Date"]["value"]
    assert merged["Base Rent Year 1 (monthly)"]["value"] == "$139,997.00"
    assert merged["Permitted Use"]["value"].startswith("Research")
    assert merged["Building Class"]["value"] == "NOT FOUND"


def test_clip_stops_after_attention_and_drops_lease_body():
    blob = (
        "Tenant's Notice Address:\n"
        "One Kendall Square, Building 1400\n"
        "Suite 14-201\n"
        "Cambridge, MA 02139\n"
        "Attention: Lease Administrator\n"
        "The following Exhibits and Addenda are attached hereto\n"
        "1. Lease of Premises. Landlord hereby leases the Premises "
        "and pipes, ducts, conduits, wires and appurtenant fixtures " * 40
    )
    clipped = clip_postal_address(blob)
    assert clipped.startswith("One Kendall Square")
    assert "Lease Administrator" in clipped
    assert "pipes" not in clipped.lower()
    assert "EXHIBIT" not in clipped.upper()
    assert len(clipped) < 160


def test_merge_replaces_overflowing_gpt_tenant_address():
    pipeline = LeaseExtractionPipeline.__new__(LeaseExtractionPipeline)
    pipeline.lease_fields = ["Tenant Registered Address", "Property Civic Address"]
    overflow = (
        "One Kendall Square, Building 1400 Suite 14-201 Cambridge, MA 02139 "
        "Attention: Lease Administrator The following Exhibits " + ("pipes, ducts " * 200)
    )
    merged = pipeline.complete_extracted_fields(ARE_EXCERPT, {
        "Tenant Registered Address": {"value": overflow, "confidence": "HIGH"},
    })
    value = merged["Tenant Registered Address"]["value"]
    assert "14-201" in value
    assert "pipes" not in value.lower()
    assert len(value) < 160


STONERIDGE_RENT_TABLE = """
OFFICE LEASE AGREEMENT
6200 STONERIDGE MALL ROAD INVESTORS LLC and WORKDAY, INC.
Base Rent:
November 1, 2008 – June 30, 2010  30,772 x $1.25 =$38,465.00
July 1, 2010 – June 30, 2011  69,132 x $2.50 =$172,830.00
July 1, 2011 – June 30, 2012  69,132 x $2.58 =$178,014.90
July 1, 2012 – June 30, 2013  69,132 x $2.66 =$183,355.35
July 1, 2013 – June 30, 2014  69,132 x $2.74 =$188,856.01
July 1, 2014 – June 30, 2015  69,132 x $2.82 =$194,521.69
(xix) property management fees to the extent the same exceed three percent (3%) of gross receipts
In the event Tenant validly exercises the 6210 Expansion Option, Base Rent shall be $2.50 per square foot
with a cumulative annual increase of three percent (3%).
"""

FLAT_RENT_LEASE = """
LEASE AGREEMENT between OTHER LANDLORD LLC and OTHER TENANT INC.
Base Rent shall be $5,000.00 per month throughout the Term. There is no annual increase.
"""

CAM_ONLY_THREE_PERCENT = """
LEASE AGREEMENT between CAM LANDLORD LLC and CAM TENANT INC.
Base Rent is $8,000 per month for the entire Term.
Excluded from Expenses: property management fees to the extent the same exceed three percent (3%) of gross receipts.
"""


def test_stoneridge_escalation_is_derived_from_this_lease_schedule():
    resolved = resolve_annual_escalation(STONERIDGE_RENT_TABLE)
    assert resolved["value"] == "3%"
    assert "derived" in resolved["notes"].lower()
    recovered = recover_lease_fields(STONERIDGE_RENT_TABLE)
    assert recovered["Annual Escalation Rate or Cap"]["value"] == "3%"


def test_are_escalation_stays_the_stated_label():
    resolved = resolve_annual_escalation(ARE_EXCERPT)
    assert resolved["value"] == "3%"
    assert "Stated" in resolved["notes"]


def test_cam_or_expansion_three_percent_is_not_this_lease_rate():
    assert resolve_annual_escalation(CAM_ONLY_THREE_PERCENT) is None
    merged = apply_lease_escalation(
        {"Annual Escalation Rate or Cap": {"value": "3%", "confidence": "HIGH"}},
        CAM_ONLY_THREE_PERCENT,
    )
    assert merged["Annual Escalation Rate or Cap"]["value"] == "NOT FOUND"


def test_escalation_is_resolved_per_lease_not_copied():
    other = """
    LEASE AGREEMENT
    Rent Adjustment Percentage: 2.5%
    Base Rent: $10,000 per month
    """
    first = resolve_annual_escalation(ARE_EXCERPT)["value"]
    second = resolve_annual_escalation(other)["value"]
    third = resolve_annual_escalation(STONERIDGE_RENT_TABLE)["value"]
    assert first == "3%"
    assert second == "2.5%"
    assert third == "3%"
    assert resolve_annual_escalation(FLAT_RENT_LEASE) is None


def test_full_are_pdf_recovers_same_economics():
    from pathlib import Path

    pdf = Path("/home/ubuntu/.cursor/projects/workspace/uploads/ARE_LLC_lease_b86b.pdf")
    if not pdf.exists():
        return
    try:
        import pdfplumber
    except ImportError:
        return
    pages = []
    with pdfplumber.open(str(pdf)) as doc:
        for page in doc.pages:
            pages.append(page.extract_text() or "")
    recovered = recover_lease_fields("\n".join(pages))
    assert recovered["Base Rent Year 1 (monthly)"]["value"] == "$139,997.00"
    assert "2020-07-01" in recovered["Lease Commencement Date"]["value"]
    assert recovered["Free Rent Period (months)"]["value"] == "5 months"
    assert "Cambridge" in recovered["Property Civic Address"]["value"]
    assert recovered["Tenant Legal Name"]["value"].startswith("CAMP4")
    tenant_addr = recovered["Tenant Registered Address"]["value"]
    assert extract_labeled_address("\n".join(pages), "Tenant's Notice Address")
    assert "14-201" in tenant_addr
    assert "Lease Administrator" in tenant_addr
    assert "pipes" not in tenant_addr.lower()
    assert len(tenant_addr) < 160


if __name__ == "__main__":
    test_basic_provisions_parse_are_labels()
    test_recover_are_terms_that_the_report_missed()
    test_merge_overwrites_not_found_model_values()
    test_clip_stops_after_attention_and_drops_lease_body()
    test_merge_replaces_overflowing_gpt_tenant_address()
    test_stoneridge_escalation_is_derived_from_this_lease_schedule()
    test_are_escalation_stays_the_stated_label()
    test_cam_or_expansion_three_percent_is_not_this_lease_rate()
    test_escalation_is_resolved_per_lease_not_copied()
    test_full_are_pdf_recovers_same_economics()
    print("test_lease_field_recovery.py: all tests passed")
