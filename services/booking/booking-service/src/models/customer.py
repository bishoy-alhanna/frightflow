import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class Customer:
    """Customer model for booking service"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    postal_code: str = ""
    tax_id: Optional[str] = None
    credit_limit: float = 0.0
    payment_terms: str = "NET_30"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'country': self.country,
            'postal_code': self.postal_code,
            'tax_id': self.tax_id,
            'credit_limit': self.credit_limit,
            'payment_terms': self.payment_terms,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

