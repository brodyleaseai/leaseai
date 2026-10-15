# ⚡ QUICK START - Fix Your LeaseAI App NOW

## 🔴 IMMEDIATE ACTION REQUIRED

### 1️⃣ Fix Database Permissions (2 minutes)

**Open Supabase SQL Editor:**
1. Go to https://app.supabase.com
2. Select your LeaseAI project
3. Click **SQL Editor** in left sidebar
4. Click **+ New query**
5. Copy/paste this:

```sql
-- Grant permissions to amendment tables
GRANT ALL ON public.amendments TO anon, authenticated, service_role;
GRANT ALL ON public.amendment_clauses TO anon, authenticated, service_role;
GRANT ALL ON public.lease_clause_history TO anon, authenticated, service_role;
GRANT ALL ON public.amendment_relationships TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_controlling_clause TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_amendment_chain TO anon, authenticated, service_role;
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
```

6. Click **Run** (green button)
7. ✅ You should see: "Success. No rows returned"

---

### 2️⃣ Download New Files to Your Local Computer

**Your GitHub has 4 new files in the `pages/` folder:**

1. Open: https://github.com/brodyleaseai/leaseai/tree/main/pages
2. Download each file to `C:\Users\brody\OneDrive\Desktop\LeaseAI\pages\`:
   - `4_📊_Admin_Dashboard.py`
   - `5_📈_ASC842_Dashboard.py`
   - `6_📅_Critical_Dates.py`
   - `7_👥_Client_Portal.py`

3. Also download updated `Home.py` to `C:\Users\brody\OneDrive\Desktop\LeaseAI\`
   - https://github.com/brodyleaseai/leaseai/blob/main/Home.py

**Quick Download Method:**
- Click on each file
- Click **Raw** button
- Right-click → **Save As**
- Save to the correct folder
- Make sure to save as `.py` files (not `.txt`)

---

### 3️⃣ Create Admin User in Supabase (2 minutes)

**You need an admin account to log in:**

1. In Supabase, go to **SQL Editor**
2. Run this query:

```sql
-- Create admin_users table if it doesn't exist
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert your admin user
INSERT INTO admin_users (email, password, name)
VALUES ('admin@leaseai.com', 'admin123', 'Admin User')
ON CONFLICT (email) DO NOTHING;
```

3. ✅ Success!

---

### 4️⃣ Restart Your App

**In your Windows terminal:**

1. Press `Ctrl+C` to stop the current app
2. Run: `streamlit run Home.py`
3. App opens in browser

---

### 5️⃣ Test Everything

**You should now see:**

✅ **Login Page** when app starts
- Email: `admin@leaseai.com`
- Password: `admin123`
- Click **Sign In**

✅ **Sidebar has 8 pages:**
1. Home
2. 📤 Upload Lease
3. 📋 Lease Review
4. 🔗 Amendment Graph
5. 📊 Admin Dashboard
6. 📈 ASC842 Dashboard
7. 📅 Critical Dates
8. 👥 Client Portal

✅ **Amendment Graph works:**
- Click on **🔗 Amendment Graph** in sidebar
- No more `permission denied` error
- All 4 tabs load successfully

---

## 🐛 If You Still Get Errors

### Error: `File does not exist: pages/4_📊_Admin_Dashboard.py`
**Fix:** You didn't download the new page files. Go back to step 2️⃣

### Error: `permission denied for table amendments`
**Fix:** You didn't run the SQL script. Go back to step 1️⃣

### Error: `Invalid credentials` when logging in
**Fix:** You didn't create the admin user. Go back to step 3️⃣

### Error: No login page shows up
**Fix:** You didn't download the updated `Home.py`. Go back to step 2️⃣

---

## ✅ Success Checklist

Check off when complete:

- [ ] Ran SQL permissions script in Supabase
- [ ] Downloaded 4 new page files to local `pages/` folder
- [ ] Downloaded updated `Home.py` to local folder
- [ ] Created admin user in Supabase
- [ ] Restarted Streamlit app
- [ ] Successfully logged in
- [ ] See all 8 pages in sidebar
- [ ] Amendment Graph loads without errors
- [ ] Can navigate between all pages

---

## 📞 Need Help?

**Check the full guide:** `FIX_GUIDE.md` (also in your GitHub repo)

**Common Questions:**

**Q: Where do I run the SQL scripts?**
A: Supabase → SQL Editor (left sidebar) → New query → Paste → Run

**Q: How do I download files from GitHub?**
A: Open the file → Click "Raw" → Right-click → Save As → Choose location

**Q: My app won't start**
A: Make sure you're in the right folder: `cd C:\Users\brody\OneDrive\Desktop\LeaseAI`

**Q: I don't see the new pages**
A: Check they're saved in the `pages\` subfolder, not the main folder

---

## 🎉 What You Get After This

✅ Full LeaseAI platform with 8 pages
✅ Authentication system (admin + client roles)
✅ Amendment Resolution Graph™ working
✅ ASC 842 compliance calculations
✅ Critical dates management
✅ Admin dashboard with metrics
✅ Client portal for customer access
✅ No more permission errors

**Time to complete:** ~10 minutes
**Difficulty:** Easy (just copy/paste SQL and download files)

---

## 📸 What It Should Look Like

**Login Screen:**
- Purple gradient header
- Email/password form
- "Demo Credentials" info box

**After Login (Admin):**
- User name in top-right
- Logout button
- 8 pages in sidebar
- 8 quick action buttons
- Platform metrics (total leases, amendments, etc.)

**Amendment Graph Page:**
- 4 tabs: Amendment Chain, Clause History, Query Engine, Upload Amendment
- No errors
- Loads lease dropdown successfully

---

Start with Step 1️⃣ and work your way down. You've got this! 🚀
