"""
Quotation service data models.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
from sqlalchemy import Index
from shared.database import BaseModel, db


class PricingRule(BaseModel):
    """Pricing rules for different services and lanes."""
    
    __tablename__ = 'pricing_rules'
    
    service = db.Column(db.String(50), nullable=False)  # FCL, LCL, AIR
    lane_key = db.Column(db.String(100), nullable=False)  # SGSIN-EGALY
    formula = db.Column(db.Text, nullable=False)  # JSON formula for pricing
    currency = db.Column(db.String(3), nullable=False, default='USD')
    effective_from = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    effective_to = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_pricing_rules_service_lane', 'service', 'lane_key'),
        Index('idx_pricing_rules_active', 'is_active', 'effective_from', 'effective_to'),
    )
    
    def get_formula(self) -> Dict[str, Any]:
        """Get pricing formula as dictionary."""
        try:
            return json.loads(self.formula)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_formula(self, formula_dict: Dict[str, Any]):
        """Set pricing formula from dictionary."""
        self.formula = json.dumps(formula_dict)
    
    def is_effective(self, date: Optional[datetime] = None) -> bool:
        """Check if pricing rule is effective at given date."""
        if date is None:
            date = datetime.utcnow()
        
        if not self.is_active:
            return False
        
        if date < self.effective_from:
            return False
        
        if self.effective_to and date > self.effective_to:
            return False
        
        return True
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with formula parsed."""
        result = super().to_dict(exclude)
        result['formula'] = self.get_formula()
        return result


class Quote(BaseModel):
    """Quote entity with pricing details."""
    
    __tablename__ = 'quotes'
    
    quote_id = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.String(50), nullable=True)  # Optional for now
    
    # Shipment details
    mode = db.Column(db.String(10), nullable=False)  # SEA, AIR
    service = db.Column(db.String(20), nullable=False)  # FCL, LCL, etc.
    origin = db.Column(db.String(10), nullable=False)  # Port/Airport code
    destination = db.Column(db.String(10), nullable=False)  # Port/Airport code
    route_key = db.Column(db.String(100), nullable=False)  # origin-destination
    
    # Cargo details
    cargo_details = db.Column(db.Text, nullable=False)  # JSON cargo info
    containers = db.Column(db.Text, nullable=True)  # JSON container info
    accessorials = db.Column(db.Text, nullable=True)  # JSON accessorial services
    
    # Pricing
    currency = db.Column(db.String(3), nullable=False, default='USD')
    base_amount = db.Column(db.Numeric(12, 2), nullable=False)
    surcharges_json = db.Column(db.Text, nullable=True)  # JSON surcharge details
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Quote lifecycle
    status = db.Column(db.String(20), nullable=False, default='DRAFT')  # DRAFT, ISSUED, ACCEPTED, EXPIRED
    valid_until = db.Column(db.DateTime, nullable=False)
    issued_at = db.Column(db.DateTime, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    
    # Document reference
    pdf_path = db.Column(db.String(500), nullable=True)
    
    # Relationships
    items = db.relationship('QuoteItem', backref='quote', lazy=True, cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_quotes_customer', 'customer_id', 'created_at'),
        Index('idx_quotes_status_valid', 'status', 'valid_until'),
        Index('idx_quotes_route', 'route_key'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.quote_id:
            self.quote_id = self.generate_quote_id()
        if not self.route_key:
            self.route_key = f"{self.origin}-{self.destination}"
        if not self.valid_until:
            self.valid_until = datetime.utcnow() + timedelta(days=7)  # Default 7 days validity
    
    @staticmethod
    def generate_quote_id() -> str:
        """Generate unique quote ID."""
        import uuid
        return f"Q-{uuid.uuid4().hex[:8].upper()}"
    
    def get_cargo_details(self) -> Dict[str, Any]:
        """Get cargo details as dictionary."""
        try:
            return json.loads(self.cargo_details)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_cargo_details(self, cargo_dict: Dict[str, Any]):
        """Set cargo details from dictionary."""
        self.cargo_details = json.dumps(cargo_dict)
    
    def get_containers(self) -> List[Dict[str, Any]]:
        """Get containers as list of dictionaries."""
        try:
            return json.loads(self.containers) if self.containers else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_containers(self, containers_list: List[Dict[str, Any]]):
        """Set containers from list of dictionaries."""
        self.containers = json.dumps(containers_list)
    
    def get_accessorials(self) -> List[str]:
        """Get accessorials as list."""
        try:
            return json.loads(self.accessorials) if self.accessorials else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_accessorials(self, accessorials_list: List[str]):
        """Set accessorials from list."""
        self.accessorials = json.dumps(accessorials_list)
    
    def get_surcharges(self) -> List[Dict[str, Any]]:
        """Get surcharges as list of dictionaries."""
        try:
            return json.loads(self.surcharges_json) if self.surcharges_json else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_surcharges(self, surcharges_list: List[Dict[str, Any]]):
        """Set surcharges from list of dictionaries."""
        self.surcharges_json = json.dumps(surcharges_list, default=str)
    
    def is_valid(self) -> bool:
        """Check if quote is still valid."""
        return datetime.utcnow() <= self.valid_until and self.status in ['ISSUED', 'DRAFT']
    
    def is_expired(self) -> bool:
        """Check if quote has expired."""
        return datetime.utcnow() > self.valid_until
    
    def accept(self):
        """Accept the quote."""
        if not self.is_valid():
            raise ValueError("Cannot accept expired or invalid quote")
        
        self.status = 'ACCEPTED'
        self.accepted_at = datetime.utcnow()
    
    def issue(self):
        """Issue the quote."""
        if self.status != 'DRAFT':
            raise ValueError("Can only issue draft quotes")
        
        self.status = 'ISSUED'
        self.issued_at = datetime.utcnow()
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with JSON fields parsed."""
        result = super().to_dict(exclude)
        result.update({
            'cargo_details': self.get_cargo_details(),
            'containers': self.get_containers(),
            'accessorials': self.get_accessorials(),
            'surcharges': self.get_surcharges(),
            'is_valid': self.is_valid(),
            'is_expired': self.is_expired(),
            'items': [item.to_dict() for item in self.items] if self.items else []
        })
        
        # Convert Decimal to float for JSON serialization
        if 'base_amount' in result:
            result['base_amount'] = float(result['base_amount'])
        if 'total_amount' in result:
            result['total_amount'] = float(result['total_amount'])
        
        return result


class QuoteItem(BaseModel):
    """Individual line items in a quote."""
    
    __tablename__ = 'quote_items'
    
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # BASE, SURCHARGE, ACCESSORIAL
    currency = db.Column(db.String(3), nullable=False, default='USD')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.total_price and self.quantity and self.unit_price:
            self.total_price = self.quantity * self.unit_price
    
    def calculate_total(self):
        """Calculate total price from quantity and unit price."""
        if self.quantity and self.unit_price:
            self.total_price = self.quantity * self.unit_price
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with Decimal conversion."""
        result = super().to_dict(exclude)
        
        # Convert Decimal to float for JSON serialization
        for field in ['quantity', 'unit_price', 'total_price']:
            if field in result and result[field] is not None:
                result[field] = float(result[field])
        
        return result

