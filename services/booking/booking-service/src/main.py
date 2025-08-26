import os
import sys
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, NotFound, Conflict

from shared.config import Config
from shared.database import Database
from shared.cache import Cache
from shared.storage import Storage
from shared.events import EventProducer
from shared.auth import auth_required, admin_required

# Import models and services
from models.booking import Booking, Shipment, Container, TrackingEvent
from models.customer import Customer
from services.booking_engine import BookingEngine
from services.tracking_service import TrackingService
from services.document_service import DocumentService

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
    storage = Storage()
    event_producer = EventProducer()
    
    booking_engine = BookingEngine(db, cache, event_producer)
    tracking_service = TrackingService(db, cache, event_producer)
    document_service = DocumentService(storage, db)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'booking-service',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Booking Management Endpoints
    @app.route('/api/v1/bookings', methods=['POST'])
    @auth_required
    def create_booking():
        """Create a new booking from an accepted quote"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['quote_id', 'customer_id']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            # Create booking
            booking = booking_engine.create_booking(
                quote_id=data['quote_id'],
                customer_id=data['customer_id'],
                special_instructions=data.get('special_instructions'),
                pickup_contact=data.get('pickup_contact'),
                delivery_contact=data.get('delivery_contact')
            )
            
            return jsonify({
                'success': True,
                'booking': booking.to_dict(),
                'message': 'Booking created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error creating booking: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/bookings', methods=['GET'])
    @auth_required
    def get_bookings():
        """Get bookings for the authenticated user"""
        try:
            user_id = request.user_id
            customer_id = request.args.get('customer_id')
            status = request.args.get('status')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            bookings = booking_engine.get_bookings(
                user_id=user_id,
                customer_id=customer_id,
                status=status,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'bookings': [booking.to_dict() for booking in bookings['items']],
                'pagination': {
                    'page': bookings['page'],
                    'per_page': bookings['per_page'],
                    'total': bookings['total'],
                    'pages': bookings['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching bookings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/bookings/<booking_id>', methods=['GET'])
    @auth_required
    def get_booking(booking_id):
        """Get a specific booking by ID"""
        try:
            booking = booking_engine.get_booking(booking_id, request.user_id)
            if not booking:
                raise NotFound("Booking not found")
            
            return jsonify({
                'success': True,
                'booking': booking.to_dict()
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching booking: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/bookings/<booking_id>/confirm', methods=['POST'])
    @auth_required
    def confirm_booking(booking_id):
        """Confirm a booking and create shipment"""
        try:
            data = request.get_json() or {}
            
            shipment = booking_engine.confirm_booking(
                booking_id=booking_id,
                user_id=request.user_id,
                vessel_details=data.get('vessel_details'),
                container_details=data.get('container_details')
            )
            
            return jsonify({
                'success': True,
                'shipment': shipment.to_dict(),
                'message': 'Booking confirmed and shipment created'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Conflict as e:
            return jsonify({'error': str(e)}), 409
        except Exception as e:
            app.logger.error(f"Error confirming booking: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Shipment Management Endpoints
    @app.route('/api/v1/shipments', methods=['GET'])
    @auth_required
    def get_shipments():
        """Get shipments for the authenticated user"""
        try:
            user_id = request.user_id
            customer_id = request.args.get('customer_id')
            status = request.args.get('status')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            shipments = tracking_service.get_shipments(
                user_id=user_id,
                customer_id=customer_id,
                status=status,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'shipments': [shipment.to_dict() for shipment in shipments['items']],
                'pagination': {
                    'page': shipments['page'],
                    'per_page': shipments['per_page'],
                    'total': shipments['total'],
                    'pages': shipments['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching shipments: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/shipments/<shipment_id>', methods=['GET'])
    @auth_required
    def get_shipment(shipment_id):
        """Get a specific shipment by ID"""
        try:
            shipment = tracking_service.get_shipment(shipment_id, request.user_id)
            if not shipment:
                raise NotFound("Shipment not found")
            
            return jsonify({
                'success': True,
                'shipment': shipment.to_dict()
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching shipment: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/shipments/track/<tracking_number>', methods=['GET'])
    def track_shipment(tracking_number):
        """Track a shipment by tracking number (public endpoint)"""
        try:
            tracking_info = tracking_service.track_shipment(tracking_number)
            if not tracking_info:
                raise NotFound("Tracking number not found")
            
            return jsonify({
                'success': True,
                'tracking': tracking_info
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error tracking shipment: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/shipments/<shipment_id>/tracking', methods=['POST'])
    @admin_required
    def add_tracking_event(shipment_id):
        """Add a tracking event to a shipment (admin only)"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['status', 'location', 'description']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            tracking_event = tracking_service.add_tracking_event(
                shipment_id=shipment_id,
                status=data['status'],
                location=data['location'],
                description=data['description'],
                event_time=data.get('event_time'),
                vessel_name=data.get('vessel_name'),
                voyage_number=data.get('voyage_number')
            )
            
            return jsonify({
                'success': True,
                'tracking_event': tracking_event.to_dict(),
                'message': 'Tracking event added successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error adding tracking event: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Container Management Endpoints
    @app.route('/api/v1/containers', methods=['GET'])
    @admin_required
    def get_containers():
        """Get container inventory (admin only)"""
        try:
            status = request.args.get('status')
            location = request.args.get('location')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)
            
            containers = booking_engine.get_containers(
                status=status,
                location=location,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'containers': [container.to_dict() for container in containers['items']],
                'pagination': {
                    'page': containers['page'],
                    'per_page': containers['per_page'],
                    'total': containers['total'],
                    'pages': containers['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching containers: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Document Management Endpoints
    @app.route('/api/v1/shipments/<shipment_id>/documents', methods=['POST'])
    @auth_required
    def upload_document(shipment_id):
        """Upload a document for a shipment"""
        try:
            if 'file' not in request.files:
                raise BadRequest("No file provided")
            
            file = request.files['file']
            if file.filename == '':
                raise BadRequest("No file selected")
            
            document_type = request.form.get('document_type', 'OTHER')
            description = request.form.get('description', '')
            
            document = document_service.upload_document(
                shipment_id=shipment_id,
                file=file,
                document_type=document_type,
                description=description,
                uploaded_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'document': document.to_dict(),
                'message': 'Document uploaded successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error uploading document: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/shipments/<shipment_id>/documents', methods=['GET'])
    @auth_required
    def get_documents(shipment_id):
        """Get documents for a shipment"""
        try:
            documents = document_service.get_documents(shipment_id, request.user_id)
            
            return jsonify({
                'success': True,
                'documents': [doc.to_dict() for doc in documents]
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching documents: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/documents/<document_id>/download', methods=['GET'])
    @auth_required
    def download_document(document_id):
        """Download a document"""
        try:
            return document_service.download_document(document_id, request.user_id)
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error downloading document: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Admin Endpoints
    @app.route('/api/v1/admin/bookings', methods=['GET'])
    @admin_required
    def admin_get_bookings():
        """Get all bookings (admin only)"""
        try:
            status = request.args.get('status')
            customer_id = request.args.get('customer_id')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)
            
            bookings = booking_engine.get_all_bookings(
                status=status,
                customer_id=customer_id,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'bookings': [booking.to_dict() for booking in bookings['items']],
                'pagination': {
                    'page': bookings['page'],
                    'per_page': bookings['per_page'],
                    'total': bookings['total'],
                    'pages': bookings['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching admin bookings: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/admin/shipments', methods=['GET'])
    @admin_required
    def admin_get_shipments():
        """Get all shipments (admin only)"""
        try:
            status = request.args.get('status')
            customer_id = request.args.get('customer_id')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)
            
            shipments = tracking_service.get_all_shipments(
                status=status,
                customer_id=customer_id,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'shipments': [shipment.to_dict() for shipment in shipments['items']],
                'pagination': {
                    'page': shipments['page'],
                    'per_page': shipments['per_page'],
                    'total': shipments['total'],
                    'pages': shipments['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching admin shipments: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/admin/shipments/<shipment_id>', methods=['PUT'])
    @admin_required
    def admin_update_shipment(shipment_id):
        """Update shipment details (admin only)"""
        try:
            data = request.get_json()
            
            shipment = tracking_service.update_shipment(
                shipment_id=shipment_id,
                updates=data
            )
            
            return jsonify({
                'success': True,
                'shipment': shipment.to_dict(),
                'message': 'Shipment updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error updating shipment: {str(e)}")
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
    port = int(os.environ.get('PORT', 8102))
    app.run(host='0.0.0.0', port=port, debug=True)
