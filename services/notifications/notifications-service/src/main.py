import os
import sys
import json
import uuid
import threading
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, NotFound, Conflict

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from shared.config import Config
from shared.database import Database
from shared.cache import Cache
from shared.events import EventConsumer, EventProducer
from shared.auth import auth_required, admin_required

# Import models and services
from models.notification import Notification, NotificationTemplate, NotificationPreference
from models.channel import NotificationChannel, ChannelConfig
from services.notification_service import NotificationService
from services.template_service import TemplateService
from services.delivery_service import DeliveryService
from services.event_processor import EventProcessor

# Custom JSON encoder for handling special types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json_encoder = CustomJSONEncoder
    
    # Enable CORS for all routes
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Initialize services
    db = Database()
    cache = Cache()
    event_producer = EventProducer()
    event_consumer = EventConsumer()
    
    notification_service = NotificationService(db, cache, event_producer)
    template_service = TemplateService(db, cache, event_producer)
    delivery_service = DeliveryService(db, cache, event_producer)
    event_processor = EventProcessor(notification_service, template_service, delivery_service)
    
    # Start event consumer in background thread
    def start_event_consumer():
        event_consumer.subscribe([
            'quote.created', 'quote.updated', 'quote.expired',
            'booking.created', 'booking.confirmed', 'booking.cancelled',
            'shipment.created', 'shipment.status_changed', 'shipment.delivered',
            'customer.created', 'customer.updated',
            'vendor.created', 'vendor.status_changed',
            'contract.created', 'contract.expiring', 'contract.terminated',
            'user.registered', 'user.password_reset'
        ], event_processor.process_event)
    
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'notifications-service',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Notification Management Endpoints
    @app.route('/api/v1/notifications', methods=['POST'])
    @auth_required
    def create_notification():
        """Create a new notification"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['recipient_id', 'type', 'title', 'content']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            notification = notification_service.create_notification(
                recipient_id=data['recipient_id'],
                notification_type=data['type'],
                title=data['title'],
                content=data['content'],
                channels=data.get('channels', ['email']),
                priority=data.get('priority', 'normal'),
                scheduled_at=data.get('scheduled_at'),
                metadata=data.get('metadata', {}),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'notification': notification.to_dict(),
                'message': 'Notification created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error creating notification: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/notifications', methods=['GET'])
    @auth_required
    def get_notifications():
        """Get notifications for the authenticated user"""
        try:
            recipient_id = request.args.get('recipient_id', request.user_id)
            status = request.args.get('status')
            notification_type = request.args.get('type')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            notifications = notification_service.get_notifications(
                recipient_id=recipient_id,
                status=status,
                notification_type=notification_type,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'notifications': [notif.to_dict() for notif in notifications['items']],
                'pagination': {
                    'page': notifications['page'],
                    'per_page': notifications['per_page'],
                    'total': notifications['total'],
                    'pages': notifications['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching notifications: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/notifications/<notification_id>', methods=['GET'])
    @auth_required
    def get_notification(notification_id):
        """Get a specific notification by ID"""
        try:
            notification = notification_service.get_notification(notification_id)
            if not notification:
                raise NotFound("Notification not found")
            
            # Check if user has access to this notification
            if notification.recipient_id != request.user_id and not request.is_admin:
                return jsonify({'error': 'Access denied'}), 403
            
            return jsonify({
                'success': True,
                'notification': notification.to_dict()
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching notification: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/notifications/<notification_id>/read', methods=['POST'])
    @auth_required
    def mark_notification_read(notification_id):
        """Mark a notification as read"""
        try:
            notification = notification_service.mark_as_read(
                notification_id=notification_id,
                user_id=request.user_id
            )
            
            return jsonify({
                'success': True,
                'notification': notification.to_dict(),
                'message': 'Notification marked as read'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error marking notification as read: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/notifications/mark-all-read', methods=['POST'])
    @auth_required
    def mark_all_notifications_read():
        """Mark all notifications as read for the user"""
        try:
            count = notification_service.mark_all_as_read(request.user_id)
            
            return jsonify({
                'success': True,
                'marked_count': count,
                'message': f'Marked {count} notifications as read'
            })
            
        except Exception as e:
            app.logger.error(f"Error marking all notifications as read: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/notifications/<notification_id>', methods=['DELETE'])
    @auth_required
    def delete_notification(notification_id):
        """Delete a notification"""
        try:
            notification_service.delete_notification(
                notification_id=notification_id,
                user_id=request.user_id
            )
            
            return jsonify({
                'success': True,
                'message': 'Notification deleted successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error deleting notification: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Template Management Endpoints
    @app.route('/api/v1/templates', methods=['POST'])
    @admin_required
    def create_template():
        """Create a notification template"""
        try:
            data = request.get_json()
            
            required_fields = ['name', 'type', 'subject', 'content']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            template = template_service.create_template(
                name=data['name'],
                template_type=data['type'],
                subject=data['subject'],
                content=data['content'],
                variables=data.get('variables', []),
                channels=data.get('channels', ['email']),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'template': template.to_dict(),
                'message': 'Template created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error creating template: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/templates', methods=['GET'])
    @admin_required
    def get_templates():
        """Get notification templates"""
        try:
            template_type = request.args.get('type')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            templates = template_service.get_templates(
                template_type=template_type,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'templates': [template.to_dict() for template in templates['items']],
                'pagination': {
                    'page': templates['page'],
                    'per_page': templates['per_page'],
                    'total': templates['total'],
                    'pages': templates['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching templates: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/templates/<template_id>', methods=['PUT'])
    @admin_required
    def update_template(template_id):
        """Update a notification template"""
        try:
            data = request.get_json()
            
            template = template_service.update_template(
                template_id=template_id,
                updates=data,
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'template': template.to_dict(),
                'message': 'Template updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error updating template: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # User Preferences Endpoints
    @app.route('/api/v1/preferences', methods=['GET'])
    @auth_required
    def get_notification_preferences():
        """Get user notification preferences"""
        try:
            preferences = notification_service.get_user_preferences(request.user_id)
            
            return jsonify({
                'success': True,
                'preferences': preferences.to_dict() if preferences else None
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching preferences: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/preferences', methods=['PUT'])
    @auth_required
    def update_notification_preferences():
        """Update user notification preferences"""
        try:
            data = request.get_json()
            
            preferences = notification_service.update_user_preferences(
                user_id=request.user_id,
                preferences=data
            )
            
            return jsonify({
                'success': True,
                'preferences': preferences.to_dict(),
                'message': 'Preferences updated successfully'
            })
            
        except Exception as e:
            app.logger.error(f"Error updating preferences: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Delivery Status Endpoints
    @app.route('/api/v1/notifications/<notification_id>/delivery', methods=['GET'])
    @auth_required
    def get_delivery_status(notification_id):
        """Get delivery status for a notification"""
        try:
            delivery_status = delivery_service.get_delivery_status(notification_id)
            
            return jsonify({
                'success': True,
                'delivery_status': delivery_status
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching delivery status: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Analytics Endpoints
    @app.route('/api/v1/analytics/notifications', methods=['GET'])
    @admin_required
    def get_notification_analytics():
        """Get notification analytics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            analytics = notification_service.get_notification_analytics(
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching notification analytics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/analytics/delivery', methods=['GET'])
    @admin_required
    def get_delivery_analytics():
        """Get delivery analytics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            analytics = delivery_service.get_delivery_analytics(
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching delivery analytics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Bulk Operations
    @app.route('/api/v1/notifications/bulk', methods=['POST'])
    @admin_required
    def send_bulk_notifications():
        """Send bulk notifications"""
        try:
            data = request.get_json()
            
            required_fields = ['recipients', 'template_id', 'data']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            result = notification_service.send_bulk_notifications(
                recipients=data['recipients'],
                template_id=data['template_id'],
                template_data=data['data'],
                channels=data.get('channels', ['email']),
                priority=data.get('priority', 'normal'),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'result': result,
                'message': 'Bulk notifications sent successfully'
            })
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error sending bulk notifications: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Channel Configuration Endpoints
    @app.route('/api/v1/channels', methods=['GET'])
    @admin_required
    def get_notification_channels():
        """Get notification channel configurations"""
        try:
            channels = delivery_service.get_channel_configurations()
            
            return jsonify({
                'success': True,
                'channels': [channel.to_dict() for channel in channels]
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching channels: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/channels/<channel_type>', methods=['PUT'])
    @admin_required
    def update_channel_config(channel_type):
        """Update channel configuration"""
        try:
            data = request.get_json()
            
            channel = delivery_service.update_channel_configuration(
                channel_type=channel_type,
                config=data,
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'channel': channel.to_dict(),
                'message': 'Channel configuration updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error updating channel config: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Test Endpoints
    @app.route('/api/v1/test/notification', methods=['POST'])
    @admin_required
    def test_notification():
        """Send a test notification"""
        try:
            data = request.get_json()
            
            required_fields = ['recipient_id', 'channel']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            result = delivery_service.send_test_notification(
                recipient_id=data['recipient_id'],
                channel=data['channel'],
                message=data.get('message', 'This is a test notification')
            )
            
            return jsonify({
                'success': True,
                'result': result,
                'message': 'Test notification sent successfully'
            })
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error sending test notification: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 8105))
    app.run(host='0.0.0.0', port=port, debug=True)
