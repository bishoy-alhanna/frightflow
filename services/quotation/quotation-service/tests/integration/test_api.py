"""
Integration tests for quotation service API endpoints.
"""
import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from src.main import create_app
from src.models.quotation import Quote, QuoteItem, PricingRule


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = 'sqlite:///:memory:'
    app.config['REDIS_URL'] = 'redis://localhost:6379/15'  # Test database
    app.config['AUTH_ENABLED'] = False
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_quote_request():
    """Sample quote request data."""
    return {
        'mode': 'SEA',
        'service': 'FCL',
        'origin': 'SGSIN',
        'destination': 'EGALY',
        'containers': [
            {'type': '40HC', 'count': 1}
        ],
        'cargo': {
            'weightKg': 8200,
            'volumeM3': 58
        },
        'accessorials': ['FUEL', 'PORT_FEES'],
        'customer_id': 'CUST123'
    }


@pytest.fixture
def sample_lcl_quote_request():
    """Sample LCL quote request data."""
    return {
        'mode': 'SEA',
        'service': 'LCL',
        'origin': 'SGSIN',
        'destination': 'USNYC',
        'cargo': {
            'weightKg': 1500,
            'volumeM3': 2.5
        },
        'accessorials': ['FUEL', 'DOCUMENTATION'],
        'customer_id': 'CUST456'
    }


class TestQuotationAPI:
    """Test cases for quotation API endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'quotation-service'
        assert 'version' in data
        assert 'timestamp' in data
    
    def test_ready_endpoint(self, client):
        """Test readiness check endpoint."""
        response = client.get('/ready')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ready'
        assert 'database' in data
    
    @patch('src.services.pricing_engine.PricingEngine.calculate_price')
    @patch('src.services.pdf_generator.PDFGenerator.generate_quote_pdf')
    def test_create_quote_fcl(self, mock_pdf, mock_pricing, client, sample_quote_request):
        """Test creating FCL quote."""
        # Mock pricing engine response
        mock_pricing.return_value = {
            'currency': 'USD',
            'base': 2400.0,
            'total': 2670.0,
            'surcharges': [
                {'code': 'FUEL', 'description': 'Fuel Surcharge', 'amount': 120.0, 'type': 'fixed'},
                {'code': 'PORT_FEES', 'description': 'Port Handling Fees', 'amount': 150.0, 'type': 'fixed'}
            ],
            'items': [
                {'description': 'SEA FCL - 1x40HC from SGSIN to EGALY', 'unit_price': 2400.0, 'type': 'BASE'},
                {'description': 'Fuel Surcharge', 'unit_price': 120.0, 'type': 'SURCHARGE'},
                {'description': 'Port Handling Fees', 'unit_price': 150.0, 'type': 'SURCHARGE'}
            ],
            'calculation_details': {'pricing_rule_id': 1}
        }
        
        # Mock PDF generation
        mock_pdf.return_value = 'quotes/2025/08/Q-ABC12345.pdf'
        
        response = client.post(
            '/api/v1/quotes',
            data=json.dumps(sample_quote_request),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        assert data['mode'] == 'SEA'
        assert data['service'] == 'FCL'
        assert data['origin'] == 'SGSIN'
        assert data['destination'] == 'EGALY'
        assert data['customer_id'] == 'CUST123'
        assert data['currency'] == 'USD'
        assert data['base_amount'] == 2400.0
        assert data['total_amount'] == 2670.0
        assert data['status'] == 'ISSUED'
        assert 'quote_id' in data
        assert 'valid_until' in data
        assert 'issued_at' in data
        assert len(data['items']) == 3
    
    @patch('src.services.pricing_engine.PricingEngine.calculate_price')
    @patch('src.services.pdf_generator.PDFGenerator.generate_quote_pdf')
    def test_create_quote_lcl(self, mock_pdf, mock_pricing, client, sample_lcl_quote_request):
        """Test creating LCL quote."""
        # Mock pricing engine response
        mock_pricing.return_value = {
            'currency': 'USD',
            'base': 800.0,
            'total': 995.0,
            'surcharges': [
                {'code': 'FUEL', 'description': 'Fuel Surcharge', 'amount': 120.0, 'type': 'fixed'},
                {'code': 'DOCUMENTATION', 'description': 'Documentation Fee', 'amount': 75.0, 'type': 'fixed'}
            ],
            'items': [
                {'description': 'SEA LCL freight from SGSIN to USNYC', 'unit_price': 800.0, 'type': 'BASE'},
                {'description': 'Fuel Surcharge', 'unit_price': 120.0, 'type': 'SURCHARGE'},
                {'description': 'Documentation Fee', 'unit_price': 75.0, 'type': 'SURCHARGE'}
            ],
            'calculation_details': {'pricing_rule_id': 2}
        }
        
        mock_pdf.return_value = 'quotes/2025/08/Q-XYZ789.pdf'
        
        response = client.post(
            '/api/v1/quotes',
            data=json.dumps(sample_lcl_quote_request),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        assert data['service'] == 'LCL'
        assert data['destination'] == 'USNYC'
        assert data['total_amount'] == 995.0
    
    def test_create_quote_validation_error(self, client):
        """Test quote creation with validation errors."""
        invalid_request = {
            'mode': 'INVALID',  # Invalid mode
            'service': 'FCL',
            # Missing required fields
        }
        
        response = client.post(
            '/api/v1/quotes',
            data=json.dumps(invalid_request),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'message' in data
    
    def test_create_quote_missing_content_type(self, client, sample_quote_request):
        """Test quote creation without content type header."""
        response = client.post(
            '/api/v1/quotes',
            data=json.dumps(sample_quote_request)
            # Missing content_type='application/json'
        )
        
        assert response.status_code == 400
    
    @patch('src.services.pricing_engine.PricingEngine.calculate_price')
    def test_create_quote_pricing_failure(self, mock_pricing, client, sample_quote_request):
        """Test quote creation when pricing engine fails."""
        mock_pricing.return_value = None  # Pricing failure
        
        response = client.post(
            '/api/v1/quotes',
            data=json.dumps(sample_quote_request),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_quote_idempotency(self, client, sample_quote_request):
        """Test quote creation idempotency."""
        idempotency_key = 'test-key-123'
        
        # First request
        response1 = client.post(
            '/api/v1/quotes',
            data=json.dumps(sample_quote_request),
            content_type='application/json',
            headers={'Idempotency-Key': idempotency_key}
        )
        
        # Second request with same key
        response2 = client.post(
            '/api/v1/quotes',
            data=json.dumps(sample_quote_request),
            content_type='application/json',
            headers={'Idempotency-Key': idempotency_key}
        )
        
        # Should return same result
        assert response1.status_code == 201
        assert response2.status_code == 200  # Cached response
        
        data1 = json.loads(response1.data)
        data2 = json.loads(response2.data)
        assert data1['quote_id'] == data2['quote_id']
    
    @patch('src.models.quotation.Quote.query')
    def test_get_quote_success(self, mock_query, client):
        """Test getting quote by ID."""
        # Mock quote object
        mock_quote = Mock()
        mock_quote.to_dict.return_value = {
            'quote_id': 'Q-TEST123',
            'customer_id': 'CUST123',
            'mode': 'SEA',
            'service': 'FCL',
            'origin': 'SGSIN',
            'destination': 'EGALY',
            'currency': 'USD',
            'base_amount': 2400.0,
            'total_amount': 2670.0,
            'status': 'ISSUED',
            'is_valid': True,
            'is_expired': False
        }
        
        mock_query.filter_by.return_value.first.return_value = mock_quote
        
        response = client.get('/api/v1/quotes/Q-TEST123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['quote_id'] == 'Q-TEST123'
        assert data['customer_id'] == 'CUST123'
    
    @patch('src.models.quotation.Quote.query')
    def test_get_quote_not_found(self, mock_query, client):
        """Test getting non-existent quote."""
        mock_query.filter_by.return_value.first.return_value = None
        
        response = client.get('/api/v1/quotes/Q-NOTFOUND')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('src.models.quotation.Quote.query')
    def test_accept_quote_success(self, mock_query, client):
        """Test accepting a quote."""
        # Mock quote object
        mock_quote = Mock()
        mock_quote.can_be_accepted.return_value = True
        mock_quote.accept.return_value = True
        mock_quote.to_dict.return_value = {
            'quote_id': 'Q-TEST123',
            'status': 'ACCEPTED',
            'accepted_at': '2025-08-29T14:30:00Z'
        }
        
        mock_query.filter_by.return_value.first.return_value = mock_quote
        
        response = client.put('/api/v1/quotes/Q-TEST123/accept')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ACCEPTED'
        assert 'accepted_at' in data
    
    @patch('src.models.quotation.Quote.query')
    def test_accept_quote_invalid(self, mock_query, client):
        """Test accepting an invalid quote."""
        # Mock expired quote
        mock_quote = Mock()
        mock_quote.can_be_accepted.return_value = False
        mock_quote.is_expired = True
        
        mock_query.filter_by.return_value.first.return_value = mock_quote
        
        response = client.put('/api/v1/quotes/Q-EXPIRED/accept')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'expired' in data['message'].lower()
    
    @patch('src.models.quotation.Quote.query')
    def test_accept_quote_not_found(self, mock_query, client):
        """Test accepting non-existent quote."""
        mock_query.filter_by.return_value.first.return_value = None
        
        response = client.put('/api/v1/quotes/Q-NOTFOUND/accept')
        
        assert response.status_code == 404
    
    @patch('src.models.quotation.Quote.query')
    def test_list_quotes(self, mock_query, client):
        """Test listing quotes with pagination."""
        # Mock paginated results
        mock_pagination = Mock()
        mock_pagination.items = [
            Mock(to_dict=lambda: {'quote_id': 'Q-TEST1', 'status': 'ISSUED'}),
            Mock(to_dict=lambda: {'quote_id': 'Q-TEST2', 'status': 'ACCEPTED'})
        ]
        mock_pagination.page = 1
        mock_pagination.per_page = 20
        mock_pagination.total = 2
        mock_pagination.pages = 1
        mock_pagination.has_prev = False
        mock_pagination.has_next = False
        mock_pagination.prev_num = None
        mock_pagination.next_num = None
        
        mock_query.paginate.return_value = mock_pagination
        
        response = client.get('/api/v1/quotes?page=1&per_page=20')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'items' in data
        assert 'pagination' in data
        assert len(data['items']) == 2
        assert data['pagination']['page'] == 1
        assert data['pagination']['total'] == 2
    
    @patch('src.models.quotation.Quote.query')
    def test_list_quotes_with_filters(self, mock_query, client):
        """Test listing quotes with filters."""
        mock_pagination = Mock()
        mock_pagination.items = []
        mock_pagination.page = 1
        mock_pagination.per_page = 20
        mock_pagination.total = 0
        mock_pagination.pages = 0
        mock_pagination.has_prev = False
        mock_pagination.has_next = False
        mock_pagination.prev_num = None
        mock_pagination.next_num = None
        
        mock_query.filter.return_value.paginate.return_value = mock_pagination
        
        response = client.get('/api/v1/quotes?customer_id=CUST123&status=ISSUED')
        
        assert response.status_code == 200
        # Verify that filters were applied
        mock_query.filter.assert_called()
    
    @patch('src.services.storage.ObjectStorage.generate_presigned_url')
    @patch('src.models.quotation.Quote.query')
    def test_get_quote_pdf(self, mock_query, mock_storage, client):
        """Test getting quote PDF download URL."""
        # Mock quote object
        mock_quote = Mock()
        mock_quote.quote_id = 'Q-TEST123'
        mock_quote.pdf_path = 'quotes/2025/08/Q-TEST123.pdf'
        
        mock_query.filter_by.return_value.first.return_value = mock_quote
        
        # Mock storage service
        mock_storage.return_value = 'https://storage.example.com/quotes/2025/08/Q-TEST123.pdf?signature=...'
        
        response = client.get('/api/v1/quotes/Q-TEST123/pdf')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'download_url' in data
        assert 'expires_in' in data
        assert data['expires_in'] == 86400  # 24 hours
    
    @patch('src.models.quotation.Quote.query')
    def test_get_quote_pdf_not_found(self, mock_query, client):
        """Test getting PDF for non-existent quote."""
        mock_query.filter_by.return_value.first.return_value = None
        
        response = client.get('/api/v1/quotes/Q-NOTFOUND/pdf')
        
        assert response.status_code == 404
    
    def test_invalid_quote_id_format(self, client):
        """Test API with invalid quote ID format."""
        response = client.get('/api/v1/quotes/INVALID-ID')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'invalid' in data['message'].lower()
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options('/api/v1/quotes')
        
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers
    
    def test_rate_limiting(self, client, sample_quote_request):
        """Test rate limiting functionality."""
        # Make multiple requests rapidly
        responses = []
        for i in range(105):  # Exceed rate limit of 100/min
            response = client.post(
                '/api/v1/quotes',
                data=json.dumps(sample_quote_request),
                content_type='application/json'
            )
            responses.append(response)
            if response.status_code == 429:
                break
        
        # Should eventually get rate limited
        assert any(r.status_code == 429 for r in responses)
        
        # Rate limited response should have Retry-After header
        rate_limited_response = next(r for r in responses if r.status_code == 429)
        assert 'Retry-After' in rate_limited_response.headers
    
    def test_request_correlation_id(self, client):
        """Test that correlation ID is included in responses."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert 'X-Correlation-ID' in response.headers
        
        # Correlation ID should be a valid UUID format
        correlation_id = response.headers['X-Correlation-ID']
        assert len(correlation_id) == 36  # UUID length
        assert correlation_id.count('-') == 4  # UUID format

