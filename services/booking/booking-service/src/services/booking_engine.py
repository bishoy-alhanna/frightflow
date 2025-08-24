import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.booking import (
    Booking, Shipment, Container, Contact, VesselDetails,
    BookingStatus, ShipmentStatus, ContainerStatus, ContainerType
)
from models.customer import Customer

class BookingEngine:
    """Core booking engine for managing bookings and shipments"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_booking(self, quote_id: str, customer_id: str, 
                      special_instructions: Optional[str] = None,
                      pickup_contact: Optional[Dict] = None,
                      delivery_contact: Optional[Dict] = None) -> Booking:
        """Create a new booking from an accepted quote"""
        
        # Validate quote exists and is accepted
        quote = self._get_quote(quote_id)
        if not quote:
            raise NotFound("Quote not found")
        
        if quote.get('status') != 'ACCEPTED':
            raise BadRequest("Quote must be accepted before booking")
        
        # Validate customer exists
        customer = self._get_customer(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        # Create booking
        booking = Booking(
            quote_id=quote_id,
            customer_id=customer_id,
            special_instructions=special_instructions,
            pickup_contact=Contact(**pickup_contact) if pickup_contact else None,
            delivery_contact=Contact(**delivery_contact) if delivery_contact else None,
            created_by=customer_id  # In real implementation, this would be the authenticated user
        )
        
        # Save to database
        self._save_booking(booking)
        
        # Cache the booking
        self.cache.set(f"booking:{booking.id}", booking.to_dict(), ttl=3600)
        
        # Publish booking created event
        self.event_producer.publish('booking.created', {
            'booking_id': booking.id,
            'quote_id': quote_id,
            'customer_id': customer_id,
            'booking_number': booking.booking_number,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return booking
    
    def get_booking(self, booking_id: str, user_id: str) -> Optional[Booking]:
        """Get a booking by ID with user access control"""
        
        # Try cache first
        cached = self.cache.get(f"booking:{booking_id}")
        if cached:
            booking_data = json.loads(cached) if isinstance(cached, str) else cached
            booking = self._dict_to_booking(booking_data)
            
            # Check access permissions
            if not self._can_access_booking(booking, user_id):
                return None
            
            return booking
        
        # Load from database
        booking = self._load_booking(booking_id)
        if not booking:
            return None
        
        # Check access permissions
        if not self._can_access_booking(booking, user_id):
            return None
        
        # Cache the result
        self.cache.set(f"booking:{booking_id}", booking.to_dict(), ttl=3600)
        
        return booking
    
    def get_bookings(self, user_id: str, customer_id: Optional[str] = None,
                    status: Optional[str] = None, page: int = 1, 
                    per_page: int = 20) -> Dict[str, Any]:
        """Get bookings for a user with pagination"""
        
        # Build query filters
        filters = {'created_by': user_id}
        if customer_id:
            filters['customer_id'] = customer_id
        if status:
            filters['status'] = status
        
        # Get bookings from database
        bookings_data = self._query_bookings(filters, page, per_page)
        
        bookings = []
        for booking_data in bookings_data['items']:
            booking = self._dict_to_booking(booking_data)
            bookings.append(booking)
        
        return {
            'items': bookings,
            'page': page,
            'per_page': per_page,
            'total': bookings_data['total'],
            'pages': (bookings_data['total'] + per_page - 1) // per_page
        }
    
    def get_all_bookings(self, status: Optional[str] = None,
                        customer_id: Optional[str] = None,
                        page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get all bookings (admin only)"""
        
        filters = {}
        if status:
            filters['status'] = status
        if customer_id:
            filters['customer_id'] = customer_id
        
        # Get bookings from database
        bookings_data = self._query_bookings(filters, page, per_page)
        
        bookings = []
        for booking_data in bookings_data['items']:
            booking = self._dict_to_booking(booking_data)
            bookings.append(booking)
        
        return {
            'items': bookings,
            'page': page,
            'per_page': per_page,
            'total': bookings_data['total'],
            'pages': (bookings_data['total'] + per_page - 1) // per_page
        }
    
    def confirm_booking(self, booking_id: str, user_id: str,
                       vessel_details: Optional[Dict] = None,
                       container_details: Optional[List[Dict]] = None) -> Shipment:
        """Confirm a booking and create a shipment"""
        
        # Get the booking
        booking = self.get_booking(booking_id, user_id)
        if not booking:
            raise NotFound("Booking not found")
        
        if booking.status != BookingStatus.PENDING:
            raise Conflict("Booking is not in pending status")
        
        # Get the original quote for shipment details
        quote = self._get_quote(booking.quote_id)
        if not quote:
            raise NotFound("Original quote not found")
        
        # Allocate containers if needed
        container_ids = []
        if container_details:
            container_ids = self._allocate_containers(container_details)
        
        # Create vessel details
        vessel = None
        if vessel_details:
            vessel = VesselDetails(**vessel_details)
        
        # Create shipment
        shipment = Shipment(
            booking_id=booking_id,
            origin_port=quote.get('origin_port', ''),
            destination_port=quote.get('destination_port', ''),
            vessel_details=vessel,
            container_ids=container_ids,
            estimated_departure=self._parse_datetime(vessel_details.get('etd')) if vessel_details else None,
            estimated_arrival=self._parse_datetime(vessel_details.get('eta')) if vessel_details else None
        )
        
        # Add initial tracking event
        shipment.add_tracking_event(
            status=ShipmentStatus.BOOKED,
            location=quote.get('origin_port', 'Origin'),
            description="Shipment booked and confirmed"
        )
        
        # Update booking status
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = datetime.utcnow()
        booking.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_booking(booking)
        self._save_shipment(shipment)
        
        # Update cache
        self.cache.set(f"booking:{booking_id}", booking.to_dict(), ttl=3600)
        self.cache.set(f"shipment:{shipment.id}", shipment.to_dict(), ttl=3600)
        self.cache.set(f"tracking:{shipment.tracking_number}", shipment.to_dict(), ttl=3600)
        
        # Publish events
        self.event_producer.publish('booking.confirmed', {
            'booking_id': booking_id,
            'shipment_id': shipment.id,
            'tracking_number': shipment.tracking_number,
            'customer_id': booking.customer_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        self.event_producer.publish('shipment.created', {
            'shipment_id': shipment.id,
            'booking_id': booking_id,
            'tracking_number': shipment.tracking_number,
            'origin_port': shipment.origin_port,
            'destination_port': shipment.destination_port,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return shipment
    
    def get_containers(self, status: Optional[str] = None,
                      location: Optional[str] = None,
                      page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get container inventory"""
        
        filters = {}
        if status:
            filters['status'] = status
        if location:
            filters['location'] = location
        
        # Get containers from database
        containers_data = self._query_containers(filters, page, per_page)
        
        containers = []
        for container_data in containers_data['items']:
            container = self._dict_to_container(container_data)
            containers.append(container)
        
        return {
            'items': containers,
            'page': page,
            'per_page': per_page,
            'total': containers_data['total'],
            'pages': (containers_data['total'] + per_page - 1) // per_page
        }
    
    def _allocate_containers(self, container_requirements: List[Dict]) -> List[str]:
        """Allocate containers based on requirements"""
        allocated_containers = []
        
        for requirement in container_requirements:
            container_type = ContainerType(requirement.get('type', 'DRY_20'))
            quantity = requirement.get('quantity', 1)
            
            # Find available containers
            available = self._find_available_containers(container_type, quantity)
            if len(available) < quantity:
                raise BadRequest(f"Not enough {container_type.value} containers available")
            
            # Allocate containers
            for container in available[:quantity]:
                container.status = ContainerStatus.ALLOCATED
                container.updated_at = datetime.utcnow()
                self._save_container(container)
                allocated_containers.append(container.id)
        
        return allocated_containers
    
    def _find_available_containers(self, container_type: ContainerType, 
                                  quantity: int) -> List[Container]:
        """Find available containers of specified type"""
        # This would query the database for available containers
        # For now, return mock containers
        containers = []
        for i in range(quantity):
            container = Container(
                container_number=f"{container_type.value}-{uuid.uuid4().hex[:8].upper()}",
                container_type=container_type,
                status=ContainerStatus.AVAILABLE,
                location="Port Warehouse"
            )
            containers.append(container)
        return containers
    
    def _get_quote(self, quote_id: str) -> Optional[Dict]:
        """Get quote from quotation service"""
        # This would make an API call to the quotation service
        # For now, return a mock quote
        return {
            'id': quote_id,
            'status': 'ACCEPTED',
            'origin_port': 'USNYC',
            'destination_port': 'CNSHA',
            'service_type': 'FCL',
            'total_amount': 2500.00
        }
    
    def _get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer information"""
        # This would query the customer database or call CRM service
        # For now, return a mock customer
        return Customer(
            id=customer_id,
            company_name="Acme Corp",
            contact_name="John Doe",
            email="john@acme.com",
            phone="+1-555-0123"
        )
    
    def _can_access_booking(self, booking: Booking, user_id: str) -> bool:
        """Check if user can access the booking"""
        # In a real implementation, this would check user permissions
        # For now, allow access if user created the booking or is admin
        return booking.created_by == user_id or self._is_admin(user_id)
    
    def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        # This would check user roles
        # For now, return True for demo purposes
        return True
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _save_booking(self, booking: Booking):
        """Save booking to database"""
        # Mock implementation
        pass
    
    def _load_booking(self, booking_id: str) -> Optional[Booking]:
        """Load booking from database"""
        # Mock implementation - return None for now
        return None
    
    def _query_bookings(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query bookings from database"""
        # Mock implementation
        return {'items': [], 'total': 0}
    
    def _save_shipment(self, shipment: Shipment):
        """Save shipment to database"""
        # Mock implementation
        pass
    
    def _save_container(self, container: Container):
        """Save container to database"""
        # Mock implementation
        pass
    
    def _query_containers(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query containers from database"""
        # Mock implementation
        return {'items': [], 'total': 0}
    
    def _dict_to_booking(self, data: Dict) -> Booking:
        """Convert dictionary to Booking object"""
        # This would properly reconstruct the Booking object
        # For now, return a basic booking
        booking = Booking()
        booking.id = data.get('id', '')
        booking.quote_id = data.get('quote_id', '')
        booking.customer_id = data.get('customer_id', '')
        booking.booking_number = data.get('booking_number', '')
        booking.status = BookingStatus(data.get('status', 'PENDING'))
        return booking
    
    def _dict_to_container(self, data: Dict) -> Container:
        """Convert dictionary to Container object"""
        container = Container()
        container.id = data.get('id', '')
        container.container_number = data.get('container_number', '')
        container.container_type = ContainerType(data.get('container_type', 'DRY_20'))
        container.status = ContainerStatus(data.get('status', 'AVAILABLE'))
        return container

