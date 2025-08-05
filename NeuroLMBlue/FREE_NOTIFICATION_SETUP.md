# Free Notification Services Setup Guide

This guide explains how to set up free alternatives to SendGrid and Twilio for password reset notifications.

## Email Services (Free)

### Option 1: Gmail SMTP (Recommended)
1. Create a Gmail account if you don't have one
2. Enable 2-factor authentication
3. Generate an App Password:
   - Go to Google Account settings
   - Security → App passwords
   - Generate password for "Mail"
4. Set environment variables:
   ```bash
   GMAIL_USER=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-app-password
   ```

### Option 2: Outlook SMTP
1. Create an Outlook account
2. Set environment variables:
   ```bash
   OUTLOOK_USER=your-email@outlook.com
   OUTLOOK_PASSWORD=your-password
   ```

## Instant Notification Services (Free)

### Option 1: Discord Webhook (Recommended)
1. Create a Discord server or use existing one
2. Create a webhook:
   - Server Settings → Integrations → Webhooks
   - Create New Webhook
   - Copy webhook URL
3. Set environment variable:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
   ```

### Option 2: Slack Webhook
1. Create a Slack workspace
2. Create an incoming webhook:
   - Apps → Incoming Webhooks
   - Add to Slack
   - Choose channel and get webhook URL
3. Set environment variable:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your-webhook-url
   ```

### Option 3: Telegram Bot
1. Create a Telegram bot:
   - Message @BotFather on Telegram
   - Create new bot with `/newbot`
   - Get bot token
2. Get your chat ID:
   - Message your bot
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find your chat ID in the response
3. Set environment variables:
   ```bash
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_CHAT_ID=your-chat-id
   ```

## How It Works

### Email Verification
- User selects "Email Verification (Free)"
- System tries Gmail SMTP first, then Outlook as backup
- Verification code sent to user's registered email

### Instant Notification
- User selects "Instant Notification (Free)"
- System tries Discord webhook, then Slack, then Telegram
- Verification code sent to configured service instantly

## Configuration Priority

The system tries services in this order:

**Email:**
1. Gmail SMTP
2. Outlook SMTP

**Instant:**
1. Discord Webhook
2. Slack Webhook
3. Telegram Bot

## Testing

To test the services:

1. Set up at least one email service (Gmail recommended)
2. Set up at least one instant service (Discord recommended)
3. Visit `/forgot-password` on your NeuroLM instance
4. Try both verification methods

## Troubleshooting

### Gmail Issues
- Make sure 2FA is enabled
- Use App Password, not regular password
- Check "Less secure app access" if needed

### Discord Issues
- Make sure webhook URL is correct
- Test webhook with curl: `curl -X POST -H "Content-Type: application/json" -d '{"content":"test"}' YOUR_WEBHOOK_URL`

### Telegram Issues
- Make sure bot token is correct
- Get chat ID by messaging bot first
- Check bot permissions

## Security Notes

- All services use HTTPS/TLS encryption
- Verification codes expire in 30 minutes
- Tokens are single-use only
- No sensitive data stored in external services