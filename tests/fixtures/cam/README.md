# Synthetic CAM test pairs

Two fictional deals, each with a lease PDF and a landlord CAM statement.
Every page is watermarked **SYNTHETIC TEST DOCUMENT**.

Regenerate both pairs with:

```bash
python tests/fixtures/cam/generate_cam_test_pdfs.py
```

---

# Northridge / Cascade Analytics (office)

Cap does **not** bind after exclusions are stripped.

| File | What to upload |
| --- | --- |
| `Northridge_Meridian_Tower_Office_Lease.pdf` | Lease upload / extract first |
| `Northridge_2025_CAM_Reconciliation_Statement.pdf` | CAM Reconciliation → New Reconciliation → statement upload |

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
5. Expect billed **$150,000**, calculated **$102,625**, overcharge **$47,375**. The five shaded rows should be flagged to challenge. The 5% cap ceiling is $105,000 and does not bind.
6. Download the PDF report and, because variance exceeds $100, generate the dispute letter. Save the reconciliation and check Dashboard / History.

---

# Ironwood / Pinnacle Fresh (retail grocery)

A second, different deal so the app is not tuned to a single office statement. **20%** share, **2024** statement, **4%** cap that **does bind** after exclusions.

| File | What to upload |
| --- | --- |
| `Ironwood_Shops_Grocery_Lease.pdf` | Lease upload / extract first |
| `Ironwood_2024_CAM_Reconciliation_Statement.pdf` | CAM Reconciliation → New Reconciliation → statement upload |

## Hypothetical deal

- **Landlord:** Ironwood Retail Partners, LLC
- **Tenant:** Pinnacle Grocery Company dba Pinnacle Fresh
- **Property:** The Ironwood Shops, 4800 East Colfax Avenue, Denver, Colorado 80220, Suite 100
- **Size:** 8,000 RSF / 40,000 RSF building = **20.00%** pro-rata
- **Term:** March 1, 2022 – February 28, 2032 (Triple Net)
- **CAM Base Year:** 2022
- **CAM Base Amount:** $80,000.00 (tenant share in 2022)
- **CAM cap:** 4% of the base amount → **max tenant CAM $83,200.00**
- **No CAM stop**
- **Exclusions:** capital improvements, parking lot reconstruction, HVAC replacement, roof replacement, legal fees relating to other tenants
- **Audit right:** yes, within 60 days of the statement
- **No depreciation or debt service** on this statement (unlike Northridge)

## 2024 landlord statement (planted errors)

- **Total Building Charges:** $723,000.00
- **Tenant Share Billed:** $144,600.00 (20.00% of $723,000)
- **Estimated CAM paid in 2024:** $84,000.00
- **Balance due on the statement:** $60,600.00

Planted excluded line items (included in the $723,000):

- Parking lot reconstruction (capital) — $90,000.00
- Rooftop HVAC replacement (capital) — $75,000.00
- Roof replacement — grocery wing — $50,000.00
- Legal fees — eviction of vacant-space tenant — $8,000.00

## What LeaseAI should compute

1. Remove the four excluded lines from the building total: $723,000 − $223,000 = **$500,000**
2. Tenant 20.00% of allowable costs = **$100,000**
3. Cap ceiling is $80,000 + 4% = **$83,200** (binds; $100,000 is above the cap)
4. Billed $144,600 − calculated $83,200 = **$61,400 overcharge**
5. Recommendation: **CHALLENGE**

Step 2 after parse:

- Reconciliation year: **2024**
- Statement date: **February 28, 2025**
- Total Landlord Charges: **723000**
- Tenant Share Billed: **144600**

Parse must keep all **20** numbered lines. The last four are planted exclusions.

## Suggested test path

1. Upload the Ironwood lease PDF. Confirm tenant **Pinnacle Grocery Company**, address **4800 East Colfax**, RSF **8,000**, CAM cap **4%**, and CAM exclusions (no debt service / depreciation).
2. Open **CAM Reconciliation** → **New Reconciliation**. Select this lease.
3. Extract CAM provisions if empty. Confirm **20.00%** share, base year **2022**, **4%** cap, audit right yes.
4. Upload the 2024 statement → **Parse CAM Statement with AI**. Confirm **20** line items (16 operating + 4 exclusions), Step 2 totals of $723,000 / $144,600.
5. Expect billed **$144,600**, calculated **$83,200**, overcharge **$61,400**, and **CAM cap applied**. The four shaded capital/roof/legal rows should be flagged to challenge.
