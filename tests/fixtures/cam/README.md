# Synthetic CAM test pair

Two text-based PDFs for an end-to-end CAM reconciliation test. The parties,
property, and charges are fictional. Each page is watermarked
**SYNTHETIC TEST DOCUMENT**.

| File | What to upload |
| --- | --- |
| `Northridge_Meridian_Tower_Office_Lease.pdf` | Lease upload / extract first |
| `Northridge_2025_CAM_Reconciliation_Statement.pdf` | CAM Reconciliation → New Reconciliation → statement upload |

Regenerate with:

```bash
python tests/fixtures/cam/generate_cam_test_pdfs.py
```

## Hypothetical deal

- **Landlord:** Northridge Office Partners, LLC
- **Tenant:** Cascade Analytics, Inc.
- **Property:** The Meridian Tower, 1200 Cascade Plaza, Portland, Oregon 97204, Suite 400
- **Size:** 12,500 RSF / 100,000 RSF building = **12.50%** pro-rata
- **Term:** January 1, 2023 – December 31, 2027 (Modified Gross)
- **CAM Base Year:** 2023
- **CAM Base Amount:** $100,000.00 (tenant share in 2023)
- **CAM cap:** 5% of the base amount → **max tenant CAM $105,000.00**
- **No CAM stop** (the current engine treats a stop as “share minus stop,” which would distort this test)
- **Exclusions:** capital improvements, structural repairs, roof replacement, depreciation, debt service, mortgage payments, legal fees relating to other tenants
- **Audit right:** yes, within 90 days of the statement

## 2025 landlord statement (planted errors)

The statement is written the way a landlord would send it — it includes costs the lease does not allow.

- **Total Building Charges:** $1,200,000.00
- **Tenant Share Billed:** $150,000.00 (12.50% of $1,200,000)
- **Estimated CAM paid in 2025:** $108,000.00
- **Balance due on the statement:** $42,000.00

Planted excluded line items (included in the $1,200,000):

- Roof replacement (capital improvement) — $180,000.00
- Structural steel repairs — $40,000.00
- Legal fees — eviction of unrelated tenant — $14,000.00
- Depreciation expense — $25,000.00
- Mortgage interest / debt service — $120,000.00

## What LeaseAI should compute

1. Remove the five excluded lines from the building total: $1,200,000 − $379,000 = **$821,000**
2. Tenant 12.50% of allowable costs = **$102,625**
3. Cap ceiling is $100,000 + 5% = **$105,000** (does not bind; $102,625 is below the cap)
4. Billed $150,000 − calculated $102,625 = **$47,375 overcharge**
5. Recommendation: **CHALLENGE**

Step 2 should fill from the statement after **Parse CAM Statement with AI**. If you still need to type it:

- Reconciliation year: **2025**
- Statement date: **March 15, 2026**
- Total Landlord Charges: **1200000** (building total, not the $42,000 balance due)
- Tenant Share Billed: **150000** (12.50% of $1,200,000)

Parse must keep all **23** numbered lines. The last five are planted exclusions (roof, structural, legal, depreciation, debt service). If only 18 appear, page 2 was dropped.

## Suggested test path

1. Upload the lease PDF and let extraction finish. Confirm tenant **Cascade Analytics, Inc.**, address **1200 Cascade Plaza**, RSF **12,500**, CAM cap **5%**, and CAM exclusions.
2. Open **CAM Reconciliation** → **New Reconciliation**. Select this lease.
3. If CAM provisions are empty, click **Extract CAM Provisions with AI**. Confirm 12.50% share, base year 2023, 5% cap, audit right yes.
4. Upload the 2025 statement → **Parse CAM Statement with AI**. Confirm **23** line items (18 operating + 5 exclusions), Step 2 totals of $1,200,000 / $150,000, and an automatic reconciliation.
5. Expect billed $150,000, correct $105,000, overcharge $45,000. The five shaded rows should be flagged to challenge.
6. Download the PDF report and, because variance exceeds $100, generate the dispute letter. Save the reconciliation and check Dashboard / History.

The dollar variance comes from the cap. GPT may also note the capital / debt-service rows; automatic line-item “challenge” flags only fire when the engine category string matches an exclusion category (for example `CAPITAL_IMPROVEMENTS`).
