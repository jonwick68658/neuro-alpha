"""
Free Notification Service
Alternative to SendGrid and Twilio using free email services and webhooks
"""

import smtplib
import requests
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

def send_gmail_email(to_email: str, verification_code: str, reset_token: str) -> bool:
    """Send password reset email using Gmail SMTP (free with Gmail account)"""
    try:
        # Gmail SMTP configuration
        gmail_user = os.getenv('GMAIL_USER')  # Your Gmail address
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')  # Gmail app password
        
        if not gmail_user or not gmail_password:
            print("Gmail credentials not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = "NeuroLM Password Reset"
        
        # HTML content
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Password Reset Request</h2>
                <p>You requested a password reset for your NeuroLM account.</p>
                <p>Your verification code is:</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <strong style="font-size: 24px; color: #007bff;">{verification_code}</strong>
                </div>
                <p>Enter this code on the password reset page to continue.</p>
                <p>This code will expire in 30 minutes.</p>
                <p>If you didn't request this reset, please ignore this email.</p>
                <hr style="border: 1px solid #eee; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">NeuroLM - Advanced AI Memory System</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Error sending Gmail email: {e}")
        return False

def send_outlook_email(to_email: str, verification_code: str, reset_token: str) -> bool:
    """Send password reset email using Outlook SMTP (free with Outlook account)"""
    try:
        # Outlook SMTP configuration
        outlook_user = os.getenv('OUTLOOK_USER')  # Your Outlook address
        outlook_password = os.getenv('OUTLOOK_PASSWORD')  # Outlook password
        
        if not outlook_user or not outlook_password:
            print("Outlook credentials not configured. Set OUTLOOK_USER and OUTLOOK_PASSWORD")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = outlook_user
        msg['To'] = to_email
        msg['Subject'] = "NeuroLM Password Reset"
        
        # HTML content
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Password Reset Request</h2>
                <p>You requested a password reset for your NeuroLM account.</p>
                <p>Your verification code is:</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <strong style="font-size: 24px; color: #007bff;">{verification_code}</strong>
                </div>
                <p>Enter this code on the password reset page to continue.</p>
                <p>This code will expire in 30 minutes.</p>
                <p>If you didn't request this reset, please ignore this email.</p>
                <hr style="border: 1px solid #eee; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">NeuroLM - Advanced AI Memory System</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        server = smtplib.SMTP('smtp-mail.outlook.com', 587)
        server.starttls()
        server.login(outlook_user, outlook_password)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Error sending Outlook email: {e}")
        return False

def send_discord_webhook_notification(webhook_url: str, message: str) -> bool:
    """Send notification via Discord webhook (free alternative to SMS)"""
    try:
        if not webhook_url:
            print("Discord webhook URL not configured")
            return False
        
        data = {
            "content": f"**NeuroLM Password Reset**\n\n{message}"
        }
        
        response = requests.post(webhook_url, json=data)
        return response.status_code == 204
        
    except Exception as e:
        print(f"Error sending Discord webhook: {e}")
        return False

def send_slack_webhook_notification(webhook_url: str, message: str) -> bool:
    """Send notification via Slack webhook (free alternative to SMS)"""
    try:
        if not webhook_url:
            print("Slack webhook URL not configured")
            return False
        
        data = {
            "text": f"*NeuroLM Password Reset*\n\n{message}"
        }
        
        response = requests.post(webhook_url, json=data)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending Slack webhook: {e}")
        return False

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """Send message via Telegram bot (free alternative to SMS)"""
    try:
        if not bot_token or not chat_id:
            print("Telegram bot token or chat ID not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": f"🔐 *NeuroLM Password Reset*\n\n{message}",
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data)
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def send_free_email_notification(to_email: str, verification_code: str, reset_token: str) -> bool:
    """Try multiple free email services in order"""
    
    # Try Gmail first
    if send_gmail_email(to_email, verification_code, reset_token):
        return True
    
    # Try Outlook as backup
    if send_outlook_email(to_email, verification_code, reset_token):
        return True
    
    return False

def send_free_instant_notification(verification_code: str, user_info: str = "user") -> bool:
    """Try multiple free instant notification services"""
    
    message = f"Your NeuroLM password reset code: {verification_code}\n\nThis code expires in 30 minutes."
    
    # Try Discord webhook
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook and send_discord_webhook_notification(discord_webhook, message):
        return True
    
    # Try Slack webhook
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    if slack_webhook and send_slack_webhook_notification(slack_webhook, message):
        return True
    
    # Try Telegram bot
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat = os.getenv('TELEGRAM_CHAT_ID')
    if telegram_token and telegram_chat and send_telegram_message(telegram_token, telegram_chat, message):
        return True
    
    return False