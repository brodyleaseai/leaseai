"""
Setup Users for LeaseAI
Create admin and client users in Supabase if they don't exist.
"""
from supabase import create_client
import config

def setup_users():
    """Check and create users if they don't exist."""
    print("=" * 60)
    print("LeaseAI User Setup")
    print("=" * 60)
    
    # Initialize Supabase
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    # Check admin users
    print("\n🔍 Checking admin_users table...")
    try:
        admin_response = supabase.table("admin_users").select("*").execute()
        if admin_response.data:
            print(f"✅ Found {len(admin_response.data)} admin user(s):")
            for admin in admin_response.data:
                print(f"   - {admin.get('email')} (ID: {admin.get('id')})")
        else:
            print("⚠️  No admin users found. Creating default admin...")
            admin_data = {
                "email": "admin@leaseai.com",
                "password": "admin123",
                "name": "System Admin"
            }
            result = supabase.table("admin_users").insert(admin_data).execute()
            print(f"✅ Created admin: admin@leaseai.com / admin123")
    except Exception as e:
        print(f"❌ Error checking admin_users: {e}")
    
    # Check clients
    print("\n🔍 Checking clients table...")
    try:
        client_response = supabase.table("clients").select("*").execute()
        if client_response.data:
            print(f"✅ Found {len(client_response.data)} client(s):")
            for client in client_response.data:
                print(f"   - {client.get('email')} (Company: {client.get('company_name')})")
        else:
            print("⚠️  No clients found. Creating default client...")
            client_data = {
                "email": "brody@kitschco.com",
                "password": "client123",
                "company_name": "KitschCo",
                "contact_name": "Brody",
                "phone": "(604) 555-0123"
            }
            result = supabase.table("clients").insert(client_data).execute()
            print(f"✅ Created client: brody@kitschco.com / client123")
    except Exception as e:
        print(f"❌ Error checking clients: {e}")
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nYou can now login with:")
    print("  Admin: admin@leaseai.com / admin123")
    print("  Client: brody@kitschco.com / client123")
    print("\n")

if __name__ == "__main__":
    setup_users()
