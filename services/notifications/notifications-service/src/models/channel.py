import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

class ChannelType(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"
    SLACK = "SLACK"
    TEAMS = "TEAMS"

class ChannelStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"

@dataclass
class ChannelConfig:
    """Configuration for a notification channel"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel_type: ChannelType = ChannelType.EMAIL
    name: str = ""
    description: Optional[str] = None
    
    # Provider configuration
    provider: str = ""  # e.g., "sendgrid", "twilio", "firebase"
    provider_config: Dict[str, Any] = field(default_factory=dict)
    
    # Channel settings
    is_enabled: bool = True
    is_default: bool = False
    priority: int = 1  # Lower number = higher priority
    
    # Rate limiting
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 60
    exponential_backoff: bool = True
    
    # Health monitoring
    status: ChannelStatus = ChannelStatus.ACTIVE
    last_health_check: Optional[datetime] = None
    health_check_interval_minutes: int = 5
    
    # Statistics
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    success_rate: float = 0.0
    
    # Tracking
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update_statistics(self, sent: int = 0, delivered: int = 0, failed: int = 0):
        """Update channel statistics"""
        self.total_sent += sent
        self.total_delivered += delivered
        self.total_failed += failed
        
        if self.total_sent > 0:
            self.success_rate = (self.total_delivered / self.total_sent) * 100
        
        self.updated_at = datetime.utcnow()
    
    def is_healthy(self) -> bool:
        """Check if channel is healthy"""
        return self.status == ChannelStatus.ACTIVE and self.success_rate >= 90.0
    
    def needs_health_check(self) -> bool:
        """Check if channel needs a health check"""
        if not self.last_health_check:
            return True
        
        minutes_since_check = (datetime.utcnow() - self.last_health_check).total_seconds() / 60
        return minutes_since_check >= self.health_check_interval_minutes
    
    def calculate_retry_delay(self, attempt: int) -> int:
        """Calculate retry delay for a given attempt"""
        if not self.exponential_backoff:
            return self.retry_delay_seconds
        
        return self.retry_delay_seconds * (2 ** (attempt - 1))
    
    def is_rate_limited(self, current_minute: int, current_hour: int, current_day: int) -> bool:
        """Check if channel is rate limited"""
        if self.rate_limit_per_minute and current_minute >= self.rate_limit_per_minute:
            return True
        
        if self.rate_limit_per_hour and current_hour >= self.rate_limit_per_hour:
            return True
        
        if self.rate_limit_per_day and current_day >= self.rate_limit_per_day:
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'channel_type': self.channel_type.value,
            'name': self.name,
            'description': self.description,
            'provider': self.provider,
            'provider_config': self.provider_config,
            'is_enabled': self.is_enabled,
            'is_default': self.is_default,
            'priority': self.priority,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'rate_limit_per_day': self.rate_limit_per_day,
            'max_retries': self.max_retries,
            'retry_delay_seconds': self.retry_delay_seconds,
            'exponential_backoff': self.exponential_backoff,
            'status': self.status.value,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'health_check_interval_minutes': self.health_check_interval_minutes,
            'total_sent': self.total_sent,
            'total_delivered': self.total_delivered,
            'total_failed': self.total_failed,
            'success_rate': self.success_rate,
            'is_healthy': self.is_healthy(),
            'needs_health_check': self.needs_health_check(),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class NotificationChannel:
    """Notification channel instance for delivery"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config_id: str = ""
    notification_id: str = ""
    
    # Delivery details
    recipient: str = ""  # email address, phone number, etc.
    message_id: Optional[str] = None  # Provider message ID
    
    # Status tracking
    status: str = "PENDING"  # PENDING, SENT, DELIVERED, FAILED
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Error handling
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    next_retry_at: Optional[datetime] = None
    
    # Provider response
    provider_response: Optional[Dict[str, Any]] = None
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def mark_as_sent(self, message_id: Optional[str] = None, provider_response: Optional[Dict] = None):
        """Mark channel as sent"""
        self.status = "SENT"
        self.sent_at = datetime.utcnow()
        self.message_id = message_id
        self.provider_response = provider_response
        self.updated_at = datetime.utcnow()
    
    def mark_as_delivered(self, provider_response: Optional[Dict] = None):
        """Mark channel as delivered"""
        self.status = "DELIVERED"
        self.delivered_at = datetime.utcnow()
        if provider_response:
            self.provider_response = provider_response
        self.updated_at = datetime.utcnow()
    
    def mark_as_failed(self, error_code: str, error_message: str, provider_response: Optional[Dict] = None):
        """Mark channel as failed"""
        self.status = "FAILED"
        self.failed_at = datetime.utcnow()
        self.error_code = error_code
        self.error_message = error_message
        if provider_response:
            self.provider_response = provider_response
        self.updated_at = datetime.utcnow()
    
    def schedule_retry(self, delay_seconds: int):
        """Schedule a retry"""
        self.retry_count += 1
        self.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        self.status = "PENDING"
        self.updated_at = datetime.utcnow()
    
    def can_retry(self, max_retries: int) -> bool:
        """Check if channel can be retried"""
        return self.retry_count < max_retries and self.status == "FAILED"
    
    def is_ready_for_retry(self) -> bool:
        """Check if channel is ready for retry"""
        if not self.next_retry_at:
            return False
        return datetime.utcnow() >= self.next_retry_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'config_id': self.config_id,
            'notification_id': self.notification_id,
            'recipient': self.recipient,
            'message_id': self.message_id,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'provider_response': self.provider_response,
            'can_retry': self.can_retry(3),  # Default max retries
            'is_ready_for_retry': self.is_ready_for_retry(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

