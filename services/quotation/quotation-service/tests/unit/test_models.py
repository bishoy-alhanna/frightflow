"""
Unit tests for quotation models.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from src.models.quotation import Quote, QuoteItem, PricingRule


class TestQuote:
    """Test cases for Quote model."""
    
    def test_quote_creation(self):
        """Test quote object creation."""
        quote = Quote(
            quote_id='Q-TEST123',
            customer_id='CUST123',
            mode='SEA',
            service='FCL',
            origin='SGSIN',
            destination='EGALY',
            route_key='SGSIN-EGALY',
            currency='USD',
            base_amount=Decimal('2400.00'),
            total_amount=Decimal('2520.00'),
            status='DRAFT'
        )
        
        assert quote.quote_id == 'Q-TEST123'
        assert quote.customer_id == 'CUST123'
        assert quote.mode == 'SEA'
        assert quote.service == 'FCL'
        assert quote.origin == 'SGSIN'
        assert quote.destination == 'EGALY'
        assert quote.route_key == 'SGSIN-EGALY'
        assert quote.currency == 'USD'
        assert quote.base_amount == Decimal('2400.00')
        assert quote.total_amount == Decimal('2520.00')
        assert quote.status == 'DRAFT'
    
    def test_quote_is_valid_property(self):
        """Test quote is_valid property."""
        # Valid quote (not expired, status is ISSUED)
        valid_quote = Quote(
            quote_id='Q-VALID123',
            status='ISSUED',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        assert valid_quote.is_valid is True
        
        # Invalid quote (expired)
        expired_quote = Quote(
            quote_id='Q-EXPIRED123',
            status='ISSUED',
            valid_until=datetime.utcnow() - timedelta(days=1)
        )
        assert expired_quote.is_valid is False
        
        # Invalid quote (wrong status)
        draft_quote = Quote(
            quote_id='Q-DRAFT123',
            status='DRAFT',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        assert draft_quote.is_valid is False
    
    def test_quote_is_expired_property(self):
        """Test quote is_expired property."""
        # Not expired
        valid_quote = Quote(
            quote_id='Q-VALID123',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        assert valid_quote.is_expired is False
        
        # Expired
        expired_quote = Quote(
            quote_id='Q-EXPIRED123',
            valid_until=datetime.utcnow() - timedelta(days=1)
        )
        assert expired_quote.is_expired is True
        
        # No expiry date
        no_expiry_quote = Quote(
            quote_id='Q-NOEXPIRY123',
            valid_until=None
        )
        assert no_expiry_quote.is_expired is False
    
    def test_quote_can_be_accepted(self):
        """Test quote can_be_accepted method."""
        # Can be accepted (valid and issued)
        valid_quote = Quote(
            quote_id='Q-VALID123',
            status='ISSUED',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        assert valid_quote.can_be_accepted() is True
        
        # Cannot be accepted (expired)
        expired_quote = Quote(
            quote_id='Q-EXPIRED123',
            status='ISSUED',
            valid_until=datetime.utcnow() - timedelta(days=1)
        )
        assert expired_quote.can_be_accepted() is False
        
        # Cannot be accepted (already accepted)
        accepted_quote = Quote(
            quote_id='Q-ACCEPTED123',
            status='ACCEPTED',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        assert accepted_quote.can_be_accepted() is False
        
        # Cannot be accepted (draft status)
        draft_quote = Quote(
            quote_id='Q-DRAFT123',
            status='DRAFT',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        assert draft_quote.can_be_accepted() is False
    
    def test_quote_accept(self):
        """Test quote accept method."""
        quote = Quote(
            quote_id='Q-TEST123',
            status='ISSUED',
            valid_until=datetime.utcnow() + timedelta(days=7)
        )
        
        # Mock datetime.utcnow for consistent testing
        with patch('src.models.quotation.datetime') as mock_datetime:
            mock_now = datetime(2025, 8, 29, 10, 30, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            result = quote.accept()
            
            assert result is True
            assert quote.status == 'ACCEPTED'
            assert quote.accepted_at == mock_now
    
    def test_quote_accept_invalid(self):
        """Test quote accept method with invalid quote."""
        expired_quote = Quote(
            quote_id='Q-EXPIRED123',
            status='ISSUED',
            valid_until=datetime.utcnow() - timedelta(days=1)
        )
        
        result = expired_quote.accept()
        
        assert result is False
        assert expired_quote.status == 'ISSUED'  # Status unchanged
        assert expired_quote.accepted_at is None
    
    def test_quote_to_dict(self):
        """Test quote to_dict method."""
        quote = Quote(
            quote_id='Q-TEST123',
            customer_id='CUST123',
            mode='SEA',
            service='FCL',
            origin='SGSIN',
            destination='EGALY',
            route_key='SGSIN-EGALY',
            currency='USD',
            base_amount=Decimal('2400.00'),
            total_amount=Decimal('2520.00'),
            status='ISSUED',
            valid_until=datetime(2025, 9, 5, 23, 59, 59),
            issued_at=datetime(2025, 8, 29, 10, 30, 0),
            created_at=datetime(2025, 8, 29, 10, 30, 0),
            updated_at=datetime(2025, 8, 29, 10, 30, 0)
        )
        
        result = quote.to_dict()
        
        assert result['quote_id'] == 'Q-TEST123'
        assert result['customer_id'] == 'CUST123'
        assert result['mode'] == 'SEA'
        assert result['service'] == 'FCL'
        assert result['origin'] == 'SGSIN'
        assert result['destination'] == 'EGALY'
        assert result['route_key'] == 'SGSIN-EGALY'
        assert result['currency'] == 'USD'
        assert result['base_amount'] == 2400.0
        assert result['total_amount'] == 2520.0
        assert result['status'] == 'ISSUED'
        assert result['valid_until'] == '2025-09-05T23:59:59Z'
        assert result['issued_at'] == '2025-08-29T10:30:00Z'
        assert result['is_valid'] is True
        assert result['is_expired'] is False
    
    def test_quote_generate_id(self):
        """Test quote ID generation."""
        quote_id = Quote.generate_id()
        
        assert quote_id.startswith('Q-')
        assert len(quote_id) == 10  # Q- + 8 characters
        assert quote_id[2:].isalnum()  # Characters after Q- are alphanumeric
    
    def test_quote_generate_id_uniqueness(self):
        """Test that generated quote IDs are unique."""
        ids = set()
        for _ in range(100):
            quote_id = Quote.generate_id()
            assert quote_id not in ids
            ids.add(quote_id)


class TestQuoteItem:
    """Test cases for QuoteItem model."""
    
    def test_quote_item_creation(self):
        """Test quote item object creation."""
        item = QuoteItem(
            quote_id='Q-TEST123',
            description='SEA FCL - 1x40HC from SGSIN to EGALY',
            quantity=Decimal('1'),
            unit_price=Decimal('2400.00'),
            total_price=Decimal('2400.00'),
            item_type='BASE',
            currency='USD'
        )
        
        assert item.quote_id == 'Q-TEST123'
        assert item.description == 'SEA FCL - 1x40HC from SGSIN to EGALY'
        assert item.quantity == Decimal('1')
        assert item.unit_price == Decimal('2400.00')
        assert item.total_price == Decimal('2400.00')
        assert item.item_type == 'BASE'
        assert item.currency == 'USD'
    
    def test_quote_item_to_dict(self):
        """Test quote item to_dict method."""
        item = QuoteItem(
            quote_id='Q-TEST123',
            description='Fuel Surcharge',
            quantity=Decimal('1'),
            unit_price=Decimal('120.00'),
            total_price=Decimal('120.00'),
            item_type='SURCHARGE',
            currency='USD'
        )
        
        result = item.to_dict()
        
        assert result['description'] == 'Fuel Surcharge'
        assert result['quantity'] == 1.0
        assert result['unit_price'] == 120.0
        assert result['total_price'] == 120.0
        assert result['item_type'] == 'SURCHARGE'
        assert result['currency'] == 'USD'


class TestPricingRule:
    """Test cases for PricingRule model."""
    
    def test_pricing_rule_creation(self):
        """Test pricing rule object creation."""
        rule = PricingRule(
            service='FCL',
            lane_key='SGSIN-EGALY',
            formula={'base_rates': {'40HC': '2400'}},
            currency='USD',
            effective_from=datetime(2025, 1, 1),
            version=1,
            is_active=True
        )
        
        assert rule.service == 'FCL'
        assert rule.lane_key == 'SGSIN-EGALY'
        assert rule.formula == {'base_rates': {'40HC': '2400'}}
        assert rule.currency == 'USD'
        assert rule.effective_from == datetime(2025, 1, 1)
        assert rule.version == 1
        assert rule.is_active is True
    
    def test_pricing_rule_get_formula(self):
        """Test pricing rule get_formula method."""
        formula_dict = {
            'base_rates': {'40HC': '2400', '20GP': '1800'},
            'surcharges': {'FUEL': '120', 'PORT_FEES': '150'}
        }
        
        rule = PricingRule(
            service='FCL',
            lane_key='SGSIN-EGALY',
            formula=formula_dict,
            currency='USD'
        )
        
        result = rule.get_formula()
        
        assert result == formula_dict
        assert result['base_rates']['40HC'] == '2400'
        assert result['surcharges']['FUEL'] == '120'
    
    def test_pricing_rule_is_effective(self):
        """Test pricing rule is_effective method."""
        now = datetime.utcnow()
        
        # Effective rule (started in past, no end date)
        effective_rule = PricingRule(
            service='FCL',
            lane_key='SGSIN-EGALY',
            effective_from=now - timedelta(days=30),
            effective_to=None,
            is_active=True
        )
        assert effective_rule.is_effective() is True
        
        # Not yet effective (starts in future)
        future_rule = PricingRule(
            service='FCL',
            lane_key='SGSIN-EGALY',
            effective_from=now + timedelta(days=30),
            effective_to=None,
            is_active=True
        )
        assert future_rule.is_effective() is False
        
        # Expired rule (ended in past)
        expired_rule = PricingRule(
            service='FCL',
            lane_key='SGSIN-EGALY',
            effective_from=now - timedelta(days=60),
            effective_to=now - timedelta(days=30),
            is_active=True
        )
        assert expired_rule.is_effective() is False
        
        # Inactive rule
        inactive_rule = PricingRule(
            service='FCL',
            lane_key='SGSIN-EGALY',
            effective_from=now - timedelta(days=30),
            effective_to=None,
            is_active=False
        )
        assert inactive_rule.is_effective() is False
    
    def test_pricing_rule_to_dict(self):
        """Test pricing rule to_dict method."""
        rule = PricingRule(
            id=1,
            service='FCL',
            lane_key='SGSIN-EGALY',
            formula={'base_rates': {'40HC': '2400'}},
            currency='USD',
            effective_from=datetime(2025, 1, 1),
            effective_to=datetime(2025, 12, 31),
            version=1,
            is_active=True,
            created_at=datetime(2025, 8, 29, 10, 30, 0),
            updated_at=datetime(2025, 8, 29, 10, 30, 0)
        )
        
        result = rule.to_dict()
        
        assert result['id'] == 1
        assert result['service'] == 'FCL'
        assert result['lane_key'] == 'SGSIN-EGALY'
        assert result['formula'] == {'base_rates': {'40HC': '2400'}}
        assert result['currency'] == 'USD'
        assert result['effective_from'] == '2025-01-01T00:00:00Z'
        assert result['effective_to'] == '2025-12-31T00:00:00Z'
        assert result['version'] == 1
        assert result['is_active'] is True
        assert result['created_at'] == '2025-08-29T10:30:00Z'
        assert result['updated_at'] == '2025-08-29T10:30:00Z'

