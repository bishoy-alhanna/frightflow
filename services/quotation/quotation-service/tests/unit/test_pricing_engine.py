"""
Unit tests for the pricing engine.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))

from src.services.pricing_engine import PricingEngine
from src.models.quotation import PricingRule


class TestPricingEngine:
    """Test cases for PricingEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pricing_engine = PricingEngine()
    
    def test_calculate_fcl_price(self):
        """Test FCL pricing calculation."""
        quote_request = {
            'service': 'FCL',
            'containers': [
                {'type': '40HC', 'count': 1},
                {'type': '20GP', 'count': 2}
            ]
        }
        
        formula = {
            'base_rates': {
                '40HC': '2400',
                '20GP': '1800',
                'default': '2000'
            }
        }
        
        result = self.pricing_engine._calculate_fcl_price(quote_request, formula)
        
        # Expected: 1 * 2400 + 2 * 1800 = 6000
        assert result == Decimal('6000.00')
    
    def test_calculate_fcl_price_with_default_rate(self):
        """Test FCL pricing with default rate for unknown container type."""
        quote_request = {
            'service': 'FCL',
            'containers': [
                {'type': 'UNKNOWN', 'count': 1}
            ]
        }
        
        formula = {
            'base_rates': {
                '40HC': '2400',
                'default': '2000'
            }
        }
        
        result = self.pricing_engine._calculate_fcl_price(quote_request, formula)
        
        assert result == Decimal('2000.00')
    
    def test_calculate_lcl_price(self):
        """Test LCL pricing calculation."""
        quote_request = {
            'service': 'LCL',
            'cargo': {
                'weightKg': 1000,
                'volumeM3': 2.5
            }
        }
        
        formula = {
            'weight_rate': '0.8',
            'volume_rate': '120',
            'minimum_charge': '500'
        }
        
        result = self.pricing_engine._calculate_lcl_price(quote_request, formula)
        
        # Weight charge: 1000 * 0.8 = 800
        # Volume charge: 2.5 * 120 = 300
        # Take higher: max(800, 300, 500) = 800
        assert result == Decimal('800.00')
    
    def test_calculate_lcl_price_minimum_charge(self):
        """Test LCL pricing with minimum charge applied."""
        quote_request = {
            'service': 'LCL',
            'cargo': {
                'weightKg': 100,
                'volumeM3': 0.5
            }
        }
        
        formula = {
            'weight_rate': '0.8',
            'volume_rate': '120',
            'minimum_charge': '500'
        }
        
        result = self.pricing_engine._calculate_lcl_price(quote_request, formula)
        
        # Weight charge: 100 * 0.8 = 80
        # Volume charge: 0.5 * 120 = 60
        # Take higher: max(80, 60, 500) = 500 (minimum)
        assert result == Decimal('500.00')
    
    def test_calculate_air_price(self):
        """Test air freight pricing calculation."""
        quote_request = {
            'service': 'AIR',
            'cargo': {
                'weightKg': 200
            }
        }
        
        formula = {
            'rate_per_kg': '4.5',
            'minimum_charge': '300'
        }
        
        result = self.pricing_engine._calculate_air_price(quote_request, formula)
        
        # Weight charge: 200 * 4.5 = 900
        # Take higher: max(900, 300) = 900
        assert result == Decimal('900.00')
    
    def test_calculate_air_price_minimum_charge(self):
        """Test air freight pricing with minimum charge applied."""
        quote_request = {
            'service': 'AIR',
            'cargo': {
                'weightKg': 50
            }
        }
        
        formula = {
            'rate_per_kg': '4.5',
            'minimum_charge': '300'
        }
        
        result = self.pricing_engine._calculate_air_price(quote_request, formula)
        
        # Weight charge: 50 * 4.5 = 225
        # Take higher: max(225, 300) = 300 (minimum)
        assert result == Decimal('300.00')
    
    def test_calculate_surcharges(self):
        """Test surcharge calculation."""
        quote_request = {
            'origin': 'SGSIN',
            'destination': 'EGALY',
            'accessorials': ['FUEL', 'PORT_FEES', 'DOCUMENTATION']
        }
        
        pricing_rule = Mock()
        pricing_rule.get_formula.return_value = {
            'surcharges': {
                'FUEL': '120',
                'PORT_FEES': '150',
                'DOCUMENTATION': '75',
                'SECURITY': '50'
            }
        }
        
        with patch.object(self.pricing_engine, '_get_fuel_surcharge_rate', return_value=Decimal('120.00')):
            result = self.pricing_engine._calculate_surcharges(quote_request, pricing_rule)
        
        expected_surcharges = [
            {'code': 'FUEL', 'description': 'Fuel Surcharge', 'amount': 120.0, 'type': 'percentage'},
            {'code': 'PORT_FEES', 'description': 'Port Handling Fees', 'amount': 150.0, 'type': 'fixed'},
            {'code': 'DOCUMENTATION', 'description': 'Documentation Fee', 'amount': 75.0, 'type': 'fixed'}
        ]
        
        assert len(result) == 3
        assert result == expected_surcharges
    
    def test_get_fuel_surcharge_rate(self):
        """Test fuel surcharge rate calculation."""
        result = self.pricing_engine._get_fuel_surcharge_rate('SGSIN', 'EGALY')
        
        # Should return base rate * route multiplier
        # Base: 120.00, SGSIN-EGALY multiplier: 1.2
        expected = Decimal('144.00')
        assert result == expected
    
    def test_get_fuel_surcharge_rate_unknown_route(self):
        """Test fuel surcharge rate for unknown route."""
        result = self.pricing_engine._get_fuel_surcharge_rate('UNKNOWN', 'ROUTE')
        
        # Should return base rate * default multiplier (1.0)
        expected = Decimal('120.00')
        assert result == expected
    
    def test_create_line_items(self):
        """Test line item creation."""
        quote_request = {
            'mode': 'SEA',
            'service': 'FCL',
            'origin': 'SGSIN',
            'destination': 'EGALY',
            'containers': [{'type': '40HC', 'count': 1}]
        }
        
        base_price = Decimal('2400.00')
        surcharges = [
            {'code': 'FUEL', 'description': 'Fuel Surcharge', 'amount': 120.0, 'type': 'fixed'},
            {'code': 'PORT_FEES', 'description': 'Port Handling Fees', 'amount': 150.0, 'type': 'fixed'}
        ]
        
        result = self.pricing_engine._create_line_items(quote_request, base_price, surcharges)
        
        assert len(result) == 3  # 1 base + 2 surcharges
        
        # Check base item
        base_item = result[0]
        assert base_item['description'] == 'SEA FCL - 1x40HC from SGSIN to EGALY'
        assert base_item['unit_price'] == 2400.0
        assert base_item['type'] == 'BASE'
        
        # Check surcharge items
        fuel_item = result[1]
        assert fuel_item['description'] == 'Fuel Surcharge'
        assert fuel_item['unit_price'] == 120.0
        assert fuel_item['type'] == 'SURCHARGE'
    
    def test_get_service_description_fcl(self):
        """Test service description generation for FCL."""
        quote_request = {
            'mode': 'SEA',
            'service': 'FCL',
            'origin': 'SGSIN',
            'destination': 'EGALY',
            'containers': [
                {'type': '40HC', 'count': 1},
                {'type': '20GP', 'count': 2}
            ]
        }
        
        result = self.pricing_engine._get_service_description(quote_request)
        
        expected = 'SEA FCL - 1x40HC, 2x20GP from SGSIN to EGALY'
        assert result == expected
    
    def test_get_service_description_lcl(self):
        """Test service description generation for LCL."""
        quote_request = {
            'mode': 'SEA',
            'service': 'LCL',
            'origin': 'SGSIN',
            'destination': 'USNYC'
        }
        
        result = self.pricing_engine._get_service_description(quote_request)
        
        expected = 'SEA LCL freight from SGSIN to USNYC'
        assert result == expected
    
    def test_fallback_pricing_fcl(self):
        """Test fallback pricing for FCL service."""
        quote_request = {
            'service': 'FCL',
            'mode': 'SEA',
            'origin': 'SGSIN',
            'destination': 'EGALY'
        }
        
        result = self.pricing_engine._fallback_pricing(quote_request)
        
        assert result['currency'] == 'USD'
        assert result['base'] == 2000.00
        assert result['total'] == 2120.00  # 2000 + 120 fuel
        assert len(result['surcharges']) == 1
        assert result['surcharges'][0]['code'] == 'FUEL'
        assert result['calculation_details']['fallback'] is True
    
    def test_fallback_pricing_lcl(self):
        """Test fallback pricing for LCL service."""
        quote_request = {
            'service': 'LCL',
            'mode': 'SEA',
            'origin': 'SGSIN',
            'destination': 'EGALY'
        }
        
        result = self.pricing_engine._fallback_pricing(quote_request)
        
        assert result['base'] == 800.00
        assert result['total'] == 920.00  # 800 + 120 fuel
    
    def test_fallback_pricing_air(self):
        """Test fallback pricing for AIR service."""
        quote_request = {
            'service': 'AIR',
            'mode': 'AIR',
            'origin': 'SGSIN',
            'destination': 'EGALY'
        }
        
        result = self.pricing_engine._fallback_pricing(quote_request)
        
        assert result['base'] == 500.00
        assert result['total'] == 620.00  # 500 + 120 fuel
    
    def test_get_exchange_rate_same_currency(self):
        """Test exchange rate for same currency."""
        result = self.pricing_engine._get_exchange_rate('USD', 'USD')
        assert result == Decimal('1.0')
    
    def test_get_exchange_rate_known_pair(self):
        """Test exchange rate for known currency pair."""
        result = self.pricing_engine._get_exchange_rate('USD', 'EUR')
        assert result == Decimal('0.85')
    
    def test_get_exchange_rate_unknown_pair(self):
        """Test exchange rate for unknown currency pair."""
        result = self.pricing_engine._get_exchange_rate('USD', 'XYZ')
        assert result == Decimal('1.0')  # Default fallback
    
    @patch('src.services.pricing_engine.PricingRule')
    def test_get_pricing_rules_found(self, mock_pricing_rule):
        """Test getting pricing rules when rules exist."""
        mock_rule = Mock()
        mock_rule.currency = 'USD'
        mock_rule.get_formula.return_value = {'base_rates': {'40HC': '2400'}}
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_rule
        mock_pricing_rule.query = mock_query
        
        result = self.pricing_engine._get_pricing_rules('FCL', 'SGSIN-EGALY')
        
        assert result == mock_rule
    
    @patch('src.services.pricing_engine.PricingRule')
    def test_get_pricing_rules_not_found(self, mock_pricing_rule):
        """Test getting pricing rules when no rules exist."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        mock_pricing_rule.query = mock_query
        
        result = self.pricing_engine._get_pricing_rules('FCL', 'UNKNOWN-ROUTE')
        
        assert result is None
    
    @patch.object(PricingEngine, '_get_pricing_rules')
    @patch.object(PricingEngine, '_calculate_base_price')
    @patch.object(PricingEngine, '_calculate_surcharges')
    def test_calculate_price_success(self, mock_surcharges, mock_base_price, mock_rules):
        """Test successful price calculation."""
        # Setup mocks
        mock_rule = Mock()
        mock_rule.currency = 'USD'
        mock_rule.id = 1
        mock_rules.return_value = mock_rule
        
        mock_base_price.return_value = Decimal('2400.00')
        mock_surcharges.return_value = [
            {'code': 'FUEL', 'amount': 120.0, 'description': 'Fuel Surcharge'}
        ]
        
        quote_request = {
            'mode': 'SEA',
            'service': 'FCL',
            'origin': 'SGSIN',
            'destination': 'EGALY',
            'containers': [{'type': '40HC', 'count': 1}]
        }
        
        result = self.pricing_engine.calculate_price(quote_request)
        
        assert result is not None
        assert result['currency'] == 'USD'
        assert result['base'] == 2400.0
        assert result['total'] == 2520.0  # 2400 + 120
        assert len(result['surcharges']) == 1
        assert result['calculation_details']['pricing_rule_id'] == 1
    
    @patch.object(PricingEngine, '_get_pricing_rules')
    @patch.object(PricingEngine, '_fallback_pricing')
    def test_calculate_price_fallback(self, mock_fallback, mock_rules):
        """Test price calculation with fallback when no rules found."""
        mock_rules.return_value = None
        mock_fallback.return_value = {
            'currency': 'USD',
            'base': 2000.0,
            'total': 2120.0,
            'surcharges': [],
            'items': [],
            'calculation_details': {'fallback': True}
        }
        
        quote_request = {
            'mode': 'SEA',
            'service': 'FCL',
            'origin': 'UNKNOWN',
            'destination': 'ROUTE'
        }
        
        result = self.pricing_engine.calculate_price(quote_request)
        
        assert result is not None
        assert result['calculation_details']['fallback'] is True
        mock_fallback.assert_called_once_with(quote_request)
    
    def test_calculate_price_exception_handling(self):
        """Test price calculation exception handling."""
        # Invalid quote request that should cause an exception
        quote_request = {}  # Missing required fields
        
        result = self.pricing_engine.calculate_price(quote_request)
        
        assert result is None

