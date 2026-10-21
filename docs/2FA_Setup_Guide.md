# LeaseAI - Two-Factor Authentication (2FA) Setup Guide
**Version:** 1.0  
**Last Updated:** October 2026  
**Audience:** All users (required for admins)

---

## 1. OVERVIEW

### 1.1 What is Two-Factor Authentication (2FA)?
Two-Factor Authentication (also called Multi-Factor Authentication or MFA) adds an extra layer of security to your account by requiring two forms of verification:
1. **Something you know:** Your password
2. **Something you have:** Your phone or authenticator app

Even if someone steals your password, they cannot access your account without your second factor.

### 1.2 Why is 2FA Required?
- **Protects sensitive data:** LeaseAI handles confidential lease information
- **Prevents unauthorized access:** Even if passwords are compromised
- **Compliance requirement:** Required for SOC 2 certification
- **Industry best practice:** Standard for enterprise SaaS applications

### 1.3 Who Must Use 2FA?
- **Required:** All admin users
- **Strongly recommended:** All users
- **Enforcement date:** December 1, 2026

---

## 2. SUPPORTED 2FA METHODS

LeaseAI supports the following 2FA methods (via Supabase Auth):

| Method | Security Level | Convenience | Cost | Recommended For |
|--------|----------------|-------------|------|-----------------|
| **Authenticator App** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Free | Everyone |
| **SMS Text Message** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Free | Backup only |

**We recommend using an authenticator app** as your primary 2FA method because:
- More secure than SMS (not vulnerable to SIM swapping)
- Works offline (no cell service required)
- Free and easy to use

---

## 3. SETTING UP 2FA WITH AUTHENTICATOR APP

### Step 1: Install an Authenticator App

Choose one of these trusted authenticator apps:

**iOS:**
- **Authy** (recommended) - Supports cloud backup
- **Google Authenticator** - Simple and reliable
- **Microsoft Authenticator** - Good for Office 365 users
- **1Password** (paid) - All-in-one password + 2FA manager

**Android:**
- **Authy** (recommended)
- **Google Authenticator**
- **Microsoft Authenticator**
- **andOTP** (open-source)

**Desktop:**
- **Authy** (Windows, Mac, Linux)
- **1Password** (cross-platform)

### Step 2: Enable 2FA in LeaseAI

1. **Log in to LeaseAI**
   - Go to https://leaseai.streamlit.app (or your deployment URL)
   - Sign in with your email and password

2. **Navigate to Account Settings**
   - Click your profile icon in the top right
   - Select **"Account Settings"** or **"Security"**

3. **Enable Two-Factor Authentication**
   - Click **"Enable 2FA"** or **"Set up authenticator app"**
   - You'll see a QR code on your screen

4. **Scan QR Code with Authenticator App**
   - Open your authenticator app
   - Tap **"Add Account"** or **"+"**
   - Scan the QR code displayed on LeaseAI
   - The app will add a new entry: **"LeaseAI (your-email@example.com)"**

5. **Enter Verification Code**
   - Your authenticator app will display a 6-digit code
   - Enter this code in the LeaseAI verification field
   - Click **"Verify and Enable"**

6. **Save Backup Codes**
   - LeaseAI will display **backup recovery codes**
   - **CRITICAL:** Save these codes in a safe place (password manager, printed copy in safe)
   - You'll need these if you lose access to your authenticator app
   - Click **"I've saved my backup codes"** to continue

7. **Success!**
   - 2FA is now enabled on your account
   - You'll be prompted for a code every time you log in

### Step 3: Test Your 2FA Setup

1. **Log out** of LeaseAI
2. **Log back in** with your email and password
3. **Enter the 6-digit code** from your authenticator app
4. **Verify successful login**

---

## 4. LOGGING IN WITH 2FA

### Normal Login Process

