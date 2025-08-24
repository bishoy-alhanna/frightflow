"""
Pricing engine for dynamic freight quote calculations.
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

from shared.cache import cache, cached
from shared.database import db
from src.models.quotation import PricingRule

logger = logging.getLogger(__name__)


class PricingEngine:
    """Dynamic pricing engine for freight quotes."""
    
    def __init__(self):
        self.exchange_rates = {}  # Cache for FX rates
        self.fuel_surcharge_rates = {}  # Cache for fuel surcharge rates
    
    def calculate_price(self, quote_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Calculate price for a quote request.
        
        Args:
            quote_request: Dictionary containing quote request details
            
        Returns:
            Dictionary with pricing breakdown or None if calculation fails
        """
        try:
            mode = quote_request['mode'].upper()
            service = quote_request['service'].upper()
            origin = quote_request['origin'].upper()
            destination = quote_request['destination'].upper()
            
            # Get pricing rules
            pricing_rules = self._get_pricing_rules(service, f"{origin}-{destination}")
            if not pricing_rules:
                logger.warning(f"No pricing rules found for {service} {origin}-{destination}")
                return self._fallback_pricing(quote_request)
            
            # Calculate base price
            base_price = self._calculate_base_price(quote_request, pricing_rules)
            
            # Calculate surcharges
            surcharges = self._calculate_surcharges(quote_request, pricing_rules)
            
            # Calculate total
            total_surcharge = sum(s['amount'] for s in surcharges)
            total_price = base_price + total_surcharge
            
            # Create line items
            items = self._create_line_items(quote_request, base_price, surcharges)
            
            return {
                'currency': pricing_rules.currency,
                'base': float(base_price),
                'surcharges': surcharges,
                'total': float(total_price),
                'items': items,
                'calculation_details': {
                    'pricing_rule_id': pricing_rules.id,
                    'calculated_at': datetime.utcnow().isoformat()
                }
            }
        
        except Exception as e:
            logger.error(f"Error calculating price: {e}")
            return None
    
    @cached(ttl=300, key_prefix="pricing_rules")
    def _get_pricing_rules(self, service: str, lane_key: str) -> Optional[PricingRule]:
        """Get active pricing rules for service and lane."""
        try:
            rule = PricingRule.query.filter(
                PricingRule.service == service,
                PricingRule.lane_key == lane_key,
                PricingRule.is_active == True,
                PricingRule.effective_from <= datetime.utcnow()
            ).filter(
                (PricingRule.effective_to.is_(None)) | 
                (PricingRule.effective_to >= datetime.utcnow())
            ).order_by(PricingRule.version.desc()).first()
            
            return rule
        except Exception as e:
            logger.error(f"Error fetching pricing rules: {e}")
            return None
    
    def _calculate_base_price(self, quote_request: Dict[str, Any], pricing_rules: PricingRule) -> Decimal:
        """Calculate base price using pricing formula."""
        try:
            formula = pricing_rules.get_formula()
            service = quote_request['service'].upper()
            
            if service == 'FCL':
                return self._calculate_fcl_price(quote_request, formula)
            elif service == 'LCL':
                return self._calculate_lcl_price(quote_request, formula)
            elif service == 'AIR':
                return self._calculate_air_price(quote_request, formula)
            else:
                logger.warning(f"Unknown service type: {service}")
                return Decimal('1000.00')  # Fallback price
        
        except Exception as e:
            logger.error(f"Error calculating base price: {e}")
            return Decimal('1000.00')  # Fallback price
    
    def _calculate_fcl_price(self, quote_request: Dict[str, Any], formula: Dict[str, Any]) -> Decimal:
        """Calculate FCL (Full Container Load) pricing."""
        containers = quote_request.get('containers', [])
        if not containers:
            return Decimal('2000.00')  # Default FCL price
        
        total_price = Decimal('0')
        
        for container in containers:
            container_type = container.get('type', '20GP')
            count = container.get('count', 1)
            
            # Get base rate from formula
            base_rates = formula.get('base_rates', {})
            rate = Decimal(str(base_rates.get(container_type, base_rates.get('default', '2000'))))
            
            total_price += rate * Decimal(str(count))
        
        return total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _calculate_lcl_price(self, quote_request: Dict[str, Any], formula: Dict[str, Any]) -> Decimal:
        """Calculate LCL (Less than Container Load) pricing."""
        cargo = quote_request.get('cargo', {})
        weight_kg = Decimal(str(cargo.get('weightKg', 1000)))
        volume_m3 = Decimal(str(cargo.get('volumeM3', 1)))
        
        # Get rates from formula
        weight_rate = Decimal(str(formula.get('weight_rate', '0.5')))  # per kg
        volume_rate = Decimal(str(formula.get('volume_rate', '100')))  # per m3
        minimum_charge = Decimal(str(formula.get('minimum_charge', '500')))
        
        # Calculate by weight and volume, take higher
        weight_charge = weight_kg * weight_rate
        volume_charge = volume_m3 * volume_rate
        
        calculated_price = max(weight_charge, volume_charge, minimum_charge)
        
        return calculated_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _calculate_air_price(self, quote_request: Dict[str, Any], formula: Dict[str, Any]) -> Decimal:
        """Calculate air freight pricing."""
        cargo = quote_request.get('cargo', {})
        weight_kg = Decimal(str(cargo.get('weightKg', 100)))
        
        # Air freight is typically charged by weight
        rate_per_kg = Decimal(str(formula.get('rate_per_kg', '5.0')))
        minimum_charge = Decimal(str(formula.get('minimum_charge', '300')))
        
        calculated_price = max(weight_kg * rate_per_kg, minimum_charge)
        
        return calculated_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _calculate_surcharges(self, quote_request: Dict[str, Any], pricing_rules: PricingRule) -> List[Dict[str, Any]]:
        """Calculate applicable surcharges."""
        surcharges = []
        accessorials = quote_request.get('accessorials', [])
        formula = pricing_rules.get_formula()
        surcharge_rates = formula.get('surcharges', {})
        
        # Fuel surcharge
        if 'FUEL' in accessorials:
            fuel_rate = self._get_fuel_surcharge_rate(quote_request['origin'], quote_request['destination'])
            if fuel_rate:
                surcharges.append({
                    'code': 'FUEL',
                    'description': 'Fuel Surcharge',
                    'amount': float(fuel_rate),
                    'type': 'percentage'
                })
        
        # Port fees
        if 'PORT_FEES' in accessorials:
            port_fee = Decimal(str(surcharge_rates.get('PORT_FEES', '150')))
            surcharges.append({
                'code': 'PORT_FEES',
                'description': 'Port Handling Fees',
                'amount': float(port_fee),
                'type': 'fixed'
            })
        
        # Documentation fee
        if 'DOCUMENTATION' in accessorials:
            doc_fee = Decimal(str(surcharge_rates.get('DOCUMENTATION', '75')))
            surcharges.append({
                'code': 'DOCUMENTATION',
                'description': 'Documentation Fee',
                'amount': float(doc_fee),
                'type': 'fixed'
            })
        
        # Security surcharge
        if 'SECURITY' in accessorials:
            security_fee = Decimal(str(surcharge_rates.get('SECURITY', '50')))
            surcharges.append({
                'code': 'SECURITY',
                'description': 'Security Surcharge',
                'amount': float(security_fee),
                'type': 'fixed'
            })
        
        return surcharges
    
    @cached(ttl=3600, key_prefix="fuel_surcharge")
    def _get_fuel_surcharge_rate(self, origin: str, destination: str) -> Optional[Decimal]:
        """Get fuel surcharge rate for route."""
        # In a real implementation, this would fetch from external API or database
        # For now, return a mock rate based on route
        base_rate = Decimal('120.00')  # Base fuel surcharge
        
        # Adjust based on route distance (simplified)
        route_multipliers = {
            'SGSIN-EGALY': Decimal('1.2'),  # Singapore to Egypt
            'SGSIN-USNYC': Decimal('1.5'),  # Singapore to New York
            'SGSIN-NLRTM': Decimal('1.1'),  # Singapore to Rotterdam
        }
        
        route_key = f"{origin}-{destination}"
        multiplier = route_multipliers.get(route_key, Decimal('1.0'))
        
        return (base_rate * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _create_line_items(self, quote_request: Dict[str, Any], base_price: Decimal, 
                          surcharges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create detailed line items for the quote."""
        items = []
        
        # Base freight item
        service_description = self._get_service_description(quote_request)
        items.append({
            'description': service_description,
            'quantity': 1,
            'unit_price': float(base_price),
            'total_price': float(base_price),
            'type': 'BASE'
        })
        
        # Surcharge items
        for surcharge in surcharges:
            items.append({
                'description': surcharge['description'],
                'quantity': 1,
                'unit_price': surcharge['amount'],
                'total_price': surcharge['amount'],
                'type': 'SURCHARGE'
            })
        
        return items
    
    def _get_service_description(self, quote_request: Dict[str, Any]) -> str:
        """Generate service description for line item."""
        mode = quote_request['mode']
        service = quote_request['service']
        origin = quote_request['origin']
        destination = quote_request['destination']
        
        if service == 'FCL':
            containers = quote_request.get('containers', [])
            if containers:
                container_desc = ', '.join([f"{c['count']}x{c['type']}" for c in containers])
                return f"{mode} {service} - {container_desc} from {origin} to {destination}"
        
        return f"{mode} {service} freight from {origin} to {destination}"
    
    def _fallback_pricing(self, quote_request: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback pricing when no rules are found."""
        logger.warning("Using fallback pricing - no rules found")
        
        service = quote_request['service'].upper()
        
        # Simple fallback pricing
        if service == 'FCL':
            base_price = 2000.00
        elif service == 'LCL':
            base_price = 800.00
        elif service == 'AIR':
            base_price = 500.00
        else:
            base_price = 1000.00
        
        # Add basic fuel surcharge
        surcharges = [{
            'code': 'FUEL',
            'description': 'Fuel Surcharge',
            'amount': 120.00,
            'type': 'fixed'
        }]
        
        total_price = base_price + sum(s['amount'] for s in surcharges)
        
        items = [{
            'description': f"Fallback {service} freight",
            'quantity': 1,
            'unit_price': base_price,
            'total_price': base_price,
            'type': 'BASE'
        }]
        
        return {
            'currency': 'USD',
            'base': base_price,
            'surcharges': surcharges,
            'total': total_price,
            'items': items,
            'calculation_details': {
                'fallback': True,
                'calculated_at': datetime.utcnow().isoformat()
            }
        }
    
    @cached(ttl=3600, key_prefix="exchange_rates")
    def _get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate between currencies."""
        if from_currency == to_currency:
            return Decimal('1.0')
        
        # In a real implementation, this would fetch from external API
        # For now, return mock rates
        mock_rates = {
            'USD_EUR': Decimal('0.85'),
            'USD_GBP': Decimal('0.75'),
            'USD_SGD': Decimal('1.35'),
            'EUR_USD': Decimal('1.18'),
            'GBP_USD': Decimal('1.33'),
            'SGD_USD': Decimal('0.74')
        }
        
        rate_key = f"{from_currency}_{to_currency}"
        return mock_rates.get(rate_key, Decimal('1.0'))
    
    def seed_sample_pricing_rules(self):
        """Seed database with sample pricing rules for testing."""
        try:
            # Check if rules already exist
            existing_rules = PricingRule.query.count()
            if existing_rules > 0:
                logger.info("Pricing rules already exist, skipping seed")
                return
            
            sample_rules = [
                {
                    'service': 'FCL',
                    'lane_key': 'SGSIN-EGALY',
                    'currency': 'USD',
                    'formula': {
                        'base_rates': {
                            '20GP': '1800',
                            '40GP': '2200',
                            '40HC': '2400',
                            'default': '2000'
                        },
                        'surcharges': {
                            'FUEL': '120',
                            'PORT_FEES': '150',
                            'DOCUMENTATION': '75',
                            'SECURITY': '50'
                        }
                    }
                },
                {
                    'service': 'LCL',
                    'lane_key': 'SGSIN-EGALY',
                    'currency': 'USD',
                    'formula': {
                        'weight_rate': '0.8',
                        'volume_rate': '120',
                        'minimum_charge': '500',
                        'surcharges': {
                            'FUEL': '80',
                            'PORT_FEES': '100',
                            'DOCUMENTATION': '50'
                        }
                    }
                },
                {
                    'service': 'AIR',
                    'lane_key': 'SGSIN-EGALY',
                    'currency': 'USD',
                    'formula': {
                        'rate_per_kg': '4.5',
                        'minimum_charge': '300',
                        'surcharges': {
                            'FUEL': '60',
                            'SECURITY': '40',
                            'DOCUMENTATION': '30'
                        }
                    }
                }
            ]
            
            for rule_data in sample_rules:
                rule = PricingRule(
                    service=rule_data['service'],
                    lane_key=rule_data['lane_key'],
                    currency=rule_data['currency']
                )
                rule.set_formula(rule_data['formula'])
                db.session.add(rule)
            
            db.session.commit()
            logger.info(f"Seeded {len(sample_rules)} pricing rules")
        
        except Exception as e:
            logger.error(f"Error seeding pricing rules: {e}")
            db.session.rollback()

