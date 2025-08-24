import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

class NotificationStatus(Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class NotificationType(Enum):
    QUOTE_CREATED = "QUOTE_CREATED"
    QUOTE_UPDATED = "QUOTE_UPDATED"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
    BOOKING_CANCELLED = "BOOKING_CANCELLED"
    SHIPMENT_STATUS_UPDATE = "SHIPMENT_STATUS_UPDATE"
    SHIPMENT_DELIVERED = "SHIPMENT_DELIVERED"
    PAYMENT_DUE = "PAYMENT_DUE"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    DOCUMENT_READY = "DOCUMENT_READY"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    MARKETING = "MARKETING"
    REMINDER = "REMINDER"
    WELCOME = "WELCOME"
    PASSWORD_RESET = "PASSWORD_RESET"

class NotificationPriority(Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

class NotificationChannel(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"

@dataclass
class NotificationDelivery:
    """Delivery attempt for a notification"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_id: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    status: str = "PENDING"  # PENDING, SENT, DELIVERED, FAILED
    attempt_number: int = 1
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'notification_id': self.notification_id,
            'channel': self.channel.value,
            'status': self.status,
            'attempt_number': self.attempt_number,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'error_message': self.error_message,
            'provider_response': self.provider_response,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class Notification:
    """Notification model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recipient_id: str = ""
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    notification_type: NotificationType = NotificationType.SYSTEM_ALERT
    title: str = ""
    content: str = ""
    html_content: Optional[str] = None
    
    # Delivery settings
    channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.EMAIL])
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Scheduling
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Status tracking
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # Delivery attempts
    delivery_attempts: List[NotificationDelivery] = field(default_factory=list)
    max_attempts: int = 3
    
    # Metadata and context
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None
    template_data: Dict[str, Any] = field(default_factory=dict)
    
    # Related entities
    related_entity_type: Optional[str] = None  # e.g., "quote", "shipment", "booking"
    related_entity_id: Optional[str] = None
    
    # Tracking
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_delivery_attempt(self, channel: NotificationChannel, 
                           status: str = "PENDING") -> NotificationDelivery:
        """Add a delivery attempt"""
        attempt = NotificationDelivery(
            notification_id=self.id,
            channel=channel,
            status=status,
            attempt_number=len([d for d in self.delivery_attempts if d.channel == channel]) + 1
        )
        self.delivery_attempts.append(attempt)
        self.updated_at = datetime.utcnow()
        return attempt
    
    def mark_as_sent(self, channel: NotificationChannel):
        """Mark notification as sent for a specific channel"""
        for attempt in self.delivery_attempts:
            if attempt.channel == channel and attempt.status == "PENDING":
                attempt.status = "SENT"
                attempt.sent_at = datetime.utcnow()
                break
        
        if self.status == NotificationStatus.PENDING:
            self.status = NotificationStatus.SENT
            self.sent_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    def mark_as_delivered(self, channel: NotificationChannel):
        """Mark notification as delivered for a specific channel"""
        for attempt in self.delivery_attempts:
            if attempt.channel == channel and attempt.status == "SENT":
                attempt.status = "DELIVERED"
                attempt.delivered_at = datetime.utcnow()
                break
        
        # If all channels are delivered, mark notification as delivered
        all_delivered = all(
            any(d.status == "DELIVERED" for d in self.delivery_attempts if d.channel == ch)
            for ch in self.channels
        )
        
        if all_delivered:
            self.status = NotificationStatus.DELIVERED
            self.delivered_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_as_failed(self, channel: NotificationChannel, error_message: str):
        """Mark notification as failed for a specific channel"""
        for attempt in self.delivery_attempts:
            if attempt.channel == channel and attempt.status in ["PENDING", "SENT"]:
                attempt.status = "FAILED"
                attempt.failed_at = datetime.utcnow()
                attempt.error_message = error_message
                break
        
        # Check if all channels have failed
        all_failed = all(
            all(d.status == "FAILED" for d in self.delivery_attempts if d.channel == ch)
            for ch in self.channels
        )
        
        if all_failed:
            self.status = NotificationStatus.FAILED
        
        self.updated_at = datetime.utcnow()
    
    def can_retry(self, channel: NotificationChannel) -> bool:
        """Check if notification can be retried for a channel"""
        channel_attempts = [d for d in self.delivery_attempts if d.channel == channel]
        return len(channel_attempts) < self.max_attempts
    
    def is_expired(self) -> bool:
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled for future delivery"""
        if not self.scheduled_at:
            return False
        return datetime.utcnow() < self.scheduled_at
    
    def get_delivery_status_by_channel(self) -> Dict[str, str]:
        """Get delivery status for each channel"""
        status_by_channel = {}
        for channel in self.channels:
            latest_attempt = None
            for attempt in self.delivery_attempts:
                if attempt.channel == channel:
                    if not latest_attempt or attempt.created_at > latest_attempt.created_at:
                        latest_attempt = attempt
            
            status_by_channel[channel.value] = latest_attempt.status if latest_attempt else "NOT_ATTEMPTED"
        
        return status_by_channel
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'recipient_id': self.recipient_id,
            'recipient_email': self.recipient_email,
            'recipient_phone': self.recipient_phone,
            'notification_type': self.notification_type.value,
            'title': self.title,
            'content': self.content,
            'html_content': self.html_content,
            'channels': [ch.value for ch in self.channels],
            'priority': self.priority.value,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status.value,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'delivery_attempts': [attempt.to_dict() for attempt in self.delivery_attempts],
            'delivery_status_by_channel': self.get_delivery_status_by_channel(),
            'max_attempts': self.max_attempts,
            'metadata': self.metadata,
            'template_id': self.template_id,
            'template_data': self.template_data,
            'related_entity_type': self.related_entity_type,
            'related_entity_id': self.related_entity_id,
            'is_expired': self.is_expired(),
            'is_scheduled': self.is_scheduled(),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class NotificationTemplate:
    """Notification template model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    template_type: NotificationType = NotificationType.SYSTEM_ALERT
    subject: str = ""
    content: str = ""
    html_content: Optional[str] = None
    
    # Template variables
    variables: List[str] = field(default_factory=list)
    sample_data: Dict[str, Any] = field(default_factory=dict)
    
    # Channel support
    supported_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.EMAIL])
    
    # Template settings
    is_active: bool = True
    version: int = 1
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Tracking
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def render(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Render template with provided data"""
        rendered_subject = self.subject
        rendered_content = self.content
        rendered_html = self.html_content
        
        # Simple template variable replacement
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_content = rendered_content.replace(placeholder, str(value))
            if rendered_html:
                rendered_html = rendered_html.replace(placeholder, str(value))
        
        return {
            'subject': rendered_subject,
            'content': rendered_content,
            'html_content': rendered_html
        }
    
    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate that all required variables are provided"""
        missing_variables = []
        for variable in self.variables:
            if variable not in data:
                missing_variables.append(variable)
        return missing_variables
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'template_type': self.template_type.value,
            'subject': self.subject,
            'content': self.content,
            'html_content': self.html_content,
            'variables': self.variables,
            'sample_data': self.sample_data,
            'supported_channels': [ch.value for ch in self.supported_channels],
            'is_active': self.is_active,
            'version': self.version,
            'description': self.description,
            'tags': self.tags,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class NotificationPreference:
    """User notification preferences"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    
    # Channel preferences
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    
    # Type preferences
    quote_notifications: bool = True
    booking_notifications: bool = True
    shipment_notifications: bool = True
    payment_notifications: bool = True
    marketing_notifications: bool = False
    system_notifications: bool = True
    
    # Delivery preferences
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    timezone: str = "UTC"
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None    # HH:MM format
    
    # Frequency preferences
    digest_frequency: str = "NONE"  # NONE, DAILY, WEEKLY
    digest_time: str = "09:00"      # HH:MM format
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """Check if a channel is enabled"""
        channel_map = {
            NotificationChannel.EMAIL: self.email_enabled,
            NotificationChannel.SMS: self.sms_enabled,
            NotificationChannel.PUSH: self.push_enabled,
            NotificationChannel.IN_APP: self.in_app_enabled
        }
        return channel_map.get(channel, False)
    
    def is_type_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a notification type is enabled"""
        type_map = {
            NotificationType.QUOTE_CREATED: self.quote_notifications,
            NotificationType.QUOTE_UPDATED: self.quote_notifications,
            NotificationType.QUOTE_EXPIRED: self.quote_notifications,
            NotificationType.BOOKING_CONFIRMED: self.booking_notifications,
            NotificationType.BOOKING_CANCELLED: self.booking_notifications,
            NotificationType.SHIPMENT_STATUS_UPDATE: self.shipment_notifications,
            NotificationType.SHIPMENT_DELIVERED: self.shipment_notifications,
            NotificationType.PAYMENT_DUE: self.payment_notifications,
            NotificationType.PAYMENT_RECEIVED: self.payment_notifications,
            NotificationType.MARKETING: self.marketing_notifications,
            NotificationType.SYSTEM_ALERT: self.system_notifications,
        }
        return type_map.get(notification_type, True)
    
    def is_in_quiet_hours(self, check_time: Optional[datetime] = None) -> bool:
        """Check if current time is in quiet hours"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        if not check_time:
            check_time = datetime.utcnow()
        
        # Simple time comparison (ignoring timezone for now)
        current_time = check_time.strftime("%H:%M")
        return self.quiet_hours_start <= current_time <= self.quiet_hours_end
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email_enabled': self.email_enabled,
            'sms_enabled': self.sms_enabled,
            'push_enabled': self.push_enabled,
            'in_app_enabled': self.in_app_enabled,
            'quote_notifications': self.quote_notifications,
            'booking_notifications': self.booking_notifications,
            'shipment_notifications': self.shipment_notifications,
            'payment_notifications': self.payment_notifications,
            'marketing_notifications': self.marketing_notifications,
            'system_notifications': self.system_notifications,
            'email_address': self.email_address,
            'phone_number': self.phone_number,
            'timezone': self.timezone,
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end,
            'digest_frequency': self.digest_frequency,
            'digest_time': self.digest_time,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

