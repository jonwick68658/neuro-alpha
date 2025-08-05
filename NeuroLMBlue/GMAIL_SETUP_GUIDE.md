# Gmail Setup Guide for NeuroLM Password Reset

## Issue with Outlook
Your `reset@neurolm.app` account has SMTP authentication disabled at the tenant level. This is a common security setting for business domains.

## Solution: Gmail Backup (5-minute setup)

### Step 1: Create Gmail Account
1. Go to https://accounts.google.com/signup
2. Create: `neurolm.reset@gmail.com` (or similar)
3. Complete account setup

### Step 2: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Click "2-Step Verification"
3. Follow setup process (use your phone number)
4. Complete verification

### Step 3: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select app: "Mail"
3. Select device: "Other (Custom name)"
4. Enter: "NeuroLM Password Reset"
5. Click "Generate"
6. **COPY THE 16-CHARACTER PASSWORD** (you can't see it again!)

### Step 4: Add to Secrets Vault
Add these two secrets to your Replit secrets vault:

```
GMAIL_USER=neurolm.reset@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password
```

### Step 5: Test
Run: `python password_reset_test.py`

## Why Gmail Works Better
- No tenant restrictions
- App passwords work reliably
- Free and unlimited for reasonable usage
- More reliable than business email servers

## Current Status
- ✅ Discord instant notifications: WORKING
- ⚠️ Outlook email: Blocked by tenant settings
- 🔄 Gmail email: Ready to set up (5 minutes)

Your system is already operational with Discord. Gmail just adds email backup!