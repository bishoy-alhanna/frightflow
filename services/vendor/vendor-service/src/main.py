import os
import sys
import json
import uuid
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, request, jsonify, Response
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
from models.vendor import Vendor, VendorContact, VendorService, VendorRating
from models.contract import Contract, ContractTerm, ContractAmendment
from services.vendor_service import VendorService as VendorServiceClass
from services.contract_service import ContractService
from services.performance_service import PerformanceService

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
    
    vendor_service = VendorServiceClass(db, cache, event_producer)
    contract_service = ContractService(db, cache, event_producer)
    performance_service = PerformanceService(db, cache, event_producer)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'vendor-service',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Vendor Management Endpoints
    @app.route('/api/v1/vendors', methods=['POST'])
    @admin_required
    def create_vendor():
        """Create a new vendor"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['company_name', 'contact_name', 'email', 'service_types']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            vendor = vendor_service.create_vendor(
                company_name=data['company_name'],
                contact_name=data['contact_name'],
                email=data['email'],
                phone=data.get('phone'),
                address=data.get('address'),
                city=data.get('city'),
                country=data.get('country'),
                postal_code=data.get('postal_code'),
                tax_id=data.get('tax_id'),
                service_types=data['service_types'],
                capabilities=data.get('capabilities', []),
                certifications=data.get('certifications', []),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'vendor': vendor.to_dict(),
                'message': 'Vendor created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Conflict as e:
            return jsonify({'error': str(e)}), 409
        except Exception as e:
            app.logger.error(f"Error creating vendor: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/vendors', methods=['GET'])
    @auth_required
    def get_vendors():
        """Get vendors with filtering and pagination"""
        try:
            search = request.args.get('search', '')
            status = request.args.get('status')
            service_type = request.args.get('service_type')
            country = request.args.get('country')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            vendors = vendor_service.get_vendors(
                search=search,
                status=status,
                service_type=service_type,
                country=country,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'vendors': [vendor.to_dict() for vendor in vendors['items']],
                'pagination': {
                    'page': vendors['page'],
                    'per_page': vendors['per_page'],
                    'total': vendors['total'],
                    'pages': vendors['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching vendors: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/vendors/<vendor_id>', methods=['GET'])
    @auth_required
    def get_vendor(vendor_id):
        """Get a specific vendor by ID"""
        try:
            vendor = vendor_service.get_vendor(vendor_id)
            if not vendor:
                raise NotFound("Vendor not found")
            
            # Get vendor performance metrics
            performance = performance_service.get_vendor_performance(vendor_id)
            
            return jsonify({
                'success': True,
                'vendor': vendor.to_dict(),
                'performance': performance
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching vendor: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/vendors/<vendor_id>', methods=['PUT'])
    @admin_required
    def update_vendor(vendor_id):
        """Update vendor information"""
        try:
            data = request.get_json()
            
            vendor = vendor_service.update_vendor(
                vendor_id=vendor_id,
                updates=data,
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'vendor': vendor.to_dict(),
                'message': 'Vendor updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error updating vendor: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/vendors/<vendor_id>/status', methods=['PUT'])
    @admin_required
    def update_vendor_status(vendor_id):
        """Update vendor status"""
        try:
            data = request.get_json()
            
            if 'status' not in data:
                raise BadRequest("Missing required field: status")
            
            vendor = vendor_service.update_vendor_status(
                vendor_id=vendor_id,
                status=data['status'],
                reason=data.get('reason'),
                updated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'vendor': vendor.to_dict(),
                'message': 'Vendor status updated successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error updating vendor status: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Vendor Rating Endpoints
    @app.route('/api/v1/vendors/<vendor_id>/ratings', methods=['POST'])
    @auth_required
    def create_vendor_rating(vendor_id):
        """Create a rating for a vendor"""
        try:
            data = request.get_json()
            
            required_fields = ['shipment_id', 'overall_rating']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            rating = vendor_service.create_vendor_rating(
                vendor_id=vendor_id,
                shipment_id=data['shipment_id'],
                overall_rating=data['overall_rating'],
                quality_rating=data.get('quality_rating'),
                timeliness_rating=data.get('timeliness_rating'),
                communication_rating=data.get('communication_rating'),
                cost_rating=data.get('cost_rating'),
                comments=data.get('comments'),
                rated_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'rating': rating.to_dict(),
                'message': 'Rating created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error creating vendor rating: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Contract Management Endpoints
    @app.route('/api/v1/contracts', methods=['POST'])
    @admin_required
    def create_contract():
        """Create a new contract"""
        try:
            data = request.get_json()
            
            required_fields = ['vendor_id', 'contract_type', 'start_date', 'end_date']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            contract = contract_service.create_contract(
                vendor_id=data['vendor_id'],
                contract_type=data['contract_type'],
                title=data.get('title'),
                description=data.get('description'),
                start_date=data['start_date'],
                end_date=data['end_date'],
                value=data.get('value'),
                currency=data.get('currency', 'USD'),
                payment_terms=data.get('payment_terms'),
                terms=data.get('terms', []),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'contract': contract.to_dict(),
                'message': 'Contract created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error creating contract: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/contracts', methods=['GET'])
    @auth_required
    def get_contracts():
        """Get contracts with filtering and pagination"""
        try:
            vendor_id = request.args.get('vendor_id')
            status = request.args.get('status')
            contract_type = request.args.get('contract_type')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            contracts = contract_service.get_contracts(
                vendor_id=vendor_id,
                status=status,
                contract_type=contract_type,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'contracts': [contract.to_dict() for contract in contracts['items']],
                'pagination': {
                    'page': contracts['page'],
                    'per_page': contracts['per_page'],
                    'total': contracts['total'],
                    'pages': contracts['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching contracts: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/contracts/<contract_id>', methods=['GET'])
    @auth_required
    def get_contract(contract_id):
        """Get a specific contract by ID"""
        try:
            contract = contract_service.get_contract(contract_id)
            if not contract:
                raise NotFound("Contract not found")
            
            return jsonify({
                'success': True,
                'contract': contract.to_dict()
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching contract: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/contracts/<contract_id>/amendments', methods=['POST'])
    @admin_required
    def create_contract_amendment(contract_id):
        """Create an amendment to a contract"""
        try:
            data = request.get_json()
            
            required_fields = ['amendment_type', 'description']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            amendment = contract_service.create_contract_amendment(
                contract_id=contract_id,
                amendment_type=data['amendment_type'],
                description=data['description'],
                changes=data.get('changes', {}),
                effective_date=data.get('effective_date'),
                created_by=request.user_id
            )
            
            return jsonify({
                'success': True,
                'amendment': amendment.to_dict(),
                'message': 'Contract amendment created successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error creating contract amendment: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Performance and Analytics Endpoints
    @app.route('/api/v1/vendors/<vendor_id>/performance', methods=['GET'])
    @auth_required
    def get_vendor_performance(vendor_id):
        """Get vendor performance metrics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            performance = performance_service.get_vendor_performance(
                vendor_id=vendor_id,
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'performance': performance
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            app.logger.error(f"Error fetching vendor performance: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/analytics/vendors', methods=['GET'])
    @admin_required
    def get_vendor_analytics():
        """Get vendor analytics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            analytics = vendor_service.get_vendor_analytics(
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching vendor analytics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/analytics/contracts', methods=['GET'])
    @admin_required
    def get_contract_analytics():
        """Get contract analytics"""
        try:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            analytics = contract_service.get_contract_analytics(
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching contract analytics: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Vendor Onboarding Endpoints
    @app.route('/api/v1/vendors/onboard', methods=['POST'])
    def vendor_onboarding():
        """Public endpoint for vendor self-registration"""
        try:
            data = request.get_json()
            
            required_fields = ['company_name', 'contact_name', 'email', 'phone', 'service_types']
            for field in required_fields:
                if field not in data:
                    raise BadRequest(f"Missing required field: {field}")
            
            application = vendor_service.create_onboarding_application(
                company_name=data['company_name'],
                contact_name=data['contact_name'],
                email=data['email'],
                phone=data['phone'],
                address=data.get('address'),
                city=data.get('city'),
                country=data.get('country'),
                service_types=data['service_types'],
                capabilities=data.get('capabilities', []),
                certifications=data.get('certifications', []),
                business_license=data.get('business_license'),
                insurance_info=data.get('insurance_info'),
                references=data.get('references', [])
            )
            
            return jsonify({
                'success': True,
                'application': application,
                'message': 'Onboarding application submitted successfully'
            }), 201
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error creating onboarding application: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/vendors/applications', methods=['GET'])
    @admin_required
    def get_onboarding_applications():
        """Get vendor onboarding applications"""
        try:
            status = request.args.get('status', 'PENDING')
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            applications = vendor_service.get_onboarding_applications(
                status=status,
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'success': True,
                'applications': applications['items'],
                'pagination': {
                    'page': applications['page'],
                    'per_page': applications['per_page'],
                    'total': applications['total'],
                    'pages': applications['pages']
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching onboarding applications: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/v1/vendors/applications/<application_id>/approve', methods=['POST'])
    @admin_required
    def approve_vendor_application(application_id):
        """Approve a vendor onboarding application"""
        try:
            data = request.get_json() or {}
            
            vendor = vendor_service.approve_onboarding_application(
                application_id=application_id,
                approved_by=request.user_id,
                notes=data.get('notes')
            )
            
            return jsonify({
                'success': True,
                'vendor': vendor.to_dict(),
                'message': 'Vendor application approved successfully'
            })
            
        except NotFound as e:
            return jsonify({'error': str(e)}), 404
        except Conflict as e:
            return jsonify({'error': str(e)}), 409
        except Exception as e:
            app.logger.error(f"Error approving vendor application: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    # Export Endpoints
    @app.route('/api/v1/vendors/export', methods=['GET'])
    @admin_required
    def export_vendors():
        """Export vendors to CSV"""
        try:
            filters = {
                'status': request.args.get('status'),
                'service_type': request.args.get('service_type'),
                'country': request.args.get('country')
            }
            
            csv_data = vendor_service.export_vendors(filters)
            
            response = Response(
                csv_data,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=vendors.csv'}
            )
            
            return response
            
        except Exception as e:
            app.logger.error(f"Error exporting vendors: {str(e)}")
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
    port = int(os.environ.get('PORT', 8104))
    app.run(host='0.0.0.0', port=port, debug=True)
