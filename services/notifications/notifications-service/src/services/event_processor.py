import json
from datetime import datetime
from typing import Dict, Any, Optional

from models.notification import NotificationType, NotificationPriority

class EventProcessor:
    """Process events and create notifications"""
    
    def __init__(self, notification_service, template_service, delivery_service):
        self.notification_service = notification_service
        self.template_service = template_service
        self.delivery_service = delivery_service
        
        # Event to notification type mapping
        self.event_mapping = {
            'quote.created': NotificationType.QUOTE_CREATED,
            'quote.updated': NotificationType.QUOTE_UPDATED,
            'quote.expired': NotificationType.QUOTE_EXPIRED,
            'booking.created': NotificationType.BOOKING_CONFIRMED,
            'booking.confirmed': NotificationType.BOOKING_CONFIRMED,
            'booking.cancelled': NotificationType.BOOKING_CANCELLED,
            'shipment.created': NotificationType.SHIPMENT_STATUS_UPDATE,
            'shipment.status_changed': NotificationType.SHIPMENT_STATUS_UPDATE,
            'shipment.delivered': NotificationType.SHIPMENT_DELIVERED,
            'payment.due': NotificationType.PAYMENT_DUE,
            'payment.received': NotificationType.PAYMENT_RECEIVED,
            'document.ready': NotificationType.DOCUMENT_READY,
            'user.registered': NotificationType.WELCOME,
            'user.password_reset': NotificationType.PASSWORD_RESET,
            'system.alert': NotificationType.SYSTEM_ALERT
        }
    
    def process_event(self, event_type: str, event_data: Dict[str, Any]):
        """Process an event and create appropriate notifications"""
        
        try:
            # Get notification type for this event
            notification_type = self.event_mapping.get(event_type)
            if not notification_type:
                print(f"No notification mapping for event type: {event_type}")
                return
            
            # Process specific event types
            if event_type == 'quote.created':
                self._process_quote_created(event_data)
            elif event_type == 'quote.updated':
                self._process_quote_updated(event_data)
            elif event_type == 'quote.expired':
                self._process_quote_expired(event_data)
            elif event_type == 'booking.confirmed':
                self._process_booking_confirmed(event_data)
            elif event_type == 'booking.cancelled':
                self._process_booking_cancelled(event_data)
            elif event_type == 'shipment.status_changed':
                self._process_shipment_status_changed(event_data)
            elif event_type == 'shipment.delivered':
                self._process_shipment_delivered(event_data)
            elif event_type == 'payment.due':
                self._process_payment_due(event_data)
            elif event_type == 'payment.received':
                self._process_payment_received(event_data)
            elif event_type == 'user.registered':
                self._process_user_registered(event_data)
            elif event_type == 'user.password_reset':
                self._process_password_reset(event_data)
            elif event_type.startswith('contract.'):
                self._process_contract_event(event_type, event_data)
            elif event_type.startswith('vendor.'):
                self._process_vendor_event(event_type, event_data)
            else:
                # Generic event processing
                self._process_generic_event(event_type, event_data, notification_type)
                
        except Exception as e:
            print(f"Error processing event {event_type}: {str(e)}")
    
    def _process_quote_created(self, event_data: Dict[str, Any]):
        """Process quote created event"""
        
        customer_id = event_data.get('customer_id')
        quote_number = event_data.get('quote_number')
        
        if not customer_id or not quote_number:
            return
        
        # Create notification for customer
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.QUOTE_CREATED.value,
            title=f"New Quote Available - {quote_number}",
            content=f"Your freight quote {quote_number} is ready for review. Please check your dashboard to view the details and confirm your booking.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.NORMAL.value,
            metadata={
                'quote_id': event_data.get('quote_id'),
                'quote_number': quote_number,
                'origin': event_data.get('origin'),
                'destination': event_data.get('destination'),
                'total_cost': event_data.get('total_cost')
            },
            created_by='system'
        )
        
        # Notify sales team if high-value quote
        total_cost = event_data.get('total_cost', 0)
        if total_cost > 10000:  # High-value threshold
            self._notify_sales_team(
                title=f"High-Value Quote Created - {quote_number}",
                content=f"A high-value quote ({total_cost}) has been created for customer {customer_id}. Quote: {quote_number}",
                metadata=event_data
            )
    
    def _process_quote_updated(self, event_data: Dict[str, Any]):
        """Process quote updated event"""
        
        customer_id = event_data.get('customer_id')
        quote_number = event_data.get('quote_number')
        
        if not customer_id or not quote_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.QUOTE_UPDATED.value,
            title=f"Quote Updated - {quote_number}",
            content=f"Your freight quote {quote_number} has been updated. Please review the changes in your dashboard.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.NORMAL.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_quote_expired(self, event_data: Dict[str, Any]):
        """Process quote expired event"""
        
        customer_id = event_data.get('customer_id')
        quote_number = event_data.get('quote_number')
        
        if not customer_id or not quote_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.QUOTE_EXPIRED.value,
            title=f"Quote Expired - {quote_number}",
            content=f"Your freight quote {quote_number} has expired. Please contact us if you would like to request a new quote.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.HIGH.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_booking_confirmed(self, event_data: Dict[str, Any]):
        """Process booking confirmed event"""
        
        customer_id = event_data.get('customer_id')
        booking_number = event_data.get('booking_number')
        
        if not customer_id or not booking_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.BOOKING_CONFIRMED.value,
            title=f"Booking Confirmed - {booking_number}",
            content=f"Your booking {booking_number} has been confirmed. We will keep you updated on the shipment progress.",
            channels=['email', 'sms', 'in_app'],
            priority=NotificationPriority.HIGH.value,
            metadata=event_data,
            created_by='system'
        )
        
        # Notify operations team
        self._notify_operations_team(
            title=f"New Booking Confirmed - {booking_number}",
            content=f"Booking {booking_number} has been confirmed and requires processing.",
            metadata=event_data
        )
    
    def _process_booking_cancelled(self, event_data: Dict[str, Any]):
        """Process booking cancelled event"""
        
        customer_id = event_data.get('customer_id')
        booking_number = event_data.get('booking_number')
        
        if not customer_id or not booking_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.BOOKING_CANCELLED.value,
            title=f"Booking Cancelled - {booking_number}",
            content=f"Your booking {booking_number} has been cancelled. If you have any questions, please contact our support team.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.HIGH.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_shipment_status_changed(self, event_data: Dict[str, Any]):
        """Process shipment status changed event"""
        
        customer_id = event_data.get('customer_id')
        shipment_number = event_data.get('shipment_number')
        new_status = event_data.get('new_status')
        
        if not customer_id or not shipment_number or not new_status:
            return
        
        # Determine priority based on status
        priority = NotificationPriority.NORMAL
        if new_status in ['DELAYED', 'EXCEPTION', 'CUSTOMS_HOLD']:
            priority = NotificationPriority.HIGH
        elif new_status in ['DELIVERED', 'COMPLETED']:
            priority = NotificationPriority.HIGH
        
        # Determine channels based on status importance
        channels = ['in_app']
        if priority == NotificationPriority.HIGH:
            channels.extend(['email', 'sms'])
        else:
            channels.append('email')
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.SHIPMENT_STATUS_UPDATE.value,
            title=f"Shipment Update - {shipment_number}",
            content=f"Your shipment {shipment_number} status has been updated to: {new_status}. Current location: {event_data.get('location', 'Unknown')}",
            channels=channels,
            priority=priority.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_shipment_delivered(self, event_data: Dict[str, Any]):
        """Process shipment delivered event"""
        
        customer_id = event_data.get('customer_id')
        shipment_number = event_data.get('shipment_number')
        
        if not customer_id or not shipment_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.SHIPMENT_DELIVERED.value,
            title=f"Shipment Delivered - {shipment_number}",
            content=f"Your shipment {shipment_number} has been successfully delivered. Thank you for choosing FreightFlow!",
            channels=['email', 'sms', 'in_app'],
            priority=NotificationPriority.HIGH.value,
            metadata=event_data,
            created_by='system'
        )
        
        # Schedule follow-up survey notification
        self._schedule_feedback_request(customer_id, shipment_number, event_data)
    
    def _process_payment_due(self, event_data: Dict[str, Any]):
        """Process payment due event"""
        
        customer_id = event_data.get('customer_id')
        invoice_number = event_data.get('invoice_number')
        amount = event_data.get('amount')
        due_date = event_data.get('due_date')
        
        if not customer_id or not invoice_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.PAYMENT_DUE.value,
            title=f"Payment Due - Invoice {invoice_number}",
            content=f"Your payment of {amount} for invoice {invoice_number} is due on {due_date}. Please make your payment to avoid any service interruptions.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.HIGH.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_payment_received(self, event_data: Dict[str, Any]):
        """Process payment received event"""
        
        customer_id = event_data.get('customer_id')
        invoice_number = event_data.get('invoice_number')
        amount = event_data.get('amount')
        
        if not customer_id or not invoice_number:
            return
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.PAYMENT_RECEIVED.value,
            title=f"Payment Received - Invoice {invoice_number}",
            content=f"We have received your payment of {amount} for invoice {invoice_number}. Thank you for your prompt payment!",
            channels=['email', 'in_app'],
            priority=NotificationPriority.NORMAL.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_user_registered(self, event_data: Dict[str, Any]):
        """Process user registered event"""
        
        user_id = event_data.get('user_id')
        email = event_data.get('email')
        name = event_data.get('name')
        
        if not user_id:
            return
        
        self.notification_service.create_notification(
            recipient_id=user_id,
            notification_type=NotificationType.WELCOME.value,
            title="Welcome to FreightFlow!",
            content=f"Welcome {name}! Your account has been successfully created. Start by requesting your first freight quote or exploring our services.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.NORMAL.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_password_reset(self, event_data: Dict[str, Any]):
        """Process password reset event"""
        
        user_id = event_data.get('user_id')
        reset_token = event_data.get('reset_token')
        
        if not user_id or not reset_token:
            return
        
        self.notification_service.create_notification(
            recipient_id=user_id,
            notification_type=NotificationType.PASSWORD_RESET.value,
            title="Password Reset Request",
            content=f"You have requested a password reset. Use the following token to reset your password: {reset_token}. This token will expire in 1 hour.",
            channels=['email'],
            priority=NotificationPriority.HIGH.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _process_contract_event(self, event_type: str, event_data: Dict[str, Any]):
        """Process contract-related events"""
        
        vendor_id = event_data.get('vendor_id')
        contract_number = event_data.get('contract_number')
        
        if not vendor_id or not contract_number:
            return
        
        if event_type == 'contract.expiring':
            self.notification_service.create_notification(
                recipient_id=vendor_id,
                notification_type=NotificationType.SYSTEM_ALERT.value,
                title=f"Contract Expiring - {contract_number}",
                content=f"Your contract {contract_number} is expiring soon. Please contact us to discuss renewal options.",
                channels=['email', 'in_app'],
                priority=NotificationPriority.HIGH.value,
                metadata=event_data,
                created_by='system'
            )
        elif event_type == 'contract.terminated':
            self.notification_service.create_notification(
                recipient_id=vendor_id,
                notification_type=NotificationType.SYSTEM_ALERT.value,
                title=f"Contract Terminated - {contract_number}",
                content=f"Your contract {contract_number} has been terminated. Please contact us if you have any questions.",
                channels=['email', 'in_app'],
                priority=NotificationPriority.URGENT.value,
                metadata=event_data,
                created_by='system'
            )
    
    def _process_vendor_event(self, event_type: str, event_data: Dict[str, Any]):
        """Process vendor-related events"""
        
        vendor_id = event_data.get('vendor_id')
        
        if not vendor_id:
            return
        
        if event_type == 'vendor.status_changed':
            new_status = event_data.get('new_status')
            self.notification_service.create_notification(
                recipient_id=vendor_id,
                notification_type=NotificationType.SYSTEM_ALERT.value,
                title=f"Vendor Status Changed",
                content=f"Your vendor status has been changed to: {new_status}. Please contact us if you have any questions.",
                channels=['email', 'in_app'],
                priority=NotificationPriority.HIGH.value,
                metadata=event_data,
                created_by='system'
            )
    
    def _process_generic_event(self, event_type: str, event_data: Dict[str, Any], 
                             notification_type: NotificationType):
        """Process generic events"""
        
        recipient_id = event_data.get('recipient_id') or event_data.get('user_id') or event_data.get('customer_id')
        
        if not recipient_id:
            return
        
        self.notification_service.create_notification(
            recipient_id=recipient_id,
            notification_type=notification_type.value,
            title=f"System Notification - {event_type}",
            content=f"An event of type {event_type} has occurred. Please check your dashboard for more details.",
            channels=['in_app'],
            priority=NotificationPriority.NORMAL.value,
            metadata=event_data,
            created_by='system'
        )
    
    def _notify_sales_team(self, title: str, content: str, metadata: Dict[str, Any]):
        """Notify sales team members"""
        
        # Get sales team member IDs (mock implementation)
        sales_team_ids = ['sales-manager-1', 'sales-rep-1', 'sales-rep-2']
        
        for member_id in sales_team_ids:
            self.notification_service.create_notification(
                recipient_id=member_id,
                notification_type=NotificationType.SYSTEM_ALERT.value,
                title=title,
                content=content,
                channels=['email', 'in_app'],
                priority=NotificationPriority.HIGH.value,
                metadata=metadata,
                created_by='system'
            )
    
    def _notify_operations_team(self, title: str, content: str, metadata: Dict[str, Any]):
        """Notify operations team members"""
        
        # Get operations team member IDs (mock implementation)
        ops_team_ids = ['ops-manager-1', 'ops-coordinator-1', 'ops-coordinator-2']
        
        for member_id in ops_team_ids:
            self.notification_service.create_notification(
                recipient_id=member_id,
                notification_type=NotificationType.SYSTEM_ALERT.value,
                title=title,
                content=content,
                channels=['email', 'in_app'],
                priority=NotificationPriority.NORMAL.value,
                metadata=metadata,
                created_by='system'
            )
    
    def _schedule_feedback_request(self, customer_id: str, shipment_number: str, 
                                 event_data: Dict[str, Any]):
        """Schedule a feedback request notification"""
        
        # Schedule notification for 24 hours after delivery
        scheduled_at = datetime.utcnow() + timedelta(hours=24)
        
        self.notification_service.create_notification(
            recipient_id=customer_id,
            notification_type=NotificationType.SYSTEM_ALERT.value,
            title="How was your shipping experience?",
            content=f"We hope your shipment {shipment_number} arrived safely. Please take a moment to rate your experience and help us improve our services.",
            channels=['email', 'in_app'],
            priority=NotificationPriority.LOW.value,
            scheduled_at=scheduled_at.isoformat(),
            metadata={
                'shipment_number': shipment_number,
                'feedback_request': True,
                **event_data
            },
            created_by='system'
        )

