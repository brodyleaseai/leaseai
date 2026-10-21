"""
Test script for Phase 5 audit logging functionality
Run this after setting up the database schema to verify everything works
"""

import sys
from datetime import datetime

def test_audit_logging():
    """Test audit logging functionality"""
    
    print("\n" + "="*70)
    print("🔒 Phase 5 Audit Logging Test")
    print("="*70 + "\n")
    
    # Import required modules
    try:
        from audit_logger import AuditLogger, log_lease_upload, log_data_export
        print("✅ Successfully imported audit_logger module")
    except ImportError as e:
        print(f"❌ Failed to import audit_logger: {e}")
        return False
    
    try:
        from supabase import create_client
        print("✅ Successfully imported supabase client")
    except ImportError as e:
        print(f"❌ Failed to import supabase: {e}")
        print("   Install with: pip install supabase")
        return False
    
    # Load config
    try:
        from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
        print("✅ Successfully loaded config")
    except ImportError:
        try:
            import streamlit as st
            SUPABASE_URL = st.secrets["SUPABASE_URL"]
            SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
            print("✅ Successfully loaded Streamlit secrets")
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            print("   Add SUPABASE_URL and SUPABASE_SERVICE_KEY to config.py or Streamlit secrets")
            return False
    
    # Create Supabase client
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Successfully created Supabase client")
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {e}")
        return False
    
    # Test 1: Create audit logger
    try:
        logger = AuditLogger(sb)
        print("✅ Successfully created AuditLogger instance")
    except Exception as e:
        print(f"❌ Failed to create AuditLogger: {e}")
        return False
    
    # Test 2: Log a test action
    print("\n📝 Testing basic audit log entry...")
    try:
        audit_id = logger.log_action(
            user_id="test-user-123",
            user_email="test@leaseai.com",
            user_role="tester",
            action_type="TEST_ACTION",
            action_category="DATA",
            action_description="Phase 5 test audit log entry",
            resource_type="test",
            resource_id="test-resource-123",
            new_values={"test": True, "timestamp": datetime.now().isoformat()},
            metadata={"phase": 5, "test_run": True}
        )
        
        if audit_id:
            print(f"✅ Audit log created successfully! ID: {audit_id}")
        else:
            print("⚠️  Audit log created but no ID returned")
    except Exception as e:
        print(f"❌ Failed to create audit log: {e}")
        return False
    
    # Test 3: Retrieve recent audit logs
    print("\n📊 Testing audit log retrieval...")
    try:
        recent_logs = logger.get_recent_audit_logs(limit=5)
        print(f"✅ Retrieved {len(recent_logs)} recent audit logs")
        
        if recent_logs:
            latest = recent_logs[0]
            print(f"   Latest log: {latest.get('action_type')} by {latest.get('user_email')}")
    except Exception as e:
        print(f"❌ Failed to retrieve audit logs: {e}")
        return False
    
    # Test 4: Log a security event
    print("\n🚨 Testing security event logging...")
    try:
        event_id = logger.log_security_event(
            event_type="TEST_SECURITY_EVENT",
            severity="LOW",
            description="Phase 5 test security event",
            user_email="test@leaseai.com",
            ip_address="127.0.0.1",
            details={"test": True, "phase": 5}
        )
        
        if event_id:
            print(f"✅ Security event logged successfully! ID: {event_id}")
        else:
            print("⚠️  Security event logged but no ID returned")
    except Exception as e:
        print(f"❌ Failed to log security event: {e}")
        return False
    
    # Test 5: Retrieve security events
    print("\n📋 Testing security event retrieval...")
    try:
        security_events = logger.get_security_events(limit=5)
        print(f"✅ Retrieved {len(security_events)} security events")
        
        if security_events:
            latest = security_events[0]
            print(f"   Latest event: [{latest.get('severity')}] {latest.get('event_type')}")
    except Exception as e:
        print(f"❌ Failed to retrieve security events: {e}")
        return False
    
    # Test 6: Test convenience functions
    print("\n🎯 Testing convenience functions...")
    try:
        log_lease_upload(
            supabase_client=sb,
            user_id="test-user-456",
            user_email="tester@leaseai.com",
            lease_id="test-lease-789",
            filename="test_lease.pdf",
            pages=10,
            property_address="123 Test Street"
        )
        print("✅ log_lease_upload() works correctly")
    except Exception as e:
        print(f"❌ log_lease_upload() failed: {e}")
        return False
    
    try:
        log_data_export(
            supabase_client=sb,
            user_id="test-user-456",
            user_email="tester@leaseai.com",
            export_type="CSV",
            lease_count=5,
            filename="test_export.csv"
        )
        print("✅ log_data_export() works correctly")
    except Exception as e:
        print(f"❌ log_data_export() failed: {e}")
        return False
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70 + "\n")
    
    print("Phase 5 audit logging is working correctly! 🎉")
    print("\nNext steps:")
    print("1. View audit logs in the Security Dashboard (🔒 Security Dashboard page)")
    print("2. Integrate audit logging into your application workflows")
    print("3. Review docs/PHASE_5_README.md for usage examples")
    
    return True


if __name__ == "__main__":
    success = test_audit_logging()
    sys.exit(0 if success else 1)
