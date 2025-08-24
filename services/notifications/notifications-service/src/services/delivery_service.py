import json
import smtplib
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.exceptions import NotFound, BadRequest

from models.channel import ChannelConfig, NotificationChannel, ChannelType, ChannelStatus
from models.notification import Notification, NotificationChannel as NotifChannel

class DeliveryService:
    """Service for delivering notifications through various channels"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
        
        # Initialize channel configurations
        self.channel_configs = self._load_channel_configurations()
    
    def deliver_notification(self, notification: Notification) -> Dict[str, Any]:
        """Deliver a notification through all configured channels"""
        
        results = {
            'notification_id': notification.id,
            'channels': {},
            'overall_success': False
        }
        
        successful_channels = 0
        
        for channel in notification.channels:
            try:
                # Get channel configuration
                config = self._get_channel_config(channel)
                if not config or not config.is_enabled:
                    results['channels'][channel.value] = {
                        'success': False,
                        'error': 'Channel not configured or disabled'
                    }
                    continue
                
                # Check rate limits
                if self._is_rate_limited(config):
                    results['channels'][channel.value] = {
                        'success': False,
                        'error': 'Rate limit exceeded'
                    }
                    continue
                
                # Deliver through specific channel
                delivery_result = self._deliver_through_channel(notification, channel, config)
                results['channels'][channel.value] = delivery_result
                
                if delivery_result['success']:
                    successful_channels += 1
                    notification.mark_as_sent(channel)
                else:
                    notification.mark_as_failed(channel, delivery_result.get('error', 'Unknown error'))
                
                # Update channel statistics
                config.update_statistics(
                    sent=1,
                    delivered=1 if delivery_result['success'] else 0,
                    failed=0 if delivery_result['success'] else 1
                )
                
            except Exception as e:
                results['channels'][channel.value] = {
                    'success': False,
                    'error': str(e)
                }
                notification.mark_as_failed(channel, str(e))
        
        results['overall_success'] = successful_channels > 0
        
        # Publish delivery event
        self.event_producer.publish('notification.delivery_attempted', {
            'notification_id': notification.id,
            'channels': list(results['channels'].keys()),
            'successful_channels': successful_channels,
            'overall_success': results['overall_success'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return results
    
    def _deliver_through_channel(self, notification: Notification, 
                               channel: NotifChannel, config: ChannelConfig) -> Dict[str, Any]:
        """Deliver notification through a specific channel"""
        
        if channel == NotifChannel.EMAIL:
            return self._deliver_email(notification, config)
        elif channel == NotifChannel.SMS:
            return self._deliver_sms(notification, config)
        elif channel == NotifChannel.PUSH:
            return self._deliver_push(notification, config)
        elif channel == NotifChannel.IN_APP:
            return self._deliver_in_app(notification, config)
        elif channel == NotifChannel.WEBHOOK:
            return self._deliver_webhook(notification, config)
        else:
            return {
                'success': False,
                'error': f'Unsupported channel: {channel.value}'
            }
    
    def _deliver_email(self, notification: Notification, config: ChannelConfig) -> Dict[str, Any]:
        """Deliver notification via email"""
        
        try:
            # Get recipient email
            recipient_email = notification.recipient_email or self._get_user_email(notification.recipient_id)
            if not recipient_email:
                return {
                    'success': False,
                    'error': 'No email address found for recipient'
                }
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification.title
            msg['From'] = config.provider_config.get('from_email', 'noreply@freightflow.com')
            msg['To'] = recipient_email
            
            # Add text content
            text_part = MIMEText(notification.content, 'plain')
            msg.attach(text_part)
            
            # Add HTML content if available
            if notification.html_content:
                html_part = MIMEText(notification.html_content, 'html')
                msg.attach(html_part)
            
            # Send email based on provider
            if config.provider == 'smtp':
                return self._send_smtp_email(msg, config)
            elif config.provider == 'sendgrid':
                return self._send_sendgrid_email(notification, recipient_email, config)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported email provider: {config.provider}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_smtp_email(self, msg: MIMEMultipart, config: ChannelConfig) -> Dict[str, Any]:
        """Send email via SMTP"""
        
        try:
            smtp_config = config.provider_config
            
            # Connect to SMTP server
            server = smtplib.SMTP(smtp_config.get('host', 'localhost'), smtp_config.get('port', 587))
            
            if smtp_config.get('use_tls', True):
                server.starttls()
            
            if smtp_config.get('username') and smtp_config.get('password'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            return {
                'success': True,
                'message_id': msg['Message-ID'],
                'provider': 'smtp'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_sendgrid_email(self, notification: Notification, recipient_email: str, 
                           config: ChannelConfig) -> Dict[str, Any]:
        """Send email via SendGrid API"""
        
        try:
            api_key = config.provider_config.get('api_key')
            if not api_key:
                return {
                    'success': False,
                    'error': 'SendGrid API key not configured'
                }
            
            # Prepare SendGrid payload
            payload = {
                'personalizations': [{
                    'to': [{'email': recipient_email}],
                    'subject': notification.title
                }],
                'from': {
                    'email': config.provider_config.get('from_email', 'noreply@freightflow.com'),
                    'name': config.provider_config.get('from_name', 'FreightFlow')
                },
                'content': [
                    {
                        'type': 'text/plain',
                        'value': notification.content
                    }
                ]
            }
            
            # Add HTML content if available
            if notification.html_content:
                payload['content'].append({
                    'type': 'text/html',
                    'value': notification.html_content
                })
            
            # Send via SendGrid API
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.sendgrid.com/v3/mail/send',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 202:
                return {
                    'success': True,
                    'message_id': response.headers.get('X-Message-Id'),
                    'provider': 'sendgrid'
                }
            else:
                return {
                    'success': False,
                    'error': f'SendGrid API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _deliver_sms(self, notification: Notification, config: ChannelConfig) -> Dict[str, Any]:
        """Deliver notification via SMS"""
        
        try:
            # Get recipient phone number
            recipient_phone = notification.recipient_phone or self._get_user_phone(notification.recipient_id)
            if not recipient_phone:
                return {
                    'success': False,
                    'error': 'No phone number found for recipient'
                }
            
            # Send SMS based on provider
            if config.provider == 'twilio':
                return self._send_twilio_sms(notification, recipient_phone, config)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported SMS provider: {config.provider}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_twilio_sms(self, notification: Notification, recipient_phone: str, 
                        config: ChannelConfig) -> Dict[str, Any]:
        """Send SMS via Twilio API"""
        
        try:
            account_sid = config.provider_config.get('account_sid')
            auth_token = config.provider_config.get('auth_token')
            from_phone = config.provider_config.get('from_phone')
            
            if not all([account_sid, auth_token, from_phone]):
                return {
                    'success': False,
                    'error': 'Twilio credentials not properly configured'
                }
            
            # Prepare Twilio payload
            payload = {
                'From': from_phone,
                'To': recipient_phone,
                'Body': f"{notification.title}\n\n{notification.content}"
            }
            
            # Send via Twilio API
            import base64
            credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = requests.post(
                f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json',
                data=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'success': True,
                    'message_id': result.get('sid'),
                    'provider': 'twilio'
                }
            else:
                return {
                    'success': False,
                    'error': f'Twilio API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _deliver_push(self, notification: Notification, config: ChannelConfig) -> Dict[str, Any]:
        """Deliver push notification"""
        
        try:
            # Get user's push tokens
            push_tokens = self._get_user_push_tokens(notification.recipient_id)
            if not push_tokens:
                return {
                    'success': False,
                    'error': 'No push tokens found for recipient'
                }
            
            # Send push notification based on provider
            if config.provider == 'firebase':
                return self._send_firebase_push(notification, push_tokens, config)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported push provider: {config.provider}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_firebase_push(self, notification: Notification, push_tokens: List[str], 
                          config: ChannelConfig) -> Dict[str, Any]:
        """Send push notification via Firebase"""
        
        try:
            server_key = config.provider_config.get('server_key')
            if not server_key:
                return {
                    'success': False,
                    'error': 'Firebase server key not configured'
                }
            
            # Prepare Firebase payload
            payload = {
                'registration_ids': push_tokens,
                'notification': {
                    'title': notification.title,
                    'body': notification.content[:100] + '...' if len(notification.content) > 100 else notification.content
                },
                'data': {
                    'notification_id': notification.id,
                    'type': notification.notification_type.value,
                    'metadata': notification.metadata
                }
            }
            
            # Send via Firebase API
            headers = {
                'Authorization': f'key={server_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': result.get('success', 0) > 0,
                    'message_id': result.get('multicast_id'),
                    'provider': 'firebase',
                    'details': result
                }
            else:
                return {
                    'success': False,
                    'error': f'Firebase API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _deliver_in_app(self, notification: Notification, config: ChannelConfig) -> Dict[str, Any]:
        """Deliver in-app notification"""
        
        try:
            # For in-app notifications, we just store them in the database
            # The frontend will poll or use websockets to get them
            
            # Save in-app notification
            self._save_in_app_notification(notification)
            
            # Optionally send via websocket if user is online
            self._send_websocket_notification(notification)
            
            return {
                'success': True,
                'message_id': notification.id,
                'provider': 'in_app'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _deliver_webhook(self, notification: Notification, config: ChannelConfig) -> Dict[str, Any]:
        """Deliver notification via webhook"""
        
        try:
            webhook_url = config.provider_config.get('webhook_url')
            if not webhook_url:
                return {
                    'success': False,
                    'error': 'Webhook URL not configured'
                }
            
            # Prepare webhook payload
            payload = {
                'notification_id': notification.id,
                'recipient_id': notification.recipient_id,
                'type': notification.notification_type.value,
                'title': notification.title,
                'content': notification.content,
                'priority': notification.priority.value,
                'metadata': notification.metadata,
                'timestamp': notification.created_at.isoformat()
            }
            
            # Send webhook
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'FreightFlow-Notifications/1.0'
            }
            
            # Add authentication if configured
            if config.provider_config.get('auth_header'):
                headers['Authorization'] = config.provider_config['auth_header']
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if 200 <= response.status_code < 300:
                return {
                    'success': True,
                    'message_id': notification.id,
                    'provider': 'webhook',
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'error': f'Webhook error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_delivery_status(self, notification_id: str) -> Dict[str, Any]:
        """Get delivery status for a notification"""
        
        # Get delivery attempts from database
        delivery_attempts = self._get_delivery_attempts(notification_id)
        
        return {
            'notification_id': notification_id,
            'delivery_attempts': delivery_attempts,
            'summary': self._summarize_delivery_status(delivery_attempts)
        }
    
    def get_delivery_analytics(self, date_from: Optional[str] = None,
                             date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get delivery analytics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_delivery_analytics_data(start_date, end_date)
        
        return {
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            },
            'overall_metrics': {
                'total_deliveries': analytics.get('total_deliveries', 0),
                'successful_deliveries': analytics.get('successful_deliveries', 0),
                'failed_deliveries': analytics.get('failed_deliveries', 0),
                'delivery_rate': analytics.get('delivery_rate', 0),
                'average_delivery_time': analytics.get('avg_delivery_time', 0)
            },
            'by_channel': analytics.get('by_channel', {}),
            'by_provider': analytics.get('by_provider', {}),
            'failure_reasons': analytics.get('failure_reasons', {}),
            'daily_stats': analytics.get('daily_stats', []),
            'channel_health': analytics.get('channel_health', {})
        }
    
    def get_channel_configurations(self) -> List[ChannelConfig]:
        """Get all channel configurations"""
        return list(self.channel_configs.values())
    
    def update_channel_configuration(self, channel_type: str, config: Dict[str, Any],
                                   updated_by: str) -> ChannelConfig:
        """Update channel configuration"""
        
        # Parse channel type
        try:
            parsed_channel_type = ChannelType(channel_type.upper())
        except ValueError:
            raise BadRequest(f"Invalid channel type: {channel_type}")
        
        # Get existing configuration
        channel_config = self.channel_configs.get(parsed_channel_type)
        if not channel_config:
            raise NotFound("Channel configuration not found")
        
        # Update configuration
        updatable_fields = [
            'name', 'description', 'provider', 'provider_config', 'is_enabled',
            'is_default', 'priority', 'rate_limit_per_minute', 'rate_limit_per_hour',
            'rate_limit_per_day', 'max_retries', 'retry_delay_seconds',
            'exponential_backoff', 'health_check_interval_minutes'
        ]
        
        for field in updatable_fields:
            if field in config:
                setattr(channel_config, field, config[field])
        
        channel_config.updated_at = datetime.utcnow()
        
        # Save configuration
        self._save_channel_configuration(channel_config)
        
        # Update in-memory cache
        self.channel_configs[parsed_channel_type] = channel_config
        
        # Publish configuration updated event
        self.event_producer.publish('channel.configuration_updated', {
            'channel_type': channel_type,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return channel_config
    
    def send_test_notification(self, recipient_id: str, channel: str,
                             message: str = "This is a test notification") -> Dict[str, Any]:
        """Send a test notification"""
        
        # Parse channel
        try:
            parsed_channel = NotifChannel(channel.upper())
        except ValueError:
            raise BadRequest(f"Invalid channel: {channel}")
        
        # Create test notification
        test_notification = Notification(
            recipient_id=recipient_id,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Test Notification",
            content=message,
            channels=[parsed_channel],
            priority=NotificationPriority.NORMAL,
            metadata={'test': True}
        )
        
        # Deliver test notification
        result = self.deliver_notification(test_notification)
        
        return result
    
    # Helper methods
    def _get_channel_config(self, channel: NotifChannel) -> Optional[ChannelConfig]:
        """Get channel configuration"""
        channel_type_map = {
            NotifChannel.EMAIL: ChannelType.EMAIL,
            NotifChannel.SMS: ChannelType.SMS,
            NotifChannel.PUSH: ChannelType.PUSH,
            NotifChannel.IN_APP: ChannelType.IN_APP,
            NotifChannel.WEBHOOK: ChannelType.WEBHOOK
        }
        
        channel_type = channel_type_map.get(channel)
        return self.channel_configs.get(channel_type) if channel_type else None
    
    def _is_rate_limited(self, config: ChannelConfig) -> bool:
        """Check if channel is rate limited"""
        # Mock implementation - in real system, check current usage
        return False
    
    def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user's email address"""
        # Mock implementation
        return f"user{user_id}@example.com"
    
    def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Get user's phone number"""
        # Mock implementation
        return "+1234567890"
    
    def _get_user_push_tokens(self, user_id: str) -> List[str]:
        """Get user's push notification tokens"""
        # Mock implementation
        return ["sample_push_token_123"]
    
    def _save_in_app_notification(self, notification: Notification):
        """Save in-app notification to database"""
        # Mock implementation
        pass
    
    def _send_websocket_notification(self, notification: Notification):
        """Send notification via websocket if user is online"""
        # Mock implementation
        pass
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _load_channel_configurations(self) -> Dict[ChannelType, ChannelConfig]:
        """Load channel configurations from database"""
        # Mock implementation - return default configurations
        configs = {}
        
        # Email configuration
        configs[ChannelType.EMAIL] = ChannelConfig(
            channel_type=ChannelType.EMAIL,
            name="Email Notifications",
            provider="sendgrid",
            provider_config={
                "api_key": "your_sendgrid_api_key",
                "from_email": "noreply@freightflow.com",
                "from_name": "FreightFlow"
            },
            is_enabled=True,
            is_default=True,
            priority=1
        )
        
        # SMS configuration
        configs[ChannelType.SMS] = ChannelConfig(
            channel_type=ChannelType.SMS,
            name="SMS Notifications",
            provider="twilio",
            provider_config={
                "account_sid": "your_twilio_account_sid",
                "auth_token": "your_twilio_auth_token",
                "from_phone": "+1234567890"
            },
            is_enabled=False,
            priority=2
        )
        
        # Push notification configuration
        configs[ChannelType.PUSH] = ChannelConfig(
            channel_type=ChannelType.PUSH,
            name="Push Notifications",
            provider="firebase",
            provider_config={
                "server_key": "your_firebase_server_key"
            },
            is_enabled=True,
            priority=3
        )
        
        # In-app notification configuration
        configs[ChannelType.IN_APP] = ChannelConfig(
            channel_type=ChannelType.IN_APP,
            name="In-App Notifications",
            provider="internal",
            provider_config={},
            is_enabled=True,
            priority=4
        )
        
        return configs
    
    def _save_channel_configuration(self, config: ChannelConfig):
        """Save channel configuration to database"""
        # Mock implementation
        pass
    
    def _get_delivery_attempts(self, notification_id: str) -> List[Dict]:
        """Get delivery attempts for a notification"""
        # Mock implementation
        return [
            {
                'id': 'attempt-1',
                'channel': 'EMAIL',
                'status': 'DELIVERED',
                'sent_at': '2024-08-24T10:30:00Z',
                'delivered_at': '2024-08-24T10:30:15Z'
            }
        ]
    
    def _summarize_delivery_status(self, delivery_attempts: List[Dict]) -> Dict:
        """Summarize delivery status"""
        total_attempts = len(delivery_attempts)
        successful_attempts = len([a for a in delivery_attempts if a['status'] == 'DELIVERED'])
        
        return {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'success_rate': (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0,
            'overall_status': 'DELIVERED' if successful_attempts > 0 else 'FAILED'
        }
    
    def _get_delivery_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get delivery analytics data from database"""
        # Mock implementation
        return {
            'total_deliveries': 2500,
            'successful_deliveries': 2425,
            'failed_deliveries': 75,
            'delivery_rate': 97.0,
            'avg_delivery_time': 3.2,
            'by_channel': {
                'EMAIL': {'total': 1500, 'successful': 1485, 'failed': 15},
                'SMS': {'total': 400, 'successful': 385, 'failed': 15},
                'PUSH': {'total': 350, 'successful': 340, 'failed': 10},
                'IN_APP': {'total': 250, 'successful': 215, 'failed': 35}
            },
            'by_provider': {
                'sendgrid': {'total': 1500, 'successful': 1485, 'failed': 15},
                'twilio': {'total': 400, 'successful': 385, 'failed': 15},
                'firebase': {'total': 350, 'successful': 340, 'failed': 10}
            },
            'failure_reasons': {
                'invalid_recipient': 25,
                'rate_limit_exceeded': 20,
                'provider_error': 15,
                'network_timeout': 10,
                'other': 5
            },
            'daily_stats': [
                {'date': '2024-08-22', 'total': 85, 'successful': 82, 'failed': 3},
                {'date': '2024-08-23', 'total': 92, 'successful': 89, 'failed': 3},
                {'date': '2024-08-24', 'total': 78, 'successful': 76, 'failed': 2}
            ],
            'channel_health': {
                'EMAIL': {'status': 'HEALTHY', 'success_rate': 99.0},
                'SMS': {'status': 'HEALTHY', 'success_rate': 96.3},
                'PUSH': {'status': 'HEALTHY', 'success_rate': 97.1},
                'IN_APP': {'status': 'WARNING', 'success_rate': 86.0}
            }
        }

