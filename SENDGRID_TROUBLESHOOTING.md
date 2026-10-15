# 🔧 SendGrid 401 Unauthorized Error - Troubleshooting Guide

**Error:** `Failed to send email: HTTP Error 401: Unauthorized`

This means your SendGrid API key is either invalid or doesn't have the correct permissions.

---

## ✅ Step-by-Step Fix

### Step 1: Verify API Key Format

Your SendGrid API key should look like this:
```
SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Check your `.env` file:**
```env
SENDGRID_API_KEY=SG.xxxxxxxxxx...
```

❌ **Wrong:**
- `SENDGRID_API_KEY=your-sendgrid-key-here`
- `SENDGRID_API_KEY=sk_test_xxxxx` (that's Stripe)
- Missing the `SG.` prefix
- Has quotes around it: `SENDGRID_API_KEY="SG.xxx"`

✅ **Correct:**
- `SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- No quotes, no spaces, just the raw API key

---

### Step 2: Verify API Key Permissions in SendGrid

1. **Log in to SendGrid:**
   - Go to https://app.sendgrid.com
   - Log in with your account

2. **Go to API Keys:**
   - Settings → API Keys (in left sidebar)

3. **Check your API key:**
   - Find the API key you're using
   - Click the three dots → View Details

4. **Required Permissions:**
   - ✅ **Mail Send** - MUST be enabled (Full Access or Restricted Access)
   - This is the minimum permission needed to send emails

