import os
import sys
import json
import uuid
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
from shared.events import EventProducer
from shared.auth import auth_required, admin_required

# Import models and services
from models.customer import Customer, Contact, CustomerInteraction, CustomerNote
from models.lead import Lead, LeadSource, LeadStatus
from services.customer_service import CustomerService
from services.lead_service import LeadService
from services.interaction_service import InteractionService

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
    
    customer_service = CustomerService(db, cache, event_producer)
    lead_service = LeadService(db, cache, event_producer)
    interaction_service = InteractionService(db, cache, event_producer)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'crm-service',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Customer Management Endpoints
    @app.route('/api/v1/customers', methods=['POST'])
    @auth_required
    def create_customer():
        """Create a new customer"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['company_name', 'contact_name', 'email']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            # Create customer
            customer = customer_service.create_customer(
                company_name=data['company_name'],
                contact_name=data['contact_name'],
                email=data['email'],
                phone=data.get('phone'),
                address=data.get('address'),
                city=data.get('city'),
                country=data.get('country'),
                postal_code=data.get('postal_code'),
                tax_id=data.get('tax_id'),
                credit_limit=data.get('credit_limit', 0.0),
                payment_terms=data.get('payment_terms', 'NET_30'),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'customer': customer.to_dict(),
                'message': 'Customer created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Conflict as e:
            return jsonify({'error': str(e)}), 409
        except Exception as e:
            app.logger.error(f"Error creating customer: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/customers', methods=['GET'])
    @auth_required
    def get_customers():
        """Get customers with filtering and pagination"""
        try:
            # Get query parameters
            search = request.args.get('search', '')
            status = request.args.get('status')
            country = request.args.get('country')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            sort_by = request.args.get('sort_by', 'created_at')
            sort_order = request.args.get('sort_order', 'desc')
            
            customers = customer_service.get_customers(
                search=search,
                status=status,
                country=country,
                page=page,
                per_page=per_page,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            return jsonify({
                'success': True,
                'customers': [customer.to_dict() for customer in customers['items']],
                'pagination': {
                    'page': customers['page'],
                    'per_page': customers['per_page'],
                    'total': customers['total'],
                    'pages': customers['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching customers: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/customers/<customer_id>', methods=['GET'])
    @auth_required
    def get_customer(customer_id):
        """Get a specific customer by ID"""
        try:
            customer = customer_service.get_customer(customer_id)
            if not customer:
                raise NotFound("Customer not found")
            
            # Get customer statistics
            stats = customer_service.get_customer_stats(customer_id)
            
            return jsonify({
                'success': True,
                'customer': customer.to_dict(),
                'stats': stats
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching customer: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/customers/<customer_id>', methods=['PUT'])
    @auth_required
    def update_customer(customer_id):
        """Update customer information"""
        try:
            data = request.get_json()
            
            customer = customer_service.update_customer(
                customer_id=customer_id,
                updates=data,
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'customer': customer.to_dict(),
                'message': 'Customer updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error updating customer: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/customers/<customer_id>/status', methods=['PUT'])
    @admin_required
    def update_customer_status(customer_id):
        """Update customer status (admin only)"""
        try:
            data = request.get_json()
            
            if 'is_active' not in data:
                raise BadRequest("Missing required field: is_active")
            
            customer = customer_service.update_customer_status(
                customer_id=customer_id,
                is_active=data['is_active'],
                reason=data.get('reason'),
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'customer': customer.to_dict(),
                'message': 'Customer status updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error updating customer status: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Customer Interactions Endpoints
    @app.route('/api/v1/customers/<customer_id>/interactions', methods=['POST'])
    @auth_required
    def create_interaction():
        """Create a new customer interaction"""
        try:
            customer_id = request.view_args['customer_id']
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['type', 'subject', 'description']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            interaction = interaction_service.create_interaction(
                customer_id=customer_id,
                interaction_type=data['type'],
                subject=data['subject'],
                description=data['description'],
                contact_person=data.get('contact_person'),
                outcome=data.get('outcome'),
                follow_up_date=data.get('follow_up_date'),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'interaction': interaction.to_dict(),
                'message': 'Interaction created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error creating interaction: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/customers/<customer_id>/interactions', methods=['GET'])
    @auth_required
    def get_customer_interactions(customer_id):
        """Get interactions for a customer"""
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            interaction_type = request.args.get('type')
            
            interactions = interaction_service.get_customer_interactions(
                customer_id=customer_id,
                interaction_type=interaction_type,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'interactions': [interaction.to_dict() for interaction in interactions['items']],
                'pagination': {
                    'page': interactions['page'],
                    'per_page': interactions['per_page'],
                    'total': interactions['total'],
                    'pages': interactions['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching customer interactions: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Customer Notes Endpoints
    @app.route('/api/v1/customers/<customer_id>/notes', methods=['POST'])
    @auth_required
    def create_customer_note(customer_id):
        """Create a note for a customer"""
        try:
            data = request.get_json()
            
            if 'content' not in data:
                raise BadRequest("Missing required field: content")
            
            note = customer_service.create_customer_note(
                customer_id=customer_id,
                content=data['content'],
                is_private=data.get('is_private', False),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'note': note.to_dict(),
                'message': 'Note created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error creating customer note: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/customers/<customer_id>/notes', methods=['GET'])
    @auth_required
    def get_customer_notes(customer_id):
        """Get notes for a customer"""
        try:
            notes = customer_service.get_customer_notes(
                customer_id=customer_id,
                user_id=request.user_id
            )
            
            return jsonify({
                'success': True,
                'notes': [note.to_dict() for note in notes]
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching customer notes: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Lead Management Endpoints
    @app.route('/api/v1/leads', methods=['POST'])
    @auth_required
    def create_lead():
        """Create a new lead"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['company_name', 'contact_name', 'email']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            lead = lead_service.create_lead(
                company_name=data['company_name'],
                contact_name=data['contact_name'],
                email=data['email'],
                phone=data.get('phone'),
                source=data.get('source', 'WEBSITE'),
                estimated_value=data.get('estimated_value'),
                notes=data.get('notes'),
                assigned_to=data.get('assigned_to'),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict(),
                'message': 'Lead created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error creating lead: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/leads', methods=['GET'])
    @auth_required
    def get_leads():
        """Get leads with filtering and pagination"""
        try:
            search = request.args.get('search', '')
            status = request.args.get('status')
            source = request.args.get('source')
            assigned_to = request.args.get('assigned_to')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            leads = lead_service.get_leads(
                search=search,
                status=status,
                source=source,
                assigned_to=assigned_to,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'leads': [lead.to_dict() for lead in leads['items']],
                'pagination': {
                    'page': leads['page'],
                    'per_page': leads['per_page'],
                    'total': leads['total'],
                    'pages': leads['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching leads: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/leads/<lead_id>', methods=['PUT'])
    @auth_required
    def update_lead(lead_id):
        """Update lead information"""
        try:
            data = request.get_json()
            
            lead = lead_service.update_lead(
                lead_id=lead_id,
                updates=data,
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'lead': lead.to_dict(),
                'message': 'Lead updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error updating lead: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/leads/<lead_id>/convert', methods=['POST'])
    @auth_required
    def convert_lead(lead_id):
        """Convert a lead to a customer"""
        try:
            data = request.get_json() or {}
            
            customer = lead_service.convert_lead_to_customer(
                lead_id=lead_id,
                additional_data=data,
                converted_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'customer': customer.to_dict(),
                'message': 'Lead converted to customer successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Conflict as e:
            return jsonify({'error': str(e)}), 409
        except Exception as e:
            app.logger.error(f"Error converting lead: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Analytics and Reports Endpoints
    @app.route('/api/v1/analytics/customers', methods=['GET'])
    @admin_required
    def get_customer_analytics():
        """Get customer analytics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            analytics = customer_service.get_customer_analytics(
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching customer analytics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/analytics/leads', methods=['GET'])
    @admin_required
    def get_lead_analytics():
        """Get lead analytics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            analytics = lead_service.get_lead_analytics(
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching lead analytics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Admin Endpoints
    @app.route('/api/v1/admin/customers/export', methods=['GET'])
    @admin_required
    def export_customers():
        """Export customers to CSV"""
        try:
            filters = {
                'status': request.args.get('status'),
                'country': request.args.get('country'),
                'date_from': request.args.get('date_from'),
                'date_to': request.args.get('date_to')
            }
            
            csv_data = customer_service.export_customers(filters)
            
            response = Response(
                csv_data,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=customers.csv'}
            )
            
            return response
            
        except Exception as e:
            app.logger.error(f"Error exporting customers: {str(e)}")
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
    port = int(os.environ.get('PORT', 8103))
    app.run(host='0.0.0.0', port=port, debug=True)
