import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, BadRequest

from models.booking import (
    Shipment, TrackingEvent, ShipmentStatus
)

class TrackingService:
    """Service for managing shipment tracking and status updates"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def get_shipment(self, shipment_id: str, user_id: str) -> Optional[Shipment]:
        """Get a shipment by ID with user access control"""
        
        # Try cache first
        cached = self.cache.get(f"shipment:{shipment_id}")
        if cached:
            shipment_data = json.loads(cached) if isinstance(cached, str) else cached
            shipment = self._dict_to_shipment(shipment_data)
            
            # Check access permissions
            if not self._can_access_shipment(shipment, user_id):
                return None
            
            return shipment
        
        # Load from database
        shipment = self._load_shipment(shipment_id)
        if not shipment:
            return None
        
        # Check access permissions
        if not self._can_access_shipment(shipment, user_id):
            return None
        
        # Cache the result
        self.cache.set(f"shipment:{shipment_id}", shipment.to_dict(), ttl=3600)
        
        return shipment
    
    def get_shipments(self, user_id: str, customer_id: Optional[str] = None,
                     status: Optional[str] = None, page: int = 1, 
                     per_page: int = 20) -> Dict[str, Any]:
        """Get shipments for a user with pagination"""
        
        # Build query filters
        filters = {}
        if customer_id:
            filters['customer_id'] = customer_id
        if status:
            filters['status'] = status
        
        # Add user access control
        if not self._is_admin(user_id):
            filters['user_id'] = user_id
        
        # Get shipments from database
        shipments_data = self._query_shipments(filters, page, per_page)
        
        shipments = []
        for shipment_data in shipments_data['items']:
            shipment = self._dict_to_shipment(shipment_data)
            shipments.append(shipment)
        
        return {
            'items': shipments,
            'page': page,
            'per_page': per_page,
            'total': shipments_data['total'],
            'pages': (shipments_data['total'] + per_page - 1) // per_page
        }
    
    def get_all_shipments(self, status: Optional[str] = None,
                         customer_id: Optional[str] = None,
                         page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get all shipments (admin only)"""
        
        filters = {}
        if status:
            filters['status'] = status
        if customer_id:
            filters['customer_id'] = customer_id
        
        # Get shipments from database
        shipments_data = self._query_shipments(filters, page, per_page)
        
        shipments = []
        for shipment_data in shipments_data['items']:
            shipment = self._dict_to_shipment(shipment_data)
            shipments.append(shipment)
        
        return {
            'items': shipments,
            'page': page,
            'per_page': per_page,
            'total': shipments_data['total'],
            'pages': (shipments_data['total'] + per_page - 1) // per_page
        }
    
    def track_shipment(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Track a shipment by tracking number (public endpoint)"""
        
        # Try cache first
        cached = self.cache.get(f"tracking:{tracking_number}")
        if cached:
            return json.loads(cached) if isinstance(cached, str) else cached
        
        # Load from database
        shipment = self._load_shipment_by_tracking(tracking_number)
        if not shipment:
            return None
        
        # Prepare tracking information
        tracking_info = {
            'tracking_number': shipment.tracking_number,
            'status': shipment.status.value,
            'origin_port': shipment.origin_port,
            'destination_port': shipment.destination_port,
            'current_location': shipment.get_current_location(),
            'progress_percentage': shipment.get_progress_percentage(),
            'estimated_arrival': shipment.estimated_arrival.isoformat() if shipment.estimated_arrival else None,
            'actual_arrival': shipment.actual_arrival.isoformat() if shipment.actual_arrival else None,
            'vessel_details': shipment.vessel_details.to_dict() if shipment.vessel_details else None,
            'tracking_events': [event.to_dict() for event in sorted(shipment.tracking_events, key=lambda x: x.event_time)],
            'last_updated': shipment.updated_at.isoformat()
        }
        
        # Cache the tracking info
        self.cache.set(f"tracking:{tracking_number}", tracking_info, ttl=300)  # 5 minutes
        
        return tracking_info
    
    def add_tracking_event(self, shipment_id: str, status: str, location: str,
                          description: str, event_time: Optional[str] = None,
                          vessel_name: Optional[str] = None,
                          voyage_number: Optional[str] = None) -> TrackingEvent:
        """Add a tracking event to a shipment"""
        
        # Load shipment
        shipment = self._load_shipment(shipment_id)
        if not shipment:
            raise NotFound("Shipment not found")
        
        # Parse event time
        parsed_time = None
        if event_time:
            try:
                parsed_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
            except:
                parsed_time = datetime.utcnow()
        else:
            parsed_time = datetime.utcnow()
        
        # Create tracking event
        try:
            shipment_status = ShipmentStatus(status)
        except ValueError:
            raise BadRequest(f"Invalid status: {status}")
        
        tracking_event = shipment.add_tracking_event(
            status=shipment_status,
            location=location,
            description=description,
            event_time=parsed_time,
            vessel_name=vessel_name,
            voyage_number=voyage_number
        )
        
        # Update estimated arrival if provided
        if tracking_event.estimated_arrival:
            shipment.estimated_arrival = tracking_event.estimated_arrival
        
        # Save to database
        self._save_shipment(shipment)
        
        # Update cache
        self.cache.set(f"shipment:{shipment_id}", shipment.to_dict(), ttl=3600)
        self.cache.delete(f"tracking:{shipment.tracking_number}")  # Clear tracking cache
        
        # Publish tracking event
        self.event_producer.publish('shipment.tracking_updated', {
            'shipment_id': shipment_id,
            'tracking_number': shipment.tracking_number,
            'status': status,
            'location': location,
            'description': description,
            'event_time': parsed_time.isoformat(),
            'vessel_name': vessel_name,
            'voyage_number': voyage_number,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Send notifications for important status changes
        if shipment_status in [ShipmentStatus.PICKED_UP, ShipmentStatus.IN_TRANSIT, 
                              ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.DELIVERED]:
            self.event_producer.publish('shipment.status_changed', {
                'shipment_id': shipment_id,
                'tracking_number': shipment.tracking_number,
                'old_status': shipment.status.value,
                'new_status': status,
                'location': location,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        return tracking_event
    
    def update_shipment(self, shipment_id: str, updates: Dict[str, Any]) -> Shipment:
        """Update shipment details (admin only)"""
        
        # Load shipment
        shipment = self._load_shipment(shipment_id)
        if not shipment:
            raise NotFound("Shipment not found")
        
        # Apply updates
        if 'estimated_departure' in updates:
            shipment.estimated_departure = self._parse_datetime(updates['estimated_departure'])
        
        if 'estimated_arrival' in updates:
            shipment.estimated_arrival = self._parse_datetime(updates['estimated_arrival'])
        
        if 'actual_departure' in updates:
            shipment.actual_departure = self._parse_datetime(updates['actual_departure'])
        
        if 'actual_arrival' in updates:
            shipment.actual_arrival = self._parse_datetime(updates['actual_arrival'])
        
        if 'vessel_details' in updates:
            vessel_data = updates['vessel_details']
            from models.booking import VesselDetails
            shipment.vessel_details = VesselDetails(**vessel_data)
        
        shipment.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_shipment(shipment)
        
        # Update cache
        self.cache.set(f"shipment:{shipment_id}", shipment.to_dict(), ttl=3600)
        self.cache.delete(f"tracking:{shipment.tracking_number}")  # Clear tracking cache
        
        # Publish update event
        self.event_producer.publish('shipment.updated', {
            'shipment_id': shipment_id,
            'tracking_number': shipment.tracking_number,
            'updates': updates,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return shipment
    
    def get_shipment_analytics(self, date_from: Optional[str] = None,
                              date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get shipment analytics and statistics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_shipment_analytics_data(start_date, end_date)
        
        return {
            'total_shipments': analytics.get('total_shipments', 0),
            'active_shipments': analytics.get('active_shipments', 0),
            'delivered_shipments': analytics.get('delivered_shipments', 0),
            'delayed_shipments': analytics.get('delayed_shipments', 0),
            'average_transit_time': analytics.get('average_transit_time', 0),
            'on_time_delivery_rate': analytics.get('on_time_delivery_rate', 0),
            'status_distribution': analytics.get('status_distribution', {}),
            'top_routes': analytics.get('top_routes', []),
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            }
        }
    
    def _can_access_shipment(self, shipment: Shipment, user_id: str) -> bool:
        """Check if user can access the shipment"""
        # In a real implementation, this would check user permissions
        # For now, allow access if user is associated with the booking or is admin
        return self._is_admin(user_id) or self._user_owns_shipment(shipment, user_id)
    
    def _user_owns_shipment(self, shipment: Shipment, user_id: str) -> bool:
        """Check if user owns the shipment"""
        # This would check the booking ownership
        # For now, return True for demo purposes
        return True
    
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
    def _load_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Load shipment from database"""
        # Mock implementation - return a sample shipment for demo
        if shipment_id == "demo":
            from models.booking import VesselDetails
            shipment = Shipment(
                id=shipment_id,
                booking_id="demo-booking",
                tracking_number="FF20240819DEMO123",
                status=ShipmentStatus.IN_TRANSIT,
                origin_port="USNYC",
                destination_port="CNSHA",
                vessel_details=VesselDetails(
                    vessel_name="MSC OSCAR",
                    voyage_number="240W",
                    eta=datetime.utcnow() + timedelta(days=7)
                )
            )
            
            # Add some tracking events
            shipment.add_tracking_event(
                ShipmentStatus.BOOKED,
                "New York Port",
                "Shipment booked and confirmed",
                datetime.utcnow() - timedelta(days=5)
            )
            
            shipment.add_tracking_event(
                ShipmentStatus.PICKED_UP,
                "New York Port",
                "Container picked up from shipper",
                datetime.utcnow() - timedelta(days=4)
            )
            
            shipment.add_tracking_event(
                ShipmentStatus.IN_TRANSIT,
                "Atlantic Ocean",
                "Vessel departed from New York",
                datetime.utcnow() - timedelta(days=3)
            )
            
            return shipment
        
        return None
    
    def _load_shipment_by_tracking(self, tracking_number: str) -> Optional[Shipment]:
        """Load shipment by tracking number"""
        # Mock implementation
        if tracking_number == "FF20240819DEMO123":
            return self._load_shipment("demo")
        return None
    
    def _query_shipments(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query shipments from database"""
        # Mock implementation - return demo data
        demo_shipment = self._load_shipment("demo")
        if demo_shipment:
            return {
                'items': [demo_shipment.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _save_shipment(self, shipment: Shipment):
        """Save shipment to database"""
        # Mock implementation
        pass
    
    def _get_shipment_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get analytics data from database"""
        # Mock implementation
        return {
            'total_shipments': 150,
            'active_shipments': 45,
            'delivered_shipments': 98,
            'delayed_shipments': 7,
            'average_transit_time': 12.5,
            'on_time_delivery_rate': 94.2,
            'status_distribution': {
                'BOOKED': 15,
                'IN_TRANSIT': 30,
                'DELIVERED': 98,
                'EXCEPTION': 7
            },
            'top_routes': [
                {'route': 'USNYC-CNSHA', 'count': 25},
                {'route': 'USLAX-JPYOK', 'count': 18},
                {'route': 'DEHAM-USNYC', 'count': 15}
            ]
        }
    
    def _dict_to_shipment(self, data: Dict) -> Shipment:
        """Convert dictionary to Shipment object"""
        # This would properly reconstruct the Shipment object
        # For now, return a basic shipment
        shipment = Shipment()
        shipment.id = data.get('id', '')
        shipment.booking_id = data.get('booking_id', '')
        shipment.tracking_number = data.get('tracking_number', '')
        shipment.status = ShipmentStatus(data.get('status', 'BOOKED'))
        shipment.origin_port = data.get('origin_port', '')
        shipment.destination_port = data.get('destination_port', '')
        return shipment