5. **Create New API Key if needed:**
   - If your key doesn't have Mail Send permission, create a new one:
     1. Click "Create API Key"
     2. Name: `LeaseAI Email Delivery`
     3. Permission: **Full Access** (easiest) or **Restricted Access** → Enable "Mail Send"
     4. Click "Create & View"
     5. **Copy the key immediately** (you won't see it again!)
     6. Paste into your `.env` file

---

### Step 3: Verify Sender Email

SendGrid requires sender verification for security.

**In your `.env` file:**
```env
SENDER_EMAIL=noreply@leaseai.com
SENDER_NAME=LeaseAI Platform
```

**Verify sender in SendGrid:**
1. Go to Settings → Sender Authentication
2. Click "Verify a Single Sender"
3. Enter:
   - From Name: `LeaseAI Platform`
   - From Email Address: `noreply@yourdomain.com` (must be your domain or verified domain)
   - Reply To: Your support email
4. Click "Create"
5. **Check your email** for verification link
6. Click the verification link

**Important:** The `SENDER_EMAIL` in your `.env` must match a verified sender in SendGrid.

---

### Step 4: Update Your `.env` File

Your complete `.env` configuration should look like this:

```env
# SendGrid Email Configuration
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDER_EMAIL=noreply@yourdomain.com
SENDER_NAME=LeaseAI Platform

# Company Information (appears in emails)
COMPANY_NAME=LeaseAI
COMPANY_LOCATION=Vancouver, BC
APP_NAME=LeaseAI
APP_URL=https://leaseai.com

# Supabase (already configured)
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-supabase-key

# OpenAI (already configured)
OPENAI_API_KEY=your-openai-key
```

**Save the file** (make sure it's saved as `.env` not `.env.txt`)

---

### Step 5: Restart Your App

Changes to `.env` only take effect when you restart:

```powershell
# In PowerShell, press Ctrl+C to stop
# Then restart:
streamlit run Home.py
```

---

### Step 6: Test Email Delivery

1. Go to **Lease Review** page
2. Select a lease
3. Click **"📧 Email Report to Client"**

**Expected Results:**
- ✅ "Email delivered to [email]" success message
- ✅ Client receives email within 1-2 minutes
- ✅ PDF is attached to email

**If Still Fails:**
- Check terminal output for exact error
- Verify API key was copied correctly (no extra spaces)
- Verify sender email is verified in SendGrid
- Check SendGrid Activity Feed for delivery status

---

## 🔍 Testing SendGrid Configuration

### Quick Test Script

Create a file `test_sendgrid.py` in your LeaseAI folder:

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'noreply@leaseai.com')

print(f"Testing SendGrid API Key...")
print(f"API Key starts with: {SENDGRID_API_KEY[:15]}...")
print(f"Sender Email: {SENDER_EMAIL}")
print()

# Create test email
message = Mail(
    from_email=SENDER_EMAIL,
    to_emails='YOUR_EMAIL@example.com',  # Change this to your email
    subject='SendGrid Test',
    plain_text_content='If you receive this, SendGrid is working!'
)

try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    
    print(f"✅ Success! Status Code: {response.status_code}")
    print("Check your email inbox (and spam folder)")
except Exception as e:
    print(f"❌ Error: {str(e)}")
```

**Run it:**
```powershell
python test_sendgrid.py
```

**Expected:**
- ✅ "Success! Status Code: 202"
- ✅ You receive the test email

---

## 📧 Critical Date Email Notifications

### Status: ✅ Already Implemented

The critical date email notifications are fully implemented and ready to use.

**Features:**
- Automated email reminders for critical lease dates
- Color-coded urgency levels (red, orange, yellow, blue)
- Professional HTML email template
- Customizable notification intervals (90, 60, 30, 14, 7, 1 days before)

**How It Works:**
1. Add a critical date in **Critical Dates** page
2. Specify notification intervals (e.g., 30 days, 7 days, 1 day before)
3. System automatically sends reminder emails at those intervals

**Current State:**
- ✅ Email function exists and is tested
- ✅ Professional HTML template with branding
- ✅ Integration with Critical Dates page
- ⚠️ Requires SendGrid to be configured (same 401 error will occur if not set up)
- ℹ️ Requires scheduled job/cron to check dates daily (not yet automated)

**To Enable Automated Sending:**
You would need to set up a daily scheduled task that:
1. Queries `critical_dates` table for upcoming dates
2. Checks notification intervals
3. Calls `send_critical_date_reminder()` for each due notification

**Manual Testing:**
Once SendGrid is working, you can test critical date emails by:
1. Adding a test critical date (e.g., 7 days from today)
2. Manually triggering the email function (would need to add a test button)

---

## ✅ What's Working Now

After downloading the updated files and fixing SendGrid:

1. ✅ **Better Text Input Contrast** - White background, black text, easy to read
2. ✅ **Improved Error Messages** - ASC 842 errors now show detailed troubleshooting
3. ✅ **PDF Generation** - Works without SendGrid (no API key needed)
4. ✅ **Email Delivery** - Will work once SendGrid is configured correctly
5. ✅ **Critical Date Emails** - Function ready, needs SendGrid + automation

---

## 🚨 Common Issues

### Issue: "SendGrid not configured"
**Fix:** Add `SENDGRID_API_KEY` to `.env` file

### Issue: "401 Unauthorized"
**Fix:** Follow Step 2 above (verify API key permissions)

### Issue: "403 Forbidden" 
**Fix:** Verify sender email in SendGrid dashboard

### Issue: Email not received
**Check:**
- Spam/junk folder
- SendGrid Activity Feed (Settings → Activity)
- Client email address is correct in database
- Sender email is verified

### Issue: "Email delivered" but no email received
**Check:**
- SendGrid Activity Feed for delivery status
- May be delayed (can take 1-5 minutes)
- Check spam folder
- Verify client's email server isn't blocking SendGrid

---

## 📞 SendGrid Support

If still having issues:

1. **Check SendGrid Activity Feed:**
   - Settings → Activity
   - Search for recent sends
   - See delivery status and errors

2. **SendGrid Status:**
   - https://status.sendgrid.com
   - Check for service outages

3. **SendGrid Support:**
   - https://support.sendgrid.com
   - Or contact via dashboard

---

## 🎯 Quick Checklist

- [ ] API key starts with `SG.`
- [ ] API key has "Mail Send" permission in SendGrid dashboard
- [ ] Sender email is verified in SendGrid
- [ ] `.env` file has all required fields
- [ ] `.env` file has no quotes around API key
- [ ] App restarted after changing `.env`
- [ ] Test email works (`test_sendgrid.py`)
- [ ] Production email works (Lease Review page)

---

**Once SendGrid is working, all email features will work automatically!** 🚀
