import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

class LeadStatus(Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    PROPOSAL_SENT = "PROPOSAL_SENT"
    NEGOTIATION = "NEGOTIATION"
    CONVERTED = "CONVERTED"
    LOST = "LOST"
    DISQUALIFIED = "DISQUALIFIED"

class LeadSource(Enum):
    WEBSITE = "WEBSITE"
    REFERRAL = "REFERRAL"
    COLD_CALL = "COLD_CALL"
    EMAIL_CAMPAIGN = "EMAIL_CAMPAIGN"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    TRADE_SHOW = "TRADE_SHOW"
    ADVERTISEMENT = "ADVERTISEMENT"
    PARTNER = "PARTNER"
    OTHER = "OTHER"

class LeadPriority(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

@dataclass
class Lead:
    """Lead model for potential customers"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    lead_number: str = ""
    
    # Company information
    company_name: str = ""
    contact_name: str = ""
    title: Optional[str] = None
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
    
    # Lead details
    source: LeadSource = LeadSource.WEBSITE
    status: LeadStatus = LeadStatus.NEW
    priority: LeadPriority = LeadPriority.MEDIUM
    estimated_value: Optional[float] = None
    probability: int = 0  # Percentage 0-100
    
    # Requirements and notes
    requirements: Optional[str] = None
    notes: Optional[str] = None
    
    # Assignment and tracking
    assigned_to: Optional[str] = None
    last_contact_date: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    
    # Conversion tracking
    converted_to_customer_id: Optional[str] = None
    converted_at: Optional[datetime] = None
    converted_by: Optional[str] = None
    lost_reason: Optional[str] = None
    
    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.lead_number:
            self.lead_number = f"LD{datetime.now().strftime('%Y%m%d')}{self.id[:8].upper()}"
    
    def update_status(self, new_status: LeadStatus, notes: Optional[str] = None):
        """Update lead status with optional notes"""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        if notes:
            status_note = f"Status changed from {old_status.value} to {new_status.value}: {notes}"
            self.notes = f"{self.notes}\n\n{status_note}" if self.notes else status_note
    
    def update_last_contact(self):
        """Update the last contact date"""
        self.last_contact_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def convert_to_customer(self, customer_id: str, converted_by: str):
        """Mark lead as converted to customer"""
        self.status = LeadStatus.CONVERTED
        self.converted_to_customer_id = customer_id
        self.converted_at = datetime.utcnow()
        self.converted_by = converted_by
        self.updated_at = datetime.utcnow()
    
    def mark_as_lost(self, reason: str):
        """Mark lead as lost with reason"""
        self.status = LeadStatus.LOST
        self.lost_reason = reason
        self.updated_at = datetime.utcnow()
    
    def calculate_score(self) -> int:
        """Calculate lead score based on various factors"""
        score = 0
        
        # Base score from probability
        score += self.probability
        
        # Source scoring
        source_scores = {
            LeadSource.REFERRAL: 20,
            LeadSource.PARTNER: 15,
            LeadSource.WEBSITE: 10,
            LeadSource.TRADE_SHOW: 10,
            LeadSource.SOCIAL_MEDIA: 5,
            LeadSource.EMAIL_CAMPAIGN: 5,
            LeadSource.COLD_CALL: 3,
            LeadSource.ADVERTISEMENT: 3,
            LeadSource.OTHER: 0
        }
        score += source_scores.get(self.source, 0)
        
        # Priority scoring
        priority_scores = {
            LeadPriority.URGENT: 15,
            LeadPriority.HIGH: 10,
            LeadPriority.MEDIUM: 5,
            LeadPriority.LOW: 0
        }
        score += priority_scores.get(self.priority, 0)
        
        # Estimated value scoring
        if self.estimated_value:
            if self.estimated_value >= 100000:
                score += 20
            elif self.estimated_value >= 50000:
                score += 15
            elif self.estimated_value >= 10000:
                score += 10
            elif self.estimated_value >= 5000:
                score += 5
        
        # Recent activity scoring
        if self.last_contact_date:
            days_since_contact = (datetime.utcnow() - self.last_contact_date).days
            if days_since_contact <= 7:
                score += 10
            elif days_since_contact <= 30:
                score += 5
        
        return min(score, 100)  # Cap at 100
    
    def get_age_in_days(self) -> int:
        """Get the age of the lead in days"""
        return (datetime.utcnow() - self.created_at).days
    
    def is_stale(self, days_threshold: int = 30) -> bool:
        """Check if lead is stale (no activity for specified days)"""
        if not self.last_contact_date:
            return self.get_age_in_days() > days_threshold
        
        days_since_contact = (datetime.utcnow() - self.last_contact_date).days
        return days_since_contact > days_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'lead_number': self.lead_number,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'title': self.title,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'source': self.source.value,
            'status': self.status.value,
            'priority': self.priority.value,
            'estimated_value': self.estimated_value,
            'probability': self.probability,
            'requirements': self.requirements,
            'notes': self.notes,
            'assigned_to': self.assigned_to,
            'last_contact_date': self.last_contact_date.isoformat() if self.last_contact_date else None,
            'next_follow_up': self.next_follow_up.isoformat() if self.next_follow_up else None,
            'converted_to_customer_id': self.converted_to_customer_id,
            'converted_at': self.converted_at.isoformat() if self.converted_at else None,
            'converted_by': self.converted_by,
            'lost_reason': self.lost_reason,
            'lead_score': self.calculate_score(),
            'age_in_days': self.get_age_in_days(),
            'is_stale': self.is_stale(),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

