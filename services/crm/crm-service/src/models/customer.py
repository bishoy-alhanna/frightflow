import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

class CustomerStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PROSPECT = "PROSPECT"

class InteractionType(Enum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    MEETING = "MEETING"
    QUOTE_REQUEST = "QUOTE_REQUEST"
    COMPLAINT = "COMPLAINT"
    SUPPORT = "SUPPORT"
    FOLLOW_UP = "FOLLOW_UP"
    OTHER = "OTHER"

class ContactType(Enum):
    PRIMARY = "PRIMARY"
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    TECHNICAL = "TECHNICAL"
    EMERGENCY = "EMERGENCY"

@dataclass
class Contact:
    """Contact information within a customer organization"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    contact_type: ContactType = ContactType.PRIMARY
    name: str = ""
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    department: Optional[str] = None
    is_primary: bool = False
    is_active: bool = True
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'contact_type': self.contact_type.value,
            'name': self.name,
            'title': self.title,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'department': self.department,
            'is_primary': self.is_primary,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class CustomerInteraction:
    """Customer interaction record"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    interaction_type: InteractionType = InteractionType.OTHER
    subject: str = ""
    description: str = ""
    contact_person: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    follow_up_completed: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'interaction_type': self.interaction_type.value,
            'subject': self.subject,
            'description': self.description,
            'contact_person': self.contact_person,
            'outcome': self.outcome,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'follow_up_completed': self.follow_up_completed,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class CustomerNote:
    """Customer note/memo"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str = ""
    content: str = ""
    is_private: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'content': self.content,
            'is_private': self.is_private,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class Customer:
    """Customer model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_number: str = ""
    company_name: str = ""
    contact_name: str = ""
    email: str = ""
    phone: Optional[str] = None
    mobile: Optional[str] = None
    website: Optional[str] = None
    
    # Address information
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Business information
    tax_id: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[float] = None
    
    # Account information
    credit_limit: float = 0.0
    payment_terms: str = "NET_30"
    currency: str = "USD"
    status: CustomerStatus = CustomerStatus.PROSPECT
    
    # Relationship information
    account_manager: Optional[str] = None
    sales_rep: Optional[str] = None
    customer_since: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None
    
    # Additional contacts
    contacts: List[Contact] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    is_active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.customer_number:
            self.customer_number = f"CU{datetime.now().strftime('%Y%m%d')}{self.id[:8].upper()}"
    
    def add_contact(self, contact: Contact) -> Contact:
        """Add a contact to the customer"""
        contact.customer_id = self.id
        self.contacts.append(contact)
        self.updated_at = datetime.utcnow()
        return contact
    
    def get_primary_contact(self) -> Optional[Contact]:
        """Get the primary contact for the customer"""
        for contact in self.contacts:
            if contact.is_primary and contact.is_active:
                return contact
        return None
    
    def get_contact_by_type(self, contact_type: ContactType) -> Optional[Contact]:
        """Get contact by type"""
        for contact in self.contacts:
            if contact.contact_type == contact_type and contact.is_active:
                return contact
        return None
    
    def update_last_contact(self):
        """Update the last contact date"""
        self.last_contact_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Activate the customer"""
        if self.status == CustomerStatus.PROSPECT:
            self.status = CustomerStatus.ACTIVE
            self.customer_since = datetime.utcnow()
        elif self.status in [CustomerStatus.INACTIVE, CustomerStatus.SUSPENDED]:
            self.status = CustomerStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deactivate(self, reason: Optional[str] = None):
        """Deactivate the customer"""
        self.status = CustomerStatus.INACTIVE
        if reason:
            self.notes = f"{self.notes}\n\nDeactivated: {reason}" if self.notes else f"Deactivated: {reason}"
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'customer_number': self.customer_number,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'tax_id': self.tax_id,
            'industry': self.industry,
            'company_size': self.company_size,
            'annual_revenue': self.annual_revenue,
            'credit_limit': self.credit_limit,
            'payment_terms': self.payment_terms,
            'currency': self.currency,
            'status': self.status.value,
            'account_manager': self.account_manager,
            'sales_rep': self.sales_rep,
            'customer_since': self.customer_since.isoformat() if self.customer_since else None,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None,
            'contacts': [contact.to_dict() for contact in self.contacts],
            'tags': self.tags,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

