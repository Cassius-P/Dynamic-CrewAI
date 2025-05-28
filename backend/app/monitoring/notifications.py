"""
Notification system for sending alerts through various channels.
"""
import asyncio
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import httpx
import structlog
from app.config import settings

logger = structlog.get_logger()

class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"

@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    email_smtp_host: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from_address: Optional[str] = None
    email_to_addresses: Optional[List[str]] = field(default_factory=list)
    
    webhook_url: Optional[str] = None
    webhook_headers: Optional[Dict[str, str]] = field(default_factory=dict)
    
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    
    sms_provider: Optional[str] = None  # "twilio", "aws_sns", etc.
    sms_credentials: Optional[Dict[str, str]] = field(default_factory=dict)
    sms_phone_numbers: Optional[List[str]] = field(default_factory=list)

class NotificationManager:
    """Manages sending notifications through various channels."""
    
    def __init__(self):
        self.config = self._load_notification_config()
    
    def _load_notification_config(self) -> NotificationConfig:
        """Load notification configuration from settings."""
        return NotificationConfig(
            email_smtp_host=getattr(settings, 'email_smtp_host', None),
            email_smtp_port=getattr(settings, 'email_smtp_port', 587),
            email_username=getattr(settings, 'email_username', None),
            email_password=getattr(settings, 'email_password', None),
            email_from_address=getattr(settings, 'email_from_address', None),
            email_to_addresses=getattr(settings, 'email_to_addresses', []),
            
            webhook_url=getattr(settings, 'webhook_url', None),
            webhook_headers=getattr(settings, 'webhook_headers', {}),
            
            slack_webhook_url=getattr(settings, 'slack_webhook_url', None),
            slack_channel=getattr(settings, 'slack_channel', '#alerts'),
            
            sms_provider=getattr(settings, 'sms_provider', None),
            sms_credentials=getattr(settings, 'sms_credentials', {}),
            sms_phone_numbers=getattr(settings, 'sms_phone_numbers', [])
        )
    
    async def send_alert_notification(self, channel: NotificationChannel, rule, alert):
        """Send alert notification through specified channel."""
        try:
            if channel == NotificationChannel.EMAIL:
                await self._send_email_alert(rule, alert)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_alert(rule, alert)
            elif channel == NotificationChannel.SLACK:
                await self._send_slack_alert(rule, alert)
            elif channel == NotificationChannel.SMS:
                await self._send_sms_alert(rule, alert)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                
        except Exception as e:
            logger.error(
                "Error sending alert notification",
                channel=channel.value,
                rule=rule.name,
                error=str(e)
            )
            raise
    
    async def send_resolution_notification(self, channel: NotificationChannel, rule, alert):
        """Send alert resolution notification through specified channel."""
        try:
            if channel == NotificationChannel.EMAIL:
                await self._send_email_resolution(rule, alert)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_resolution(rule, alert)
            elif channel == NotificationChannel.SLACK:
                await self._send_slack_resolution(rule, alert)
            elif channel == NotificationChannel.SMS:
                await self._send_sms_resolution(rule, alert)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                
        except Exception as e:
            logger.error(
                "Error sending resolution notification",
                channel=channel.value,
                rule=rule.name,
                error=str(e)
            )
            raise
    
    async def _send_email_alert(self, rule, alert):
        """Send alert notification via email."""
        if not self._is_email_configured():
            logger.warning("Email notifications not configured")
            return
        
        subject = f"🚨 {rule.severity.value.upper()} Alert: {rule.component}"
        
        # Create email content
        body = self._generate_email_alert_body(rule, alert)
        
        await self._send_email(subject, body, is_html=True)
        logger.info("Email alert sent", rule=rule.name)
    
    async def _send_email_resolution(self, rule, alert):
        """Send alert resolution notification via email."""
        if not self._is_email_configured():
            logger.warning("Email notifications not configured")
            return
        
        subject = f"✅ RESOLVED: {rule.component} Alert"
        
        # Create email content
        body = self._generate_email_resolution_body(rule, alert)
        
        await self._send_email(subject, body, is_html=True)
        logger.info("Email resolution sent", rule=rule.name)
    
    def _generate_email_alert_body(self, rule, alert) -> str:
        """Generate HTML email body for alert."""
        severity_color = {
            "critical": "#dc3545",
            "warning": "#ffc107", 
            "info": "#17a2b8"
        }.get(rule.severity.value, "#6c757d")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: {severity_color}; color: white; padding: 15px; border-radius: 5px;">
                <h2>🚨 {rule.severity.value.upper()} Alert Triggered</h2>
            </div>
            
            <div style="padding: 20px;">
                <h3>Alert Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Component:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{rule.component}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Rule:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{rule.name}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Severity:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{rule.severity.value}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Message:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.message}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Current Value:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.current_value}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Threshold:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.threshold_value}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Triggered At:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.triggered_at.isoformat()}</td>
                    </tr>
                </table>
                
                <h4>Recommended Actions</h4>
                <ul>
                    {self._get_recommended_actions(rule, alert)}
                </ul>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 20px;">
                <small>This alert was generated by the CrewAI Backend Monitoring System</small>
            </div>
        </body>
        </html>
        """
    
    def _generate_email_resolution_body(self, rule, alert) -> str:
        """Generate HTML email body for alert resolution."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #28a745; color: white; padding: 15px; border-radius: 5px;">
                <h2>✅ Alert Resolved</h2>
            </div>
            
            <div style="padding: 20px;">
                <h3>Resolution Details</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Component:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{rule.component}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Rule:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{rule.name}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Original Alert:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.message}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Resolved At:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.last_triggered.isoformat()}</td>
                    </tr>
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">Duration:</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{alert.last_triggered - alert.triggered_at}</td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 20px;">
                <small>This resolution was generated by the CrewAI Backend Monitoring System</small>
            </div>
        </body>
        </html>
        """
    
    def _get_recommended_actions(self, rule, alert) -> str:
        """Get recommended actions based on alert type."""
        actions_map = {
            "database_connection_failure": [
                "Check database server status",
                "Verify connection credentials",
                "Check network connectivity",
                "Review database logs"
            ],
            "redis_connection_failure": [
                "Check Redis server status",
                "Verify Redis configuration",
                "Check available memory",
                "Review Redis logs"
            ],
            "celery_no_workers": [
                "Start Celery workers",
                "Check worker health",
                "Review worker logs",
                "Verify queue configuration"
            ],
            "api_response_time_high": [
                "Check system resources",
                "Review slow queries",
                "Analyze traffic patterns",
                "Consider scaling up"
            ]
        }
        
        actions = actions_map.get(rule.name, ["Check system health", "Review logs", "Contact system administrator"])
        return "".join([f"<li>{action}</li>" for action in actions])
    
    async def _send_webhook_alert(self, rule, alert):
        """Send alert notification via webhook."""
        if not self.config.webhook_url:
            logger.warning("Webhook URL not configured")
            return
        
        payload = {
            "type": "alert",
            "severity": rule.severity.value,
            "component": rule.component,
            "rule_name": rule.name,
            "message": alert.message,
            "current_value": alert.current_value,
            "threshold_value": alert.threshold_value,
            "triggered_at": alert.triggered_at.isoformat(),
            "metadata": {
                "trigger_count": alert.trigger_count,
                "rule_metadata": rule.metadata
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CrewAI-Backend-Monitor/1.0"
        }
        headers.update(self.config.webhook_headers or {})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.webhook_url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
        
        logger.info("Webhook alert sent", rule=rule.name, status_code=response.status_code)
    
    async def _send_webhook_resolution(self, rule, alert):
        """Send alert resolution via webhook."""
        if not self.config.webhook_url:
            logger.warning("Webhook URL not configured")
            return
        
        payload = {
            "type": "resolution",
            "component": rule.component,
            "rule_name": rule.name,
            "message": alert.message,
            "resolved_at": alert.last_triggered.isoformat(),
            "duration_seconds": (alert.last_triggered - alert.triggered_at).total_seconds(),
            "metadata": alert.metadata
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CrewAI-Backend-Monitor/1.0"
        }
        headers.update(self.config.webhook_headers or {})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.webhook_url,
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
        
        logger.info("Webhook resolution sent", rule=rule.name, status_code=response.status_code)
    
    async def _send_slack_alert(self, rule, alert):
        """Send alert notification to Slack."""
        if not self.config.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        color_map = {
            "critical": "danger",
            "warning": "warning", 
            "info": "good"
        }
        
        payload = {
            "channel": self.config.slack_channel,
            "username": "CrewAI Monitor",
            "icon_emoji": "🚨",
            "attachments": [
                {
                    "color": color_map.get(rule.severity.value, "danger"),
                    "title": f"{rule.severity.value.upper()} Alert: {rule.component}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Component",
                            "value": rule.component,
                            "short": True
                        },
                        {
                            "title": "Rule",
                            "value": rule.name,
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.current_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold_value),
                            "short": True
                        }
                    ],
                    "ts": alert.triggered_at.timestamp()
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
        
        logger.info("Slack alert sent", rule=rule.name)
    
    async def _send_slack_resolution(self, rule, alert):
        """Send alert resolution to Slack."""
        if not self.config.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        duration = alert.last_triggered - alert.triggered_at
        
        payload = {
            "channel": self.config.slack_channel,
            "username": "CrewAI Monitor",
            "icon_emoji": "✅",
            "attachments": [
                {
                    "color": "good",
                    "title": f"✅ RESOLVED: {rule.component}",
                    "text": f"Alert '{rule.name}' has been resolved",
                    "fields": [
                        {
                            "title": "Component",
                            "value": rule.component,
                            "short": True
                        },
                        {
                            "title": "Duration",
                            "value": str(duration),
                            "short": True
                        }
                    ],
                    "ts": alert.last_triggered.timestamp()
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
        
        logger.info("Slack resolution sent", rule=rule.name)
    
    async def _send_sms_alert(self, rule, alert):
        """Send alert notification via SMS."""
        if not self.config.sms_provider or not self.config.sms_phone_numbers:
            logger.warning("SMS notifications not configured")
            return
        
        message = f"ALERT [{rule.severity.value.upper()}]: {rule.component} - {alert.message}"
        
        if self.config.sms_provider == "twilio":
            await self._send_twilio_sms(message)
        elif self.config.sms_provider == "aws_sns":
            await self._send_aws_sns_sms(message)
        else:
            logger.warning(f"Unsupported SMS provider: {self.config.sms_provider}")
    
    async def _send_sms_resolution(self, rule, alert):
        """Send alert resolution via SMS."""
        if not self.config.sms_provider or not self.config.sms_phone_numbers:
            logger.warning("SMS notifications not configured")
            return
        
        message = f"RESOLVED: {rule.component} alert '{rule.name}' has been resolved"
        
        if self.config.sms_provider == "twilio":
            await self._send_twilio_sms(message)
        elif self.config.sms_provider == "aws_sns":
            await self._send_aws_sns_sms(message)
    
    async def _send_twilio_sms(self, message: str):
        """Send SMS via Twilio."""
        # Placeholder for Twilio SMS implementation
        logger.info("Twilio SMS would be sent", message=message[:50])
    
    async def _send_aws_sns_sms(self, message: str):
        """Send SMS via AWS SNS."""
        # Placeholder for AWS SNS SMS implementation
        logger.info("AWS SNS SMS would be sent", message=message[:50])
    
    async def _send_email(self, subject: str, body: str, is_html: bool = False):
        """Send email using SMTP."""
        if not self._is_email_configured():
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.config.email_from_address or ""
        msg['To'] = ", ".join(self.config.email_to_addresses or [])
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        
        # Send email
        def send_email_sync():
            try:
                # Validate all required email configuration
                if not all([
                    self.config.email_smtp_host,
                    self.config.email_username,
                    self.config.email_password,
                    self.config.email_from_address,
                    self.config.email_to_addresses
                ]):
                    logger.error("Email configuration incomplete")
                    return False
                
                # Type assertions for mypy - we've already validated these are not None
                smtp_host = str(self.config.email_smtp_host)
                username = str(self.config.email_username)
                password = str(self.config.email_password)
                from_address = str(self.config.email_from_address)
                to_addresses = self.config.email_to_addresses or []
                
                server = smtplib.SMTP(smtp_host, self.config.email_smtp_port)
                server.starttls()
                server.login(username, password)
                text = msg.as_string()
                server.sendmail(from_address, to_addresses, text)
                server.quit()
                return True
            except Exception as e:
                logger.error("Error sending email", error=str(e))
                return False
        
        # Run synchronous email sending in thread pool
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, send_email_sync)
        
        if success:
            logger.info("Email sent successfully")
        else:
            logger.error("Failed to send email")
    
    def _is_email_configured(self) -> bool:
        """Check if email configuration is complete."""
        return all([
            self.config.email_smtp_host,
            self.config.email_username,
            self.config.email_password,
            self.config.email_from_address,
            self.config.email_to_addresses
        ])
    
    async def test_notification_channel(self, channel: NotificationChannel) -> bool:
        """Test if notification channel is working."""
        try:
            if channel == NotificationChannel.EMAIL:
                return self._is_email_configured()
            elif channel == NotificationChannel.WEBHOOK:
                return bool(self.config.webhook_url)
            elif channel == NotificationChannel.SLACK:
                return bool(self.config.slack_webhook_url)
            elif channel == NotificationChannel.SMS:
                return bool(self.config.sms_provider and self.config.sms_phone_numbers)
            return False
        except Exception as e:
            logger.error(f"Error testing {channel} notification", error=str(e))
            return False 