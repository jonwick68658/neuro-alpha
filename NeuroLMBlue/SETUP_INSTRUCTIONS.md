# Setup Instructions for reset@neurolm.app

## 1. Outlook SMTP Setup (Already Done)

You've already set up `reset@neurolm.app` with Outlook. Here's what you need:

```bash
# Add these to your environment variables
OUTLOOK_USER=reset@neurolm.app
OUTLOOK_PASSWORD=your-outlook-password
```

## 2. Gmail Setup (Optional but Recommended for Backup)

### Step 1: Create Gmail Account
1. Go to https://accounts.google.com/signup
2. Create account: `neurolm.reset@gmail.com` (or similar)
3. Complete account setup

### Step 2: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Click "2-Step Verification"
3. Follow setup process (use your phone)

### Step 3: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select app: "Mail"
3. Select device: "Other" → type "NeuroLM Reset"
4. Click "Generate"
5. Copy the 16-character password (save it!)

### Step 4: Set Environment Variables
```bash
GMAIL_USER=neurolm.reset@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password
```

## 3. Discord Server Setup (For Instant Notifications)

### Step 1: Create Discord Server
1. Open Discord (desktop app or web)
2. Click "+" to add server
3. Choose "Create My Own"
4. Name it "NeuroLM Notifications"
5. Make it private

### Step 2: Create Webhook
1. Right-click your server name
2. Select "Server Settings"
3. Go to "Integrations"
4. Click "Webhooks"
5. Click "Create Webhook"
6. Name it "Password Reset"
7. Choose #general channel (or create #notifications)
8. Click "Copy Webhook URL"

### Step 3: Set Environment Variable
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE
```

## 4. Test Your Setup

Run the test script:
```bash
python test_notifications.py
```

This will verify all your services are working correctly.

## 5. Recommended Configuration

For best results, set up:
- **Primary Email**: Outlook SMTP (reset@neurolm.app)
- **Backup Email**: Gmail SMTP (neurolm.reset@gmail.com)
- **Instant Notifications**: Discord webhook

This gives you triple redundancy - if one service fails, others will work.

## Security Notes

- Use strong, unique passwords for all accounts
- Enable 2FA where possible
- Keep app passwords secure
- Discord webhook is private to your server only