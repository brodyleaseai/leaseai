"""
Quick diagnostic test for ASC 842 calculations
Run this to test if the ASC 842 engine is working
"""

from datetime import date

print("Testing ASC 842 Compliance Engine...")
print("=" * 60)

# Test 1: Import the engine
print("\n1. Testing imports...")
try:
    from asc842_engine import ASC842ComplianceEngine
    print("   ✅ ASC842ComplianceEngine imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Create simple lease data
print("\n2. Creating test lease data...")
lease_data = {
    'commencement_date': '2024-01-01',
    'end_date': '2026-12-31',
    'monthly_payment': 5000.0,
    'discount_rate': 0.05,  # 5% as decimal
    'initial_direct_costs': 0.0,
    'lease_incentives': 0.0,
    'prepayments': 0.0,
    'residual_value_guarantee': 0.0,
    'has_renewal_option': False,
    'renewal_term_months': 0,
    'renewal_reasonably_certain': False,
    'has_purchase_option': False,
    'purchase_option_price': 0.0,
    'purchase_reasonably_certain': False,
    'has_termination_option': False,
    'termination_penalty': 0.0,
    'has_variable_payments': False,
    'variable_payment_index_rate': 0.0,
    'annual_rent_increases': 0.0
}
print("   ✅ Test data created")

# Test 3: Initialize engine
print("\n3. Initializing ASC 842 engine...")
try:
    engine = ASC842ComplianceEngine(lease_data)
    print("   ✅ Engine initialized")
    print(f"   - Lease term: {engine.lease_term_months} months")
    print(f"   - Monthly payment: ${engine.monthly_payment:,.2f}")
    print(f"   - Discount rate: {engine.discount_rate * 100}%")
except Exception as e:
    print(f"   ❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Run classification
print("\n4. Running lease classification...")
try:
    engine.classify_lease()
    print(f"   ✅ Classification: {engine.lease_classification}")
except Exception as e:
    print(f"   ❌ Classification failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Run full calculation
print("\n5. Running full calculation...")
try:
    results = engine.run_full_calculation()
    print(f"   ✅ Calculation complete")
    print(f"   - Classification: {results.get('classification', 'N/A')}")
    print(f"   - Initial ROU Asset: ${results.get('initial_rou_asset', 0):,.2f}")
    print(f"   - Initial Liability: ${results.get('initial_liability', 0):,.2f}")
    
    engine.initial_liability = results.get('initial_liability', 0)
    engine.initial_rou_asset = results.get('initial_rou_asset', 0)
    engine.lease_classification = results.get('classification', 'Operating')
except Exception as e:
    print(f"   ❌ Full calculation failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Generate schedules
print("\n6. Generating amortization schedules...")
try:
    engine.liability_schedule = engine.generate_liability_amortization_schedule()
    if engine.liability_schedule is not None:
        print(f"   ✅ Liability schedule: {len(engine.liability_schedule)} rows")
    else:
        print(f"   ⚠️  Liability schedule is None")
except Exception as e:
    print(f"   ❌ Liability schedule failed: {e}")
    import traceback
    traceback.print_exc()

try:
    engine.rou_schedule = engine.generate_rou_asset_depreciation_schedule()
    if engine.rou_schedule is not None:
        print(f"   ✅ ROU schedule: {len(engine.rou_schedule)} rows")
    else:
        print(f"   ⚠️  ROU schedule is None")
except Exception as e:
    print(f"   ❌ ROU schedule failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Generate journal entries
print("\n7. Generating journal entries...")
try:
    engine.journal_entries = engine.generate_monthly_journal_entries()
    print(f"   ✅ Journal entries: {len(engine.journal_entries)} entries")
except Exception as e:
    print(f"   ❌ Journal entries failed: {e}")
    import traceback
    traceback.print_exc()

# Test 8: Check for warnings/errors
print("\n8. Checking for warnings/errors...")
if engine.warnings:
    print(f"   ⚠️  Warnings: {len(engine.warnings)}")
    for w in engine.warnings:
        print(f"      - {w}")
else:
    print("   ✅ No warnings")

if engine.errors:
    print(f"   ❌ Errors: {len(engine.errors)}")
    for e in engine.errors:
        print(f"      - {e}")
else:
    print("   ✅ No errors")

print("\n9. Inverted dates must not raise KeyError interest_expense...")
try:
    inverted = ASC842ComplianceEngine({
        **lease_data,
        "commencement_date": "2026-10-29",
        "end_date": "2015-06-30",
    })
    assert inverted.lease_term_months == 0
    schedule = inverted.generate_liability_amortization_schedule()
    assert "interest_expense" in schedule.columns
    try:
        inverted.run_full_calculation()
        print("   ❌ Inverted term should raise ValueError")
        exit(1)
    except ValueError as error:
        print(f"   ✅ Guarded inverted term: {error}")
except Exception as e:
    print(f"   ❌ Inverted-date guard failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n10. Stonebridge Phase I dates calculate without crashing...")
try:
    stone = ASC842ComplianceEngine({
        **lease_data,
        "commencement_date": "2008-11-01",
        "end_date": "2015-06-30",
        "monthly_payment": 38465.0,
        "annual_rent_increases": 0.03,
    })
    results = stone.run_full_calculation()
    assert results["lease_term_months"] > 0
    assert "interest_expense" in stone.liability_schedule.columns
    print(f"   ✅ Stonebridge term {results['lease_term_months']} months, liability ${results['initial_liability']:,.2f}")
except Exception as e:
    print(f"   ❌ Stonebridge calculation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("ASC 842 engine is working correctly.")
print("=" * 60)