1. Go to LeaseAI login page
2. Enter your **email** and **password**
3. Click **"Sign In"**
4. You'll be prompted: **"Enter your 2FA code"**
5. Open your **authenticator app**
6. Find the **LeaseAI** entry
7. Enter the **6-digit code** (you have 30 seconds before it refreshes)
8. Click **"Verify"**
9. You're logged in!

### Tips
- Codes refresh every 30 seconds
- If a code expires while you're entering it, wait for the next one
- Codes are time-based, so make sure your phone's clock is accurate

---

## 5. RECOVERING ACCESS (LOST PHONE / LOST AUTHENTICATOR)

### Option 1: Use Backup Recovery Codes

If you saved your backup codes:

1. Go to LeaseAI login page
2. Enter your email and password
3. When prompted for 2FA code, click **"Use backup code"**
4. Enter one of your backup recovery codes
5. **Important:** Each backup code can only be used once
6. After logging in, **set up 2FA again** on your new device
7. **Generate new backup codes**

### Option 2: Contact Support

If you lost your backup codes:

1. Email: **support@leaseai.com**
2. Subject: **"2FA Recovery Request - [Your Email]"**
3. Include:
   - Your full name
   - Your email address
   - Your company name
   - Reason for request (lost phone, etc.)
   - **Identity verification:** Answer security questions or provide verification documents

4. **Security Review:**
   - Support will verify your identity (may take 24-48 hours)
   - We may require:
     - Government-issued ID
     - Verification from your company admin
     - Video call verification

5. **2FA Reset:**
   - Once verified, support will temporarily disable 2FA on your account
   - You'll receive an email with a **temporary login link**
   - **Immediately re-enable 2FA** after logging in

**Note:** This process is intentionally strict to protect your account.

---

## 6. TRANSFERRING 2FA TO A NEW PHONE

### Option A: Transfer Before Losing Access (Recommended)

#### For Authy Users:
1. Install Authy on your new phone
2. Log in with your phone number
3. Your accounts automatically sync (if you enabled cloud backup)
4. Done! ✅

#### For Google Authenticator Users:
Google Authenticator now supports account transfer:

1. On **old phone**, open Google Authenticator
2. Tap **"⋮"** (three dots) → **"Transfer accounts"** → **"Export accounts"**
3. Select the accounts you want to transfer
4. A QR code appears on your old phone
5. On **new phone**, install Google Authenticator
6. Tap **"⋮"** → **"Transfer accounts"** → **"Import accounts"**
7. Scan the QR code from your old phone
8. Done! ✅

### Option B: Transfer After Losing Access

If you already lost your old phone:

1. Use a **backup recovery code** to log in
2. **Disable 2FA** in Account Settings
3. **Re-enable 2FA** on your new phone (follow Step 2 above)
4. **Save new backup codes**

---

## 7. DISABLING 2FA (NOT RECOMMENDED)

**⚠️ Warning:** Disabling 2FA makes your account significantly less secure.

**Only disable 2FA if:**
- You're switching to a different 2FA method
- You're transferring to a new device
- **You're an admin:** You cannot disable 2FA (company policy)

**To disable 2FA:**

1. Log in to LeaseAI (using your current 2FA method)
2. Go to **Account Settings** → **Security**
3. Click **"Disable Two-Factor Authentication"**
4. Enter your **password** to confirm
5. Enter a **2FA code** from your authenticator app
6. Click **"Disable"**
7. You'll receive a **confirmation email**

---

## 8. ADMIN ENFORCEMENT POLICY

### 8.1 Requirements for Admins

All users with **Admin** role must:
- ✅ Enable 2FA within 7 days of account creation
- ✅ Use an authenticator app (SMS not sufficient for admins)
- ✅ Save backup codes in a secure location
- ✅ Cannot disable 2FA without approval from Founder/CTO

### 8.2 Enforcement Timeline

| Date | Action |
|------|--------|
| **October 21, 2026** | 2FA available for all users |
| **November 1, 2026** | Admins receive email: "Enable 2FA by Dec 1" |
| **November 15, 2026** | Reminder emails sent |
| **December 1, 2026** | **2FA required for all admins** |
| | Admins without 2FA: account locked until enabled |

