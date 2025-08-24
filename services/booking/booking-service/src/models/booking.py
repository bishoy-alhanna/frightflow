import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

class BookingStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

class ShipmentStatus(Enum):
    BOOKED = "BOOKED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    EXCEPTION = "EXCEPTION"

class ContainerStatus(Enum):
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"

class ContainerType(Enum):
    DRY_20 = "20FT_DRY"
    DRY_40 = "40FT_DRY"
    DRY_40_HC = "40FT_HC_DRY"
    REEFER_20 = "20FT_REEFER"
    REEFER_40 = "40FT_REEFER"
    OPEN_TOP_20 = "20FT_OPEN_TOP"
    OPEN_TOP_40 = "40FT_OPEN_TOP"
    FLAT_RACK_20 = "20FT_FLAT_RACK"
    FLAT_RACK_40 = "40FT_FLAT_RACK"

class DocumentType(Enum):
    BILL_OF_LADING = "BILL_OF_LADING"
    COMMERCIAL_INVOICE = "COMMERCIAL_INVOICE"
    PACKING_LIST = "PACKING_LIST"
    CERTIFICATE_OF_ORIGIN = "CERTIFICATE_OF_ORIGIN"
    CUSTOMS_DECLARATION = "CUSTOMS_DECLARATION"
    INSURANCE_CERTIFICATE = "INSURANCE_CERTIFICATE"
    DELIVERY_ORDER = "DELIVERY_ORDER"
    OTHER = "OTHER"

@dataclass
class Contact:
    """Contact information for pickup/delivery"""
    name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'company': self.company,
            'phone': self.phone,
            'email': self.email,
            'address': self.address
        }

@dataclass
class VesselDetails:
    """Vessel information for shipment"""
    vessel_name: str
    voyage_number: str
    imo_number: Optional[str] = None
    eta: Optional[datetime] = None
    etd: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vessel_name': self.vessel_name,
            'voyage_number': self.voyage_number,
            'imo_number': self.imo_number,
            'eta': self.eta.isoformat() if self.eta else None,
            'etd': self.etd.isoformat() if self.etd else None
        }

@dataclass
class Container:
    """Container model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    container_number: str = ""
    container_type: ContainerType = ContainerType.DRY_20
    status: ContainerStatus = ContainerStatus.AVAILABLE
    location: Optional[str] = None
    current_shipment_id: Optional[str] = None
    last_inspection_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'container_number': self.container_number,
            'container_type': self.container_type.value,
            'status': self.status.value,
            'location': self.location,
            'current_shipment_id': self.current_shipment_id,
            'last_inspection_date': self.last_inspection_date.isoformat() if self.last_inspection_date else None,
            'next_maintenance_date': self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class TrackingEvent:
    """Tracking event for shipment"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    shipment_id: str = ""
    status: ShipmentStatus = ShipmentStatus.BOOKED
    location: str = ""
    description: str = ""
    event_time: datetime = field(default_factory=datetime.utcnow)
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'status': self.status.value,
            'location': self.location,
            'description': self.description,
            'event_time': self.event_time.isoformat(),
            'vessel_name': self.vessel_name,
            'voyage_number': self.voyage_number,
            'estimated_arrival': self.estimated_arrival.isoformat() if self.estimated_arrival else None,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class Document:
    """Document model for shipments"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    shipment_id: str = ""
    document_type: DocumentType = DocumentType.OTHER
    filename: str = ""
    original_filename: str = ""
    file_size: int = 0
    mime_type: str = ""
    storage_path: str = ""
    checksum: str = ""
    description: str = ""
    uploaded_by: str = ""
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'shipment_id': self.shipment_id,
            'document_type': self.document_type.value,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'description': self.description,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat()
        }

@dataclass
class Booking:
    """Booking model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quote_id: str = ""
    customer_id: str = ""
    booking_number: str = ""
    status: BookingStatus = BookingStatus.PENDING
    special_instructions: Optional[str] = None
    pickup_contact: Optional[Contact] = None
    delivery_contact: Optional[Contact] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.booking_number:
            self.booking_number = f"BK{datetime.now().strftime('%Y%m%d')}{self.id[:8].upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'customer_id': self.customer_id,
            'booking_number': self.booking_number,
            'status': self.status.value,
            'special_instructions': self.special_instructions,
            'pickup_contact': self.pickup_contact.to_dict() if self.pickup_contact else None,
            'delivery_contact': self.delivery_contact.to_dict() if self.delivery_contact else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }

@dataclass
class Shipment:
    """Shipment model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    booking_id: str = ""
    tracking_number: str = ""
    status: ShipmentStatus = ShipmentStatus.BOOKED
    origin_port: str = ""
    destination_port: str = ""
    vessel_details: Optional[VesselDetails] = None
    container_ids: List[str] = field(default_factory=list)
    estimated_departure: Optional[datetime] = None
    estimated_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    tracking_events: List[TrackingEvent] = field(default_factory=list)
    documents: List[Document] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        if not self.tracking_number:
            self.tracking_number = f"FF{datetime.now().strftime('%Y%m%d')}{self.id[:8].upper()}"
    
    def add_tracking_event(self, status: ShipmentStatus, location: str, description: str, 
                          event_time: Optional[datetime] = None, vessel_name: Optional[str] = None,
                          voyage_number: Optional[str] = None) -> TrackingEvent:
        """Add a tracking event to the shipment"""
        event = TrackingEvent(
            shipment_id=self.id,
            status=status,
            location=location,
            description=description,
            event_time=event_time or datetime.utcnow(),
            vessel_name=vessel_name,
            voyage_number=voyage_number
        )
        self.tracking_events.append(event)
        self.status = status
        self.updated_at = datetime.utcnow()
        return event
    
    def get_current_location(self) -> Optional[str]:
        """Get the current location from the latest tracking event"""
        if self.tracking_events:
            return sorted(self.tracking_events, key=lambda x: x.event_time)[-1].location
        return None
    
    def get_progress_percentage(self) -> int:
        """Calculate shipment progress as percentage"""
        status_progress = {
            ShipmentStatus.BOOKED: 10,
            ShipmentStatus.PICKUP_SCHEDULED: 20,
            ShipmentStatus.PICKED_UP: 30,
            ShipmentStatus.IN_TRANSIT: 60,
            ShipmentStatus.CUSTOMS_CLEARANCE: 80,
            ShipmentStatus.OUT_FOR_DELIVERY: 90,
            ShipmentStatus.DELIVERED: 100,
            ShipmentStatus.EXCEPTION: 0
        }
        return status_progress.get(self.status, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'tracking_number': self.tracking_number,
            'status': self.status.value,
            'origin_port': self.origin_port,
            'destination_port': self.destination_port,
            'vessel_details': self.vessel_details.to_dict() if self.vessel_details else None,
            'container_ids': self.container_ids,
            'estimated_departure': self.estimated_departure.isoformat() if self.estimated_departure else None,
            'estimated_arrival': self.estimated_arrival.isoformat() if self.estimated_arrival else None,
            'actual_departure': self.actual_departure.isoformat() if self.actual_departure else None,
            'actual_arrival': self.actual_arrival.isoformat() if self.actual_arrival else None,
            'current_location': self.get_current_location(),
            'progress_percentage': self.get_progress_percentage(),
            'tracking_events': [event.to_dict() for event in sorted(self.tracking_events, key=lambda x: x.event_time)],
            'documents': [doc.to_dict() for doc in self.documents],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class Customer:
    """Customer model (simplified for booking service)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'company_name': self.company_name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'created_at': self.created_at.isoformat()
        }

