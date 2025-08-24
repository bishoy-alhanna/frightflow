import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

class ContractStatus(Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    SUSPENDED = "SUSPENDED"

class ContractType(Enum):
    MASTER_SERVICE_AGREEMENT = "MASTER_SERVICE_AGREEMENT"
    SPOT_RATE_AGREEMENT = "SPOT_RATE_AGREEMENT"
    VOLUME_COMMITMENT = "VOLUME_COMMITMENT"
    EXCLUSIVE_PARTNERSHIP = "EXCLUSIVE_PARTNERSHIP"
    PREFERRED_VENDOR = "PREFERRED_VENDOR"
    SERVICE_LEVEL_AGREEMENT = "SERVICE_LEVEL_AGREEMENT"

class AmendmentType(Enum):
    RATE_CHANGE = "RATE_CHANGE"
    TERM_EXTENSION = "TERM_EXTENSION"
    SCOPE_CHANGE = "SCOPE_CHANGE"
    VOLUME_ADJUSTMENT = "VOLUME_ADJUSTMENT"
    SERVICE_MODIFICATION = "SERVICE_MODIFICATION"
    OTHER = "OTHER"

@dataclass
class ContractTerm:
    """Individual term or clause in a contract"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contract_id: str = ""
    term_type: str = ""  # e.g., "PAYMENT", "DELIVERY", "LIABILITY", "TERMINATION"
    title: str = ""
    description: str = ""
    value: Optional[str] = None
    is_mandatory: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'term_type': self.term_type,
            'title': self.title,
            'description': self.description,
            'value': self.value,
            'is_mandatory': self.is_mandatory,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class ContractAmendment:
    """Amendment to a contract"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contract_id: str = ""
    amendment_number: int = 1
    amendment_type: AmendmentType = AmendmentType.OTHER
    title: str = ""
    description: str = ""
    changes: Dict[str, Any] = field(default_factory=dict)
    effective_date: Optional[datetime] = None
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def approve(self, approved_by: str):
        """Approve the amendment"""
        self.approved = True
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'amendment_number': self.amendment_number,
            'amendment_type': self.amendment_type.value,
            'title': self.title,
            'description': self.description,
            'changes': self.changes,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'approved': self.approved,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class Contract:
    """Contract model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contract_number: str = ""
    vendor_id: str = ""
    contract_type: ContractType = ContractType.MASTER_SERVICE_AGREEMENT
    title: str = ""
    description: Optional[str] = None
    
    # Contract dates
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    renewal_date: Optional[datetime] = None
    notice_period_days: int = 30
    
    # Financial terms
    value: Optional[float] = None
    currency: str = "USD"
    payment_terms: str = "NET_30"
    
    # Performance terms
    minimum_volume: Optional[float] = None
    maximum_volume: Optional[float] = None
    service_level_targets: Dict[str, Any] = field(default_factory=dict)
    penalties: Dict[str, Any] = field(default_factory=dict)
    
    # Contract terms and amendments
    terms: List[ContractTerm] = field(default_factory=list)
    amendments: List[ContractAmendment] = field(default_factory=list)
    
    # Status and tracking
    status: ContractStatus = ContractStatus.DRAFT
    auto_renewal: bool = False
    
    # Document management
    document_url: Optional[str] = None
    signed_document_url: Optional[str] = None
    
    # Approval workflow
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.contract_number:
            self.contract_number = f"CT{datetime.now().strftime('%Y%m%d')}{self.id[:8].upper()}"
    
    def add_term(self, term: ContractTerm) -> ContractTerm:
        """Add a term to the contract"""
        term.contract_id = self.id
        self.terms.append(term)
        self.updated_at = datetime.utcnow()
        return term
    
    def add_amendment(self, amendment: ContractAmendment) -> ContractAmendment:
        """Add an amendment to the contract"""
        amendment.contract_id = self.id
        amendment.amendment_number = len(self.amendments) + 1
        self.amendments.append(amendment)
        self.updated_at = datetime.utcnow()
        return amendment
    
    def activate(self, approved_by: str):
        """Activate the contract"""
        self.status = ContractStatus.ACTIVE
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def terminate(self, reason: Optional[str] = None):
        """Terminate the contract"""
        self.status = ContractStatus.TERMINATED
        if reason:
            self.notes = f"{self.notes}\n\nTerminated: {reason}" if self.notes else f"Terminated: {reason}"
        self.updated_at = datetime.utcnow()
    
    def suspend(self, reason: str):
        """Suspend the contract"""
        self.status = ContractStatus.SUSPENDED
        self.notes = f"{self.notes}\n\nSuspended: {reason}" if self.notes else f"Suspended: {reason}"
        self.updated_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if contract is currently active"""
        if self.status != ContractStatus.ACTIVE:
            return False
        
        now = datetime.utcnow()
        if now < self.start_date:
            return False
        
        if self.end_date and now > self.end_date:
            return False
        
        return True
    
    def is_expiring_soon(self, days_threshold: int = 30) -> bool:
        """Check if contract is expiring within the threshold"""
        if not self.end_date or self.status != ContractStatus.ACTIVE:
            return False
        
        days_until_expiry = (self.end_date - datetime.utcnow()).days
        return 0 <= days_until_expiry <= days_threshold
    
    def get_days_until_expiry(self) -> Optional[int]:
        """Get number of days until contract expires"""
        if not self.end_date:
            return None
        
        days = (self.end_date - datetime.utcnow()).days
        return max(0, days)
    
    def calculate_utilization(self, actual_volume: float) -> float:
        """Calculate contract utilization percentage"""
        if not self.minimum_volume:
            return 0.0
        
        return min((actual_volume / self.minimum_volume) * 100, 100.0)
    
    def get_applicable_amendments(self) -> List[ContractAmendment]:
        """Get amendments that are approved and effective"""
        now = datetime.utcnow()
        return [
            amendment for amendment in self.amendments
            if amendment.approved and (
                not amendment.effective_date or amendment.effective_date <= now
            )
        ]
    
    def get_term_by_type(self, term_type: str) -> Optional[ContractTerm]:
        """Get a specific term by type"""
        for term in self.terms:
            if term.term_type == term_type:
                return term
        return None
    
    def get_service_level_target(self, metric: str) -> Optional[Any]:
        """Get a specific service level target"""
        return self.service_level_targets.get(metric)
    
    def get_penalty_for_breach(self, breach_type: str) -> Optional[Any]:
        """Get penalty for a specific breach type"""
        return self.penalties.get(breach_type)
    
    def renew(self, new_end_date: datetime, renewed_by: str):
        """Renew the contract"""
        self.end_date = new_end_date
        self.renewal_date = datetime.utcnow()
        self.notes = f"{self.notes}\n\nRenewed by {renewed_by} until {new_end_date.isoformat()}" if self.notes else f"Renewed by {renewed_by} until {new_end_date.isoformat()}"
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'contract_number': self.contract_number,
            'vendor_id': self.vendor_id,
            'contract_type': self.contract_type.value,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'renewal_date': self.renewal_date.isoformat() if self.renewal_date else None,
            'notice_period_days': self.notice_period_days,
            'value': self.value,
            'currency': self.currency,
            'payment_terms': self.payment_terms,
            'minimum_volume': self.minimum_volume,
            'maximum_volume': self.maximum_volume,
            'service_level_targets': self.service_level_targets,
            'penalties': self.penalties,
            'terms': [term.to_dict() for term in self.terms],
            'amendments': [amendment.to_dict() for amendment in self.amendments],
            'status': self.status.value,
            'auto_renewal': self.auto_renewal,
            'document_url': self.document_url,
            'signed_document_url': self.signed_document_url,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'is_active': self.is_active(),
            'is_expiring_soon': self.is_expiring_soon(),
            'days_until_expiry': self.get_days_until_expiry(),
            'tags': self.tags,
            'notes': self.notes,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