### 8.3 Recommended for All Users

Starting **January 1, 2027**, 2FA will be **required for all users** (not just admins).

**Non-admin users:** Please enable 2FA now to avoid login disruptions in January.

---

## 9. SECURITY BEST PRACTICES

### ✅ DO:
- Enable 2FA on all accounts (not just LeaseAI)
- Use an authenticator app (more secure than SMS)
- Save backup codes in a password manager or secure location
- Set up 2FA on multiple devices (e.g., phone + tablet)
- Use Authy with cloud backup for easy device transfers

### ❌ DON'T:
- Share your 2FA codes with anyone (including support)
- Screenshot QR codes and store them insecurely
- Rely solely on SMS-based 2FA (vulnerable to SIM swapping)
- Lose your backup codes (write them down!)
- Use the same password across multiple accounts

---

## 10. TROUBLESHOOTING

### Problem: "Invalid code" error

**Possible causes:**
1. **Time sync issue:** Your phone's clock is off
   - **Fix:** Go to phone settings → Date & Time → Enable "Automatic time"
   
2. **Code expired:** You took too long to enter it
   - **Fix:** Wait for the next code (refreshes every 30 seconds)

3. **Wrong account:** You entered a code from a different app
   - **Fix:** Make sure you're using the LeaseAI entry in your authenticator

### Problem: "2FA setup failed"

**Fix:**
1. Try a different browser
2. Clear browser cache and cookies
3. Try scanning the QR code with a different authenticator app
4. If still failing, contact support@leaseai.com

### Problem: Authenticator app shows "Invalid QR code"

**Fix:**
1. Try entering the setup key manually instead:
   - In your authenticator app, tap "Enter a setup key" instead of scanning
   - Enter the code displayed under the QR code in LeaseAI
   - Make sure to select "Time-based" (not "Counter-based")

### Problem: Lost phone AND lost backup codes

**Solution:**
- Contact support@leaseai.com with identity verification
- See Section 5: "Option 2: Contact Support"
- **This will take 24-48 hours for security verification**

---

## 11. FREQUENTLY ASKED QUESTIONS (FAQ)

**Q: Why can't I use SMS for 2FA?**  
A: SMS is less secure because of SIM swapping attacks. Authenticator apps are more secure and work offline.

**Q: What if I don't have a smartphone?**  
A: You can use desktop authenticator apps like Authy for Windows/Mac or browser extensions.

**Q: Can I use the same authenticator app for multiple accounts?**  
A: Yes! One authenticator app (like Google Authenticator or Authy) can hold codes for dozens of accounts.

**Q: How long do backup codes last?**  
A: Backup codes never expire, but each can only be used once. Generate new codes after using one.

**Q: Will I need to enter 2FA every time I log in?**  
A: On trusted devices, you can check "Trust this device" to avoid entering a code for 30 days.

**Q: Can I exempt certain users from 2FA?**  
A: No. All admins must use 2FA (no exceptions). All other users will be required starting Jan 2027.

**Q: What if I switch phones frequently?**  
A: Use Authy with cloud backup — your codes sync across devices automatically.

---

## 12. SUPPORT CONTACTS

**For 2FA setup help:**  
Email: support@leaseai.com  
Subject: "2FA Setup Assistance"

**For 2FA recovery (lost phone):**  
Email: support@leaseai.com  
Subject: "2FA Recovery Request - [Your Email]"  
Include: Full name, company, reason for request

**For urgent access issues:**  
Phone: [Support Hotline]  
Available: Monday-Friday, 9 AM - 5 PM EST

---

**Security Note:** LeaseAI support will NEVER ask for your password or 2FA codes. If someone claiming to be from LeaseAI asks for this information, it's a phishing attempt — report it immediately to security@leaseai.com.

---

**Document Owner:** Security Team  
**Last Updated:** October 2026  
**Next Review:** January 2027
