"""
Email service for GambleGlee
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class EmailService:
    """Email service for sending various types of emails"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_tls = settings.SMTP_TLS
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

    async def send_verification_email(self, email: str, name: str, token: str) -> bool:
        """Send email verification email"""
        try:
            subject = "Verify your GambleGlee account"
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Verify your GambleGlee account</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c3e50;">Welcome to GambleGlee!</h1>
                    <p>Hi {name},</p>
                    <p>Thank you for signing up for GambleGlee! To complete your registration, please verify your email address by clicking the button below:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}" style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Email Address</a>
                    </div>
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{verification_url}</p>
                    <p>This verification link will expire in 24 hours.</p>
                    <p>If you didn't create an account with GambleGlee, please ignore this email.</p>
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #666;">
                        This email was sent to {email}. If you have any questions, please contact our support team.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Welcome to GambleGlee!

            Hi {name},

            Thank you for signing up for GambleGlee! To complete your registration, please verify your email address by visiting this link:

            {verification_url}

            This verification link will expire in 24 hours.

            If you didn't create an account with GambleGlee, please ignore this email.

            Best regards,
            The GambleGlee Team
            """

            return await self._send_email(email, subject, text_content, html_content)

        except Exception as e:
            logger.error("Failed to send verification email", email=email, error=str(e))
            return False

    async def send_password_reset_email(self, email: str, name: str, token: str) -> bool:
        """Send password reset email"""
        try:
            subject = "Reset your GambleGlee password"
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Reset your GambleGlee password</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c3e50;">Password Reset Request</h1>
                    <p>Hi {name},</p>
                    <p>We received a request to reset your GambleGlee password. Click the button below to reset your password:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
                    </div>
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_url}</p>
                    <p>This reset link will expire in 1 hour.</p>
                    <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #666;">
                        This email was sent to {email}. If you have any questions, please contact our support team.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Password Reset Request

            Hi {name},

            We received a request to reset your GambleGlee password. Click the link below to reset your password:

            {reset_url}

            This reset link will expire in 1 hour.

            If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

            Best regards,
            The GambleGlee Team
            """

            return await self._send_email(email, subject, text_content, html_content)

        except Exception as e:
            logger.error("Failed to send password reset email", email=email, error=str(e))
            return False

    async def send_welcome_email(self, email: str, name: str) -> bool:
        """Send welcome email after successful verification"""
        try:
            subject = "Welcome to GambleGlee!"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Welcome to GambleGlee!</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c3e50;">Welcome to GambleGlee!</h1>
                    <p>Hi {name},</p>
                    <p>Congratulations! Your GambleGlee account has been successfully verified and activated.</p>
                    <p>You can now:</p>
                    <ul>
                        <li>Create and accept bets with friends</li>
                        <li>Stream live trick shots</li>
                        <li>Earn rewards for your activity</li>
                        <li>Connect with other users</li>
                    </ul>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{settings.FRONTEND_URL}" style="background-color: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Get Started</a>
                    </div>
                    <p>If you have any questions, feel free to contact our support team.</p>
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #666;">
                        This email was sent to {email}. You can unsubscribe from marketing emails in your account settings.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Welcome to GambleGlee!

            Hi {name},

            Congratulations! Your GambleGlee account has been successfully verified and activated.

            You can now:
            - Create and accept bets with friends
            - Stream live trick shots
            - Earn rewards for your activity
            - Connect with other users

            Get started at: {settings.FRONTEND_URL}

            If you have any questions, feel free to contact our support team.

            Best regards,
            The GambleGlee Team
            """

            return await self._send_email(email, subject, text_content, html_content)

        except Exception as e:
            logger.error("Failed to send welcome email", email=email, error=str(e))
            return False

    async def send_security_alert_email(self, email: str, name: str, alert_type: str, details: Dict[str, Any]) -> bool:
        """Send security alert email"""
        try:
            subject = f"Security Alert: {alert_type}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Security Alert</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #e74c3c;">Security Alert</h1>
                    <p>Hi {name},</p>
                    <p>We detected unusual activity on your GambleGlee account:</p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <strong>Alert Type:</strong> {alert_type}<br>
                        <strong>Time:</strong> {details.get('timestamp', 'Unknown')}<br>
                        <strong>IP Address:</strong> {details.get('ip_address', 'Unknown')}<br>
                        <strong>Location:</strong> {details.get('location', 'Unknown')}
                    </div>
                    <p>If this was you, you can ignore this email. If you don't recognize this activity, please:</p>
                    <ol>
                        <li>Change your password immediately</li>
                        <li>Review your account activity</li>
                        <li>Contact our support team</li>
                    </ol>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{settings.FRONTEND_URL}/security" style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">Review Security</a>
                    </div>
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                    <p style="font-size: 12px; color: #666;">
                        This email was sent to {email}. If you have any questions, please contact our support team.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
            Security Alert

            Hi {name},

            We detected unusual activity on your GambleGlee account:

            Alert Type: {alert_type}
            Time: {details.get('timestamp', 'Unknown')}
            IP Address: {details.get('ip_address', 'Unknown')}
            Location: {details.get('location', 'Unknown')}

            If this was you, you can ignore this email. If you don't recognize this activity, please:
            1. Change your password immediately
            2. Review your account activity
            3. Contact our support team

            Review your security settings: {settings.FRONTEND_URL}/security

            Best regards,
            The GambleGlee Team
            """

            return await self._send_email(email, subject, text_content, html_content)

        except Exception as e:
            logger.error("Failed to send security alert email", email=email, error=str(e))
            return False

    async def _send_email(self, to_email: str, subject: str, text_content: str, html_content: str) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            if settings.ENVIRONMENT == "development":
                # In development, just log the email
                logger.info("Email sent (development mode)", to=to_email, subject=subject)
                return True
            else:
                # In production, actually send the email
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_tls:
                        server.starttls()
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)

                logger.info("Email sent", to=to_email, subject=subject)
                return True

        except Exception as e:
            logger.error("Failed to send email", to=to_email, subject=subject, error=str(e))
            return False
