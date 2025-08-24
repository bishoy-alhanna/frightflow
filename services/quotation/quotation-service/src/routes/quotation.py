"""
Quotation service API routes.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal
from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import SQLAlchemyError

from shared.database import db, db_transaction
from shared.cache import cache, cached
from shared.events import publish_event, EventTypes, Topics
from shared.auth import require_auth, get_current_user
from src.models.quotation import Quote, PricingRule, QuoteItem
from src.services.pricing_engine import PricingEngine
from src.services.pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

quotation_bp = Blueprint('quotation', __name__)

# Initialize services
pricing_engine = PricingEngine()
pdf_generator = PDFGenerator()


@quotation_bp.route('/quotes', methods=['POST'])
def create_quote():
    """
    Create a new quote with dynamic pricing.
    
    Request body example:
    {
        "mode": "SEA",
        "service": "FCL",
        "origin": "SGSIN",
        "destination": "EGALY",
        "containers": [{"type": "40HC", "count": 1}],
        "cargo": {"weightKg": 8200, "volumeM3": 58},
        "accessorials": ["FUEL", "PORT_FEES"],
        "customer_id": "CUST123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['mode', 'service', 'origin', 'destination']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Field {field} is required'}), 400
        
        # Check for idempotency key
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key:
            existing_quote = cache.get(f"quote_idempotency:{idempotency_key}")
            if existing_quote:
                logger.info(f"Returning cached quote for idempotency key: {idempotency_key}")
                return jsonify(existing_quote), 200
        
        # Calculate pricing
        pricing_result = pricing_engine.calculate_price(data)
        if not pricing_result:
            return jsonify({'error': 'Unable to calculate pricing'}), 500
        
        # Create quote
        with db_transaction():
            quote = Quote(
                customer_id=data.get('customer_id'),
                mode=data['mode'].upper(),
                service=data['service'].upper(),
                origin=data['origin'].upper(),
                destination=data['destination'].upper(),
                currency=pricing_result.get('currency', 'USD'),
                base_amount=Decimal(str(pricing_result['base'])),
                total_amount=Decimal(str(pricing_result['total'])),
                valid_until=datetime.utcnow() + timedelta(days=7)
            )
            
            # Set cargo details
            quote.set_cargo_details(data.get('cargo', {}))
            quote.set_containers(data.get('containers', []))
            quote.set_accessorials(data.get('accessorials', []))
            quote.set_surcharges(pricing_result.get('surcharges', []))
            
            # Create quote items
            for item_data in pricing_result.get('items', []):
                item = QuoteItem(
                    quote=quote,
                    description=item_data['description'],
                    quantity=Decimal(str(item_data.get('quantity', 1))),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    item_type=item_data.get('type', 'BASE'),
                    currency=quote.currency
                )
                item.calculate_total()
                db.session.add(item)
            
            # Issue the quote
            quote.issue()
            db.session.add(quote)
            db.session.commit()
        
        # Generate PDF asynchronously (in background)
        try:
            pdf_path = pdf_generator.generate_quote_pdf(quote)
            if pdf_path:
                quote.pdf_path = pdf_path
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to generate PDF for quote {quote.quote_id}: {e}")
        
        # Publish event
        try:
            publish_event(
                topic=Topics.QUOTATIONS,
                event_type=EventTypes.QUOTE_ISSUED,
                data={
                    'quote_id': quote.quote_id,
                    'customer_id': quote.customer_id,
                    'total_amount': float(quote.total_amount),
                    'currency': quote.currency,
                    'valid_until': quote.valid_until.isoformat()
                },
                source_service='quotation-service'
            )
        except Exception as e:
            logger.error(f"Failed to publish quote issued event: {e}")
        
        # Cache result for idempotency
        result = quote.to_dict()
        if idempotency_key:
            cache.set(f"quote_idempotency:{idempotency_key}", result, ttl=3600)
        
        logger.info(f"Created quote {quote.quote_id} for customer {quote.customer_id}")
        return jsonify(result), 201
    
    except SQLAlchemyError as e:
        logger.error(f"Database error creating quote: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logger.error(f"Unexpected error creating quote: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@quotation_bp.route('/quotes/<quote_id>', methods=['GET'])
def get_quote(quote_id: str):
    """Get quote by ID."""
    try:
        # Try cache first
        cached_quote = cache.get(f"quote:{quote_id}")
        if cached_quote:
            logger.debug(f"Cache hit for quote: {quote_id}")
            return jsonify(cached_quote), 200
        
        # Query database
        quote = Quote.query.filter_by(quote_id=quote_id).first()
        if not quote:
            return jsonify({'error': 'Quote not found'}), 404
        
        # Check access permissions (simplified)
        current_user = get_current_user()
        if current_user and quote.customer_id and quote.customer_id != current_user.user_id:
            if not current_user.has_any_role(['admin', 'ops', 'sales']):
                return jsonify({'error': 'Access denied'}), 403
        
        result = quote.to_dict()
        
        # Cache the result
        cache.set(f"quote:{quote_id}", result, ttl=300)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error retrieving quote {quote_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@quotation_bp.route('/quotes/<quote_id>/accept', methods=['PUT'])
def accept_quote(quote_id: str):
    """Accept a quote."""
    try:
        quote = Quote.query.filter_by(quote_id=quote_id).first()
        if not quote:
            return jsonify({'error': 'Quote not found'}), 404
        
        # Check if quote is valid
        if not quote.is_valid():
            return jsonify({'error': 'Quote is expired or invalid'}), 400
        
        # Check access permissions
        current_user = get_current_user()
        if current_user and quote.customer_id and quote.customer_id != current_user.user_id:
            if not current_user.has_any_role(['admin', 'ops', 'sales']):
                return jsonify({'error': 'Access denied'}), 403
        
        # Accept the quote
        with db_transaction():
            quote.accept()
            db.session.commit()
        
        # Publish event
        try:
            publish_event(
                topic=Topics.QUOTATIONS,
                event_type=EventTypes.QUOTE_ACCEPTED,
                data={
                    'quote_id': quote.quote_id,
                    'customer_id': quote.customer_id,
                    'total_amount': float(quote.total_amount),
                    'currency': quote.currency,
                    'accepted_at': quote.accepted_at.isoformat()
                },
                source_service='quotation-service'
            )
        except Exception as e:
            logger.error(f"Failed to publish quote accepted event: {e}")
        
        # Clear cache
        cache.delete(f"quote:{quote_id}")
        
        logger.info(f"Quote {quote_id} accepted")
        return jsonify(quote.to_dict()), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error accepting quote {quote_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@quotation_bp.route('/quotes/<quote_id>/pdf', methods=['GET'])
def get_quote_pdf(quote_id: str):
    """Get pre-signed URL for quote PDF."""
    try:
        quote = Quote.query.filter_by(quote_id=quote_id).first()
        if not quote:
            return jsonify({'error': 'Quote not found'}), 404
        
        # Check access permissions
        current_user = get_current_user()
        if current_user and quote.customer_id and quote.customer_id != current_user.user_id:
            if not current_user.has_any_role(['admin', 'ops', 'sales']):
                return jsonify({'error': 'Access denied'}), 403
        
        if not quote.pdf_path:
            # Generate PDF if not exists
            try:
                pdf_path = pdf_generator.generate_quote_pdf(quote)
                if pdf_path:
                    quote.pdf_path = pdf_path
                    db.session.commit()
                else:
                    return jsonify({'error': 'Failed to generate PDF'}), 500
            except Exception as e:
                logger.error(f"Failed to generate PDF for quote {quote_id}: {e}")
                return jsonify({'error': 'Failed to generate PDF'}), 500
        
        # Get pre-signed URL
        from shared.storage import storage
        download_url = storage.get_presigned_download_url(
            quote.pdf_path,
            expires=timedelta(hours=24)
        )
        
        if not download_url:
            return jsonify({'error': 'Failed to generate download URL'}), 500
        
        return jsonify({
            'download_url': download_url,
            'expires_in': 24 * 3600  # 24 hours in seconds
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting PDF for quote {quote_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@quotation_bp.route('/quotes', methods=['GET'])
def list_quotes():
    """List quotes with pagination and filtering."""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        customer_id = request.args.get('customer_id')
        status = request.args.get('status')
        
        # Build query
        query = Quote.query
        
        # Apply filters
        if customer_id:
            query = query.filter(Quote.customer_id == customer_id)
        if status:
            query = query.filter(Quote.status == status.upper())
        
        # Check access permissions
        current_user = get_current_user()
        if current_user and not current_user.has_any_role(['admin', 'ops', 'sales']):
            # Regular users can only see their own quotes
            if current_user.user_id:
                query = query.filter(Quote.customer_id == current_user.user_id)
            else:
                return jsonify({'error': 'Access denied'}), 403
        
        # Order by creation date (newest first)
        query = query.order_by(Quote.created_at.desc())
        
        # Paginate
        from shared.database import PaginationHelper
        result = PaginationHelper.paginate(query, page, per_page)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error listing quotes: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@quotation_bp.route('/pricing-rules', methods=['GET'])
@require_auth
def list_pricing_rules():
    """List pricing rules (admin/ops only)."""
    try:
        current_user = get_current_user()
        if not current_user.has_any_role(['admin', 'ops']):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        service = request.args.get('service')
        lane_key = request.args.get('lane_key')
        
        # Build query
        query = PricingRule.query.filter(PricingRule.is_active == True)
        
        if service:
            query = query.filter(PricingRule.service == service.upper())
        if lane_key:
            query = query.filter(PricingRule.lane_key == lane_key.upper())
        
        # Order by creation date
        query = query.order_by(PricingRule.created_at.desc())
        
        # Paginate
        from shared.database import PaginationHelper
        result = PaginationHelper.paginate(query, page, per_page)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error listing pricing rules: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@quotation_bp.route('/pricing-rules', methods=['POST'])
@require_auth
def create_pricing_rule():
    """Create a new pricing rule (admin only)."""
    try:
        current_user = get_current_user()
        if not current_user.has_role('admin'):
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # Validate required fields
        required_fields = ['service', 'lane_key', 'formula']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Field {field} is required'}), 400
        
        # Create pricing rule
        with db_transaction():
            rule = PricingRule(
                service=data['service'].upper(),
                lane_key=data['lane_key'].upper(),
                currency=data.get('currency', 'USD'),
                effective_from=datetime.fromisoformat(data['effective_from']) if data.get('effective_from') else datetime.utcnow(),
                effective_to=datetime.fromisoformat(data['effective_to']) if data.get('effective_to') else None
            )
            rule.set_formula(data['formula'])
            
            db.session.add(rule)
            db.session.commit()
        
        # Clear pricing cache
        cache.delete(f"pricing_rules:{rule.service}:{rule.lane_key}")
        
        logger.info(f"Created pricing rule for {rule.service} {rule.lane_key}")
        return jsonify(rule.to_dict()), 201
    
    except Exception as e:
        logger.error(f"Error creating pricing rule: {e}")
        return jsonify({'error': 'Internal server error'}), 500

