import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

class VendorStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REJECTED = "REJECTED"

class ServiceType(Enum):
    OCEAN_FREIGHT = "OCEAN_FREIGHT"
    AIR_FREIGHT = "AIR_FREIGHT"
    LAND_FREIGHT = "LAND_FREIGHT"
    CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE"
    WAREHOUSING = "WAREHOUSING"
    TRUCKING = "TRUCKING"
    RAIL_FREIGHT = "RAIL_FREIGHT"
    LAST_MILE_DELIVERY = "LAST_MILE_DELIVERY"
    PACKAGING = "PACKAGING"
    INSURANCE = "INSURANCE"

class ContactType(Enum):
    PRIMARY = "PRIMARY"
    BILLING = "BILLING"
    OPERATIONS = "OPERATIONS"
    EMERGENCY = "EMERGENCY"
    SALES = "SALES"

@dataclass
class VendorContact:
    """Contact information for vendor personnel"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vendor_id: str = ""
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
            'vendor_id': self.vendor_id,
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
class VendorService:
    """Services offered by a vendor"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vendor_id: str = ""
    service_type: ServiceType = ServiceType.OCEAN_FREIGHT
    service_name: str = ""
    description: Optional[str] = None
    coverage_areas: List[str] = field(default_factory=list)
    pricing_model: Optional[str] = None
    minimum_volume: Optional[float] = None
    maximum_volume: Optional[float] = None
    transit_time_min: Optional[int] = None  # in days
    transit_time_max: Optional[int] = None  # in days
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'service_type': self.service_type.value,
            'service_name': self.service_name,
            'description': self.description,
            'coverage_areas': self.coverage_areas,
            'pricing_model': self.pricing_model,
            'minimum_volume': self.minimum_volume,
            'maximum_volume': self.maximum_volume,
            'transit_time_min': self.transit_time_min,
            'transit_time_max': self.transit_time_max,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class VendorRating:
    """Rating and review for a vendor"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vendor_id: str = ""
    shipment_id: str = ""
    overall_rating: float = 0.0  # 1-5 scale
    quality_rating: Optional[float] = None
    timeliness_rating: Optional[float] = None
    communication_rating: Optional[float] = None
    cost_rating: Optional[float] = None
    comments: Optional[str] = None
    rated_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'shipment_id': self.shipment_id,
            'overall_rating': self.overall_rating,
            'quality_rating': self.quality_rating,
            'timeliness_rating': self.timeliness_rating,
            'communication_rating': self.communication_rating,
            'cost_rating': self.cost_rating,
            'comments': self.comments,
            'rated_by': self.rated_by,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class Vendor:
    """Vendor model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vendor_number: str = ""
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
    business_license: Optional[str] = None
    insurance_info: Optional[str] = None
    
    # Service information
    service_types: List[ServiceType] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    coverage_areas: List[str] = field(default_factory=list)
    
    # Financial information
    payment_terms: str = "NET_30"
    currency: str = "USD"
    credit_limit: float = 0.0
    
    # Status and tracking
    status: VendorStatus = VendorStatus.PENDING_APPROVAL
    onboarding_date: Optional[datetime] = None
    last_activity_date: Optional[datetime] = None
    
    # Performance metrics
    average_rating: float = 0.0
    total_ratings: int = 0
    total_shipments: int = 0
    on_time_delivery_rate: float = 0.0
    
    # Relationship information
    account_manager: Optional[str] = None
    
    # Additional contacts and services
    contacts: List[VendorContact] = field(default_factory=list)
    services: List[VendorService] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    is_active: bool = True
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.vendor_number:
            self.vendor_number = f"VN{datetime.now().strftime('%Y%m%d')}{self.id[:8].upper()}"
    
    def add_contact(self, contact: VendorContact) -> VendorContact:
        """Add a contact to the vendor"""
        contact.vendor_id = self.id
        self.contacts.append(contact)
        self.updated_at = datetime.utcnow()
        return contact
    
    def add_service(self, service: VendorService) -> VendorService:
        """Add a service to the vendor"""
        service.vendor_id = self.id
        self.services.append(service)
        self.updated_at = datetime.utcnow()
        return service
    
    def get_primary_contact(self) -> Optional[VendorContact]:
        """Get the primary contact for the vendor"""
        for contact in self.contacts:
            if contact.is_primary and contact.is_active:
                return contact
        return None
    
    def get_contact_by_type(self, contact_type: ContactType) -> Optional[VendorContact]:
        """Get contact by type"""
        for contact in self.contacts:
            if contact.contact_type == contact_type and contact.is_active:
                return contact
        return None
    
    def get_services_by_type(self, service_type: ServiceType) -> List[VendorService]:
        """Get services by type"""
        return [service for service in self.services 
                if service.service_type == service_type and service.is_active]
    
    def update_last_activity(self):
        """Update the last activity date"""
        self.last_activity_date = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Activate the vendor"""
        if self.status == VendorStatus.PENDING_APPROVAL:
            self.status = VendorStatus.ACTIVE
            self.onboarding_date = datetime.utcnow()
        elif self.status in [VendorStatus.INACTIVE, VendorStatus.SUSPENDED]:
            self.status = VendorStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deactivate(self, reason: Optional[str] = None):
        """Deactivate the vendor"""
        self.status = VendorStatus.INACTIVE
        if reason:
            self.notes = f"{self.notes}\n\nDeactivated: {reason}" if self.notes else f"Deactivated: {reason}"
        self.updated_at = datetime.utcnow()
    
    def suspend(self, reason: str):
        """Suspend the vendor"""
        self.status = VendorStatus.SUSPENDED
        self.notes = f"{self.notes}\n\nSuspended: {reason}" if self.notes else f"Suspended: {reason}"
        self.updated_at = datetime.utcnow()
    
    def update_rating(self, new_rating: float):
        """Update average rating with new rating"""
        total_score = self.average_rating * self.total_ratings + new_rating
        self.total_ratings += 1
        self.average_rating = total_score / self.total_ratings
        self.updated_at = datetime.utcnow()
    
    def calculate_performance_score(self) -> float:
        """Calculate overall performance score"""
        score = 0.0
        
        # Rating component (40%)
        if self.average_rating > 0:
            score += (self.average_rating / 5.0) * 40
        
        # On-time delivery component (30%)
        score += (self.on_time_delivery_rate / 100.0) * 30
        
        # Experience component (20%)
        if self.total_shipments > 0:
            experience_score = min(self.total_shipments / 100.0, 1.0)  # Cap at 100 shipments
            score += experience_score * 20
        
        # Activity component (10%)
        if self.last_activity_date:
            days_since_activity = (datetime.utcnow() - self.last_activity_date).days
            activity_score = max(0, 1 - (days_since_activity / 365.0))  # Decay over a year
            score += activity_score * 10
        
        return min(score, 100.0)  # Cap at 100
    
    def is_qualified_for_service(self, service_type: ServiceType, 
                                origin: str, destination: str) -> bool:
        """Check if vendor is qualified for a specific service"""
        if self.status != VendorStatus.ACTIVE:
            return False
        
        # Check if vendor offers the service type
        if service_type not in self.service_types:
            return False
        
        # Check coverage areas
        if self.coverage_areas:
            origin_covered = any(area.lower() in origin.lower() for area in self.coverage_areas)
            dest_covered = any(area.lower() in destination.lower() for area in self.coverage_areas)
            if not (origin_covered or dest_covered):
                return False
        
        # Check minimum performance criteria
        if self.total_ratings >= 5 and self.average_rating < 3.0:
            return False
        
        if self.total_shipments >= 10 and self.on_time_delivery_rate < 70.0:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'vendor_number': self.vendor_number,
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
            'business_license': self.business_license,
            'insurance_info': self.insurance_info,
            'service_types': [st.value for st in self.service_types],
            'capabilities': self.capabilities,
            'certifications': self.certifications,
            'coverage_areas': self.coverage_areas,
            'payment_terms': self.payment_terms,
            'currency': self.currency,
            'credit_limit': self.credit_limit,
            'status': self.status.value,
            'onboarding_date': self.onboarding_date.isoformat() if self.onboarding_date else None,
            'last_activity_date': self.last_activity_date.isoformat() if self.last_activity_date else None,
            'average_rating': self.average_rating,
            'total_ratings': self.total_ratings,
            'total_shipments': self.total_shipments,
            'on_time_delivery_rate': self.on_time_delivery_rate,
            'performance_score': self.calculate_performance_score(),
            'account_manager': self.account_manager,
            'contacts': [contact.to_dict() for contact in self.contacts],
            'services': [service.to_dict() for service in self.services],
            'tags': self.tags,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

