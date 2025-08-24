import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.notification import Notification, NotificationTemplate, NotificationPreference, NotificationStatus, NotificationType, NotificationPriority, NotificationChannel

class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_notification(self, recipient_id: str, notification_type: str,
                          title: str, content: str, channels: List[str] = None,
                          priority: str = "normal", scheduled_at: Optional[str] = None,
                          metadata: Dict[str, Any] = None, created_by: str = "") -> Notification:
        """Create a new notification"""
        
        # Parse notification type
        try:
            parsed_type = NotificationType(notification_type.upper())
        except ValueError:
            raise BadRequest(f"Invalid notification type: {notification_type}")
        
        # Parse priority
        try:
            parsed_priority = NotificationPriority(priority.upper())
        except ValueError:
            raise BadRequest(f"Invalid priority: {priority}")
        
        # Parse channels
        parsed_channels = []
        if channels:
            for channel in channels:
                try:
                    parsed_channels.append(NotificationChannel(channel.upper()))
                except ValueError:
                    raise BadRequest(f"Invalid channel: {channel}")
        else:
            parsed_channels = [NotificationChannel.EMAIL]
        
        # Parse scheduled time
        parsed_scheduled_at = None
        if scheduled_at:
            try:
                parsed_scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            except ValueError:
                raise BadRequest("Invalid scheduled_at format")
        
        # Get user preferences to filter channels
        preferences = self.get_user_preferences(recipient_id)
        if preferences:
            enabled_channels = []
            for channel in parsed_channels:
                if preferences.is_channel_enabled(channel) and preferences.is_type_enabled(parsed_type):
                    enabled_channels.append(channel)
            parsed_channels = enabled_channels or [NotificationChannel.IN_APP]  # Fallback to in-app
        
        # Create notification
        notification = Notification(
            recipient_id=recipient_id,
            notification_type=parsed_type,
            title=title,
            content=content,
            channels=parsed_channels,
            priority=parsed_priority,
            scheduled_at=parsed_scheduled_at,
            metadata=metadata or {},
            created_by=created_by
        )
        
        # Add delivery attempts for each channel
        for channel in parsed_channels:
            notification.add_delivery_attempt(channel)
        
        # Save to database
        self._save_notification(notification)
        
        # Cache the notification
        self.cache.set(f"notification:{notification.id}", notification.to_dict(), ttl=3600)
        
        # Publish notification created event
        self.event_producer.publish('notification.created', {
            'notification_id': notification.id,
            'recipient_id': recipient_id,
            'notification_type': notification_type,
            'title': title,
            'channels': channels,
            'priority': priority,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return notification
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID"""
        
        # Try cache first
        cached = self.cache.get(f"notification:{notification_id}")
        if cached:
            notification_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_notification(notification_data)
        
        # Load from database
        notification = self._load_notification(notification_id)
        if notification:
            # Cache the result
            self.cache.set(f"notification:{notification_id}", notification.to_dict(), ttl=3600)
        
        return notification
    
    def get_notifications(self, recipient_id: str, status: Optional[str] = None,
                         notification_type: Optional[str] = None,
                         page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get notifications for a user"""
        
        # Build query filters
        filters = {'recipient_id': recipient_id}
        if status:
            filters['status'] = status
        if notification_type:
            filters['notification_type'] = notification_type
        
        # Get notifications from database
        notifications_data = self._query_notifications(filters, page, per_page)
        
        notifications = []
        for notification_data in notifications_data['items']:
            notification = self._dict_to_notification(notification_data)
            notifications.append(notification)
        
        return {
            'items': notifications,
            'page': page,
            'per_page': per_page,
            'total': notifications_data['total'],
            'pages': (notifications_data['total'] + per_page - 1) // per_page
        }
    
    def mark_as_read(self, notification_id: str, user_id: str) -> Notification:
        """Mark a notification as read"""
        
        notification = self.get_notification(notification_id)
        if not notification:
            raise NotFound("Notification not found")
        
        if notification.recipient_id != user_id:
            raise BadRequest("Cannot mark notification for another user")
        
        notification.mark_as_read()
        
        # Save to database
        self._save_notification(notification)
        
        # Update cache
        self.cache.set(f"notification:{notification_id}", notification.to_dict(), ttl=3600)
        
        # Publish notification read event
        self.event_producer.publish('notification.read', {
            'notification_id': notification_id,
            'recipient_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return notification
    
    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        
        # Get unread notifications
        unread_notifications = self._query_unread_notifications(user_id)
        
        count = 0
        for notification_data in unread_notifications:
            notification = self._dict_to_notification(notification_data)
            notification.mark_as_read()
            self._save_notification(notification)
            
            # Update cache
            self.cache.set(f"notification:{notification.id}", notification.to_dict(), ttl=3600)
            count += 1
        
        # Publish bulk read event
        if count > 0:
            self.event_producer.publish('notifications.bulk_read', {
                'recipient_id': user_id,
                'count': count,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return count
    
    def delete_notification(self, notification_id: str, user_id: str):
        """Delete a notification"""
        
        notification = self.get_notification(notification_id)
        if not notification:
            raise NotFound("Notification not found")
        
        if notification.recipient_id != user_id:
            raise BadRequest("Cannot delete notification for another user")
        
        # Delete from database
        self._delete_notification(notification_id)
        
        # Remove from cache
        self.cache.delete(f"notification:{notification_id}")
        
        # Publish notification deleted event
        self.event_producer.publish('notification.deleted', {
            'notification_id': notification_id,
            'recipient_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_user_preferences(self, user_id: str) -> Optional[NotificationPreference]:
        """Get user notification preferences"""
        
        # Try cache first
        cached = self.cache.get(f"preferences:{user_id}")
        if cached:
            preferences_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_preferences(preferences_data)
        
        # Load from database
        preferences = self._load_user_preferences(user_id)
        if preferences:
            # Cache the result
            self.cache.set(f"preferences:{user_id}", preferences.to_dict(), ttl=3600)
        
        return preferences
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> NotificationPreference:
        """Update user notification preferences"""
        
        # Get existing preferences or create new
        user_preferences = self.get_user_preferences(user_id)
        if not user_preferences:
            user_preferences = NotificationPreference(user_id=user_id)
        
        # Update preferences
        updatable_fields = [
            'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled',
            'quote_notifications', 'booking_notifications', 'shipment_notifications',
            'payment_notifications', 'marketing_notifications', 'system_notifications',
            'email_address', 'phone_number', 'timezone',
            'quiet_hours_start', 'quiet_hours_end',
            'digest_frequency', 'digest_time'
        ]
        
        for field in updatable_fields:
            if field in preferences:
                setattr(user_preferences, field, preferences[field])
        
        user_preferences.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_user_preferences(user_preferences)
        
        # Update cache
        self.cache.set(f"preferences:{user_id}", user_preferences.to_dict(), ttl=3600)
        
        # Publish preferences updated event
        self.event_producer.publish('notification.preferences_updated', {
            'user_id': user_id,
            'preferences': preferences,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return user_preferences
    
    def send_bulk_notifications(self, recipients: List[str], template_id: str,
                              template_data: Dict[str, Any], channels: List[str] = None,
                              priority: str = "normal", created_by: str = "") -> Dict[str, Any]:
        """Send bulk notifications using a template"""
        
        # Get template
        template = self._load_template(template_id)
        if not template:
            raise NotFound("Template not found")
        
        # Validate template data
        missing_vars = template.validate_data(template_data)
        if missing_vars:
            raise BadRequest(f"Missing template variables: {', '.join(missing_vars)}")
        
        # Render template
        rendered = template.render(template_data)
        
        results = {
            'total_recipients': len(recipients),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        # Create notifications for each recipient
        for recipient_id in recipients:
            try:
                notification = self.create_notification(
                    recipient_id=recipient_id,
                    notification_type=template.template_type.value,
                    title=rendered['subject'],
                    content=rendered['content'],
                    channels=channels or [ch.value for ch in template.supported_channels],
                    priority=priority,
                    metadata={'template_id': template_id, 'bulk_send': True},
                    created_by=created_by
                )
                results['successful'] += 1
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'recipient_id': recipient_id,
                    'error': str(e)
                })
        
        # Publish bulk send event
        self.event_producer.publish('notifications.bulk_sent', {
            'template_id': template_id,
            'total_recipients': results['total_recipients'],
            'successful': results['successful'],
            'failed': results['failed'],
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return results
    
    def get_notification_analytics(self, date_from: Optional[str] = None,
                                 date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get notification analytics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_notification_analytics_data(start_date, end_date)
        
        return {
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            },
            'overview': {
                'total_notifications': analytics.get('total_notifications', 0),
                'sent_notifications': analytics.get('sent_notifications', 0),
                'delivered_notifications': analytics.get('delivered_notifications', 0),
                'read_notifications': analytics.get('read_notifications', 0),
                'failed_notifications': analytics.get('failed_notifications', 0),
                'delivery_rate': analytics.get('delivery_rate', 0),
                'read_rate': analytics.get('read_rate', 0)
            },
            'by_type': analytics.get('by_type', {}),
            'by_channel': analytics.get('by_channel', {}),
            'by_priority': analytics.get('by_priority', {}),
            'daily_stats': analytics.get('daily_stats', []),
            'top_recipients': analytics.get('top_recipients', []),
            'performance_metrics': {
                'average_delivery_time': analytics.get('avg_delivery_time', 0),
                'average_read_time': analytics.get('avg_read_time', 0),
                'bounce_rate': analytics.get('bounce_rate', 0),
                'unsubscribe_rate': analytics.get('unsubscribe_rate', 0)
            }
        }
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _save_notification(self, notification: Notification):
        """Save notification to database"""
        # Mock implementation
        pass
    
    def _load_notification(self, notification_id: str) -> Optional[Notification]:
        """Load notification from database"""
        # Mock implementation - return a sample notification for demo
        if notification_id == "demo":
            notification = Notification(
                id=notification_id,
                recipient_id="user-123",
                notification_type=NotificationType.QUOTE_CREATED,
                title="New Quote Available",
                content="Your freight quote #QT240824001 is ready for review.",
                channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
                priority=NotificationPriority.NORMAL,
                status=NotificationStatus.DELIVERED
            )
            return notification
        return None
    
    def _query_notifications(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query notifications from database"""
        # Mock implementation
        demo_notification = self._load_notification("demo")
        if demo_notification and filters.get('recipient_id') == "user-123":
            return {
                'items': [demo_notification.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _query_unread_notifications(self, user_id: str) -> List[Dict]:
        """Query unread notifications for a user"""
        # Mock implementation
        return []
    
    def _delete_notification(self, notification_id: str):
        """Delete notification from database"""
        # Mock implementation
        pass
    
    def _load_user_preferences(self, user_id: str) -> Optional[NotificationPreference]:
        """Load user preferences from database"""
        # Mock implementation - return default preferences
        return NotificationPreference(
            user_id=user_id,
            email_enabled=True,
            sms_enabled=False,
            push_enabled=True,
            in_app_enabled=True
        )
    
    def _save_user_preferences(self, preferences: NotificationPreference):
        """Save user preferences to database"""
        # Mock implementation
        pass
    
    def _load_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Load template from database"""
        # Mock implementation
        return None
    
    def _get_notification_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get notification analytics data from database"""
        # Mock implementation
        return {
            'total_notifications': 1250,
            'sent_notifications': 1200,
            'delivered_notifications': 1150,
            'read_notifications': 890,
            'failed_notifications': 50,
            'delivery_rate': 95.8,
            'read_rate': 77.4,
            'by_type': {
                'QUOTE_CREATED': 450,
                'SHIPMENT_STATUS_UPDATE': 380,
                'BOOKING_CONFIRMED': 220,
                'PAYMENT_DUE': 120,
                'SYSTEM_ALERT': 80
            },
            'by_channel': {
                'EMAIL': 800,
                'IN_APP': 650,
                'SMS': 200,
                'PUSH': 150
            },
            'by_priority': {
                'NORMAL': 900,
                'HIGH': 250,
                'URGENT': 80,
                'LOW': 20
            },
            'daily_stats': [
                {'date': '2024-08-20', 'sent': 45, 'delivered': 43, 'read': 32},
                {'date': '2024-08-21', 'sent': 52, 'delivered': 50, 'read': 38},
                {'date': '2024-08-22', 'sent': 48, 'delivered': 46, 'read': 35}
            ],
            'top_recipients': [
                {'user_id': 'user-123', 'count': 25},
                {'user_id': 'user-456', 'count': 22},
                {'user_id': 'user-789', 'count': 18}
            ],
            'avg_delivery_time': 2.5,
            'avg_read_time': 45.2,
            'bounce_rate': 1.2,
            'unsubscribe_rate': 0.3
        }
    
    def _dict_to_notification(self, data: Dict) -> Notification:
        """Convert dictionary to Notification object"""
        notification = Notification()
        notification.id = data.get('id', '')
        notification.recipient_id = data.get('recipient_id', '')
        notification.notification_type = NotificationType(data.get('notification_type', 'SYSTEM_ALERT'))
        notification.title = data.get('title', '')
        notification.content = data.get('content', '')
        notification.status = NotificationStatus(data.get('status', 'PENDING'))
        notification.priority = NotificationPriority(data.get('priority', 'NORMAL'))
        notification.channels = [NotificationChannel(ch) for ch in data.get('channels', ['EMAIL'])]
        return notification
    
    def _dict_to_preferences(self, data: Dict) -> NotificationPreference:
        """Convert dictionary to NotificationPreference object"""
        preferences = NotificationPreference()
        preferences.id = data.get('id', '')
        preferences.user_id = data.get('user_id', '')
        preferences.email_enabled = data.get('email_enabled', True)
        preferences.sms_enabled = data.get('sms_enabled', False)
        preferences.push_enabled = data.get('push_enabled', True)
        preferences.in_app_enabled = data.get('in_app_enabled', True)
        return preferences

