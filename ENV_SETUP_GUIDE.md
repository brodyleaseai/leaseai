# Environment Setup Guide

## Quick Start: Setting Up Your .env File

### 1. The `.env` file has been created for you at the project root

### 2. Replace the placeholder values with your actual API keys:

#### 🔹 Supabase (Required)
Get your keys from: https://supabase.com/dashboard/project/_/settings/api

```env
SUPABASE_URL=https://nttwaqptwfwchedsqqem.supabase.co
SUPABASE_KEY=eyJhbGc...your-actual-anon-key
SUPABASE_SERVICE_KEY=eyJhbGc...your-actual-service-key
```

#### 🔹 OpenAI (Required for extraction)
Get your key from: https://platform.openai.com/api-keys

```env
OPENAI_API_KEY=sk-proj-...your-actual-openai-key
```

#### 🔹 SendGrid (Optional - for email notifications)
Get your key from: https://app.sendgrid.com/settings/api_keys

```env
SENDGRID_API_KEY=SG...your-actual-sendgrid-key
SENDGRID_FROM_EMAIL=your-email@domain.com
```

#### 🔹 Stripe (Optional - for payments)
Get your keys from: https://dashboard.stripe.com/test/apikeys

```env
STRIPE_SECRET_KEY=sk_test_...your-actual-stripe-secret
STRIPE_PUBLISHABLE_KEY=pk_test_...your-actual-stripe-publishable
STRIPE_WEBHOOK_SECRET=whsec_...your-actual-webhook-secret
```

#### 🔹 AWS (Optional - for high-quality OCR)
Get from AWS Console or leave empty to use free Tesseract OCR

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...your-actual-aws-key
AWS_SECRET_ACCESS_KEY=...your-actual-aws-secret
```

### 3. Save the `.env` file

### 4. Test it works:
```bash
python -c "import config; print('Config loaded:', config.OPENAI_API_KEY[:10] + '...')"
```

---

## 🔒 Security Notes

✅ **`.env` is in `.gitignore`** - Won't be committed to git  
✅ **`config.py` only has placeholders** - Safe to commit  
✅ **Never share `.env` file** - Contains sensitive credentials  
✅ **Use environment variables in production** - Not `.env` files  

---

## 📁 File Structure

```
leaseai/
├── .env                    ← Your secrets (not in git)
├── .gitignore              ← Contains .env
├── config.py               ← Loads .env automatically
├── extraction_pipeline.py  ← Uses config for API keys
└── requirements.txt        ← Includes python-dotenv
```

---

## 🚀 How It Works

1. **`python-dotenv`** automatically loads `.env` when you import `config.py`
2. **`config.py`** reads environment variables using `os.getenv()`
3. **Your application** uses `config.OPENAI_API_KEY` etc.
4. **Falls back to placeholders** if `.env` doesn't exist

---

## ✨ You're all set!

Just replace the placeholders in `.env` with your actual keys and you're ready to go!
