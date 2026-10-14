"""
Debug Critical Date Notifications
Shows why notifications were or weren't sent.
"""
from supabase import create_client
import config
from datetime import datetime, timedelta

def debug_notifications():
    """Check critical dates and show notification logic."""
    print("=" * 60)
    print("Critical Date Notification Debug")
    print("=" * 60)
    
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    today = datetime.now().date()
    print(f"\n📅 Today: {today.strftime('%B %d, %Y')}")
    
    # Fetch all active critical dates
    response = supabase.table("critical_dates").select(
        "*, leases(id, property_address, tenant_name, client_id, clients(email, company_name))"
    ).eq("is_active", True).execute()
    
    dates = response.data if response.data else []
    
    print(f"\n🔍 Found {len(dates)} active critical date(s)\n")
    
    if not dates:
        print("❌ No active critical dates found!")
        print("   Add a critical date first, then run this script.")
        return
    
    for idx, date_record in enumerate(dates, 1):
        print(f"{'='*60}")
        print(f"Critical Date #{idx}")
        print(f"{'='*60}")
        
        date_value = datetime.strptime(date_record["date_value"], "%Y-%m-%d").date()
        days_until = (date_value - today).days
        
        lease = date_record.get("leases", {})
        client = lease.get("clients", {})
        
        print(f"📋 Property: {lease.get('property_address', 'N/A')}")
        print(f"📅 Date Type: {date_record['date_type']}")
        print(f"📆 Date: {date_value.strftime('%B %d, %Y')}")
        print(f"⏰ Days Until: {days_until} days")
        print(f"📧 Client Email: {client.get('email', 'N/A')}")
        print(f"🔔 Notification Intervals: {date_record.get('notification_intervals', [])}")
        print(f"✅ Notifications Already Sent: {date_record.get('notifications_sent', [])}")
        
        print(f"\n🤔 Notification Logic:")
        
        notification_intervals = date_record.get("notification_intervals", [])
        notifications_sent = date_record.get("notifications_sent", [])
        
        if days_until in notification_intervals:
            if days_until in notifications_sent:
                print(f"   ⏭️  {days_until} days: Already sent (skipped)")
            else:
                if client.get('email'):
                    print(f"   ✅ {days_until} days: SHOULD SEND EMAIL NOW")
                else:
                    print(f"   ❌ {days_until} days: No client email available")
        else:
            print(f"   ⚠️  {days_until} days: Not a notification interval")
            
            # Show next notification opportunity
            future_intervals = [i for i in notification_intervals if i < days_until and i not in notifications_sent]
            if future_intervals:
                next_interval = max(future_intervals)
                days_to_wait = days_until - next_interval
                next_date = today + timedelta(days=days_to_wait)
                print(f"   📅 Next notification: In {days_to_wait} day(s) on {next_date.strftime('%B %d, %Y')} ({next_interval} days before)")
            else:
                print(f"   📭 No more notifications scheduled")
        
        print()
    
    print("=" * 60)
    print("\n💡 Tips:")
    print("   - Notifications only send when days_until exactly matches an interval")
    print("   - To test now, add a date exactly 30 days from today")
    print("   - Or wait until the date reaches one of your intervals")
    print()

if __name__ == "__main__":
    debug_notifications()
