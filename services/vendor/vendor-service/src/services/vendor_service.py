import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.vendor import Vendor, VendorContact, VendorService, VendorRating, VendorStatus, ServiceType, ContactType

class VendorService:
    """Service for managing vendors"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_vendor(self, company_name: str, contact_name: str, email: str,
                     phone: Optional[str] = None, address: Optional[str] = None,
                     city: Optional[str] = None, country: Optional[str] = None,
                     postal_code: Optional[str] = None, tax_id: Optional[str] = None,
                     service_types: List[str] = None, capabilities: List[str] = None,
                     certifications: List[str] = None, created_by: str = "") -> Vendor:
        """Create a new vendor"""
        
        # Check if vendor with same email already exists
        existing = self._find_vendor_by_email(email)
        if existing:
            raise Conflict("Vendor with this email already exists")
        
        # Parse service types
        parsed_service_types = []
        if service_types:
            for st in service_types:
                try:
                    parsed_service_types.append(ServiceType(st))
                except ValueError:
                    raise BadRequest(f"Invalid service type: {st}")
        
        # Create vendor
        vendor = Vendor(
            company_name=company_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            country=country,
            postal_code=postal_code,
            tax_id=tax_id,
            service_types=parsed_service_types,
            capabilities=capabilities or [],
            certifications=certifications or [],
            created_by=created_by
        )
        
        # Add primary contact
        primary_contact = VendorContact(
            vendor_id=vendor.id,
            contact_type=ContactType.PRIMARY,
            name=contact_name,
            email=email,
            phone=phone,
            is_primary=True
        )
        vendor.add_contact(primary_contact)
        
        # Save to database
        self._save_vendor(vendor)
        
        # Cache the vendor
        self.cache.set(f"vendor:{vendor.id}", vendor.to_dict(), ttl=3600)
        
        # Publish vendor created event
        self.event_producer.publish('vendor.created', {
            'vendor_id': vendor.id,
            'vendor_number': vendor.vendor_number,
            'company_name': vendor.company_name,
            'email': vendor.email,
            'service_types': [st.value for st in vendor.service_types],
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return vendor
    
    def get_vendor(self, vendor_id: str) -> Optional[Vendor]:
        """Get a vendor by ID"""
        
        # Try cache first
        cached = self.cache.get(f"vendor:{vendor_id}")
        if cached:
            vendor_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_vendor(vendor_data)
        
        # Load from database
        vendor = self._load_vendor(vendor_id)
        if vendor:
            # Cache the result
            self.cache.set(f"vendor:{vendor_id}", vendor.to_dict(), ttl=3600)
        
        return vendor
    
    def get_vendors(self, search: str = "", status: Optional[str] = None,
                   service_type: Optional[str] = None, country: Optional[str] = None,
                   page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get vendors with filtering and pagination"""
        
        # Build query filters
        filters = {}
        if search:
            filters['search'] = search
        if status:
            filters['status'] = status
        if service_type:
            filters['service_type'] = service_type
        if country:
            filters['country'] = country
        
        # Get vendors from database
        vendors_data = self._query_vendors(filters, page, per_page)
        
        vendors = []
        for vendor_data in vendors_data['items']:
            vendor = self._dict_to_vendor(vendor_data)
            vendors.append(vendor)
        
        return {
            'items': vendors,
            'page': page,
            'per_page': per_page,
            'total': vendors_data['total'],
            'pages': (vendors_data['total'] + per_page - 1) // per_page
        }
    
    def update_vendor(self, vendor_id: str, updates: Dict[str, Any],
                     updated_by: str) -> Vendor:
        """Update vendor information"""
        
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            raise NotFound("Vendor not found")
        
        # Apply updates
        updatable_fields = [
            'company_name', 'contact_name', 'email', 'phone', 'mobile', 'website',
            'address', 'city', 'state', 'country', 'postal_code', 'tax_id',
            'business_license', 'insurance_info', 'capabilities', 'certifications',
            'coverage_areas', 'payment_terms', 'currency', 'credit_limit',
            'account_manager', 'notes'
        ]
        
        for field in updatable_fields:
            if field in updates:
                setattr(vendor, field, updates[field])
        
        # Handle service types separately
        if 'service_types' in updates:
            parsed_service_types = []
            for st in updates['service_types']:
                try:
                    parsed_service_types.append(ServiceType(st))
                except ValueError:
                    raise BadRequest(f"Invalid service type: {st}")
            vendor.service_types = parsed_service_types
        
        # Handle tags separately
        if 'tags' in updates:
            vendor.tags = updates['tags'] if isinstance(updates['tags'], list) else []
        
        vendor.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_vendor(vendor)
        
        # Update cache
        self.cache.set(f"vendor:{vendor_id}", vendor.to_dict(), ttl=3600)
        
        # Publish vendor updated event
        self.event_producer.publish('vendor.updated', {
            'vendor_id': vendor_id,
            'vendor_number': vendor.vendor_number,
            'updates': updates,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return vendor
    
    def update_vendor_status(self, vendor_id: str, status: str,
                           reason: Optional[str] = None, updated_by: str = "") -> Vendor:
        """Update vendor status"""
        
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            raise NotFound("Vendor not found")
        
        # Validate status
        try:
            new_status = VendorStatus(status)
        except ValueError:
            raise BadRequest(f"Invalid status: {status}")
        
        old_status = vendor.status
        vendor.status = new_status
        
        if new_status == VendorStatus.ACTIVE:
            vendor.activate()
        elif new_status == VendorStatus.INACTIVE:
            vendor.deactivate(reason)
        elif new_status == VendorStatus.SUSPENDED:
            vendor.suspend(reason or "No reason provided")
        
        # Save to database
        self._save_vendor(vendor)
        
        # Update cache
        self.cache.set(f"vendor:{vendor_id}", vendor.to_dict(), ttl=3600)
        
        # Publish status change event
        self.event_producer.publish('vendor.status_changed', {
            'vendor_id': vendor_id,
            'vendor_number': vendor.vendor_number,
            'old_status': old_status.value,
            'new_status': new_status.value,
            'reason': reason,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return vendor
    
    def create_vendor_rating(self, vendor_id: str, shipment_id: str,
                           overall_rating: float, quality_rating: Optional[float] = None,
                           timeliness_rating: Optional[float] = None,
                           communication_rating: Optional[float] = None,
                           cost_rating: Optional[float] = None,
                           comments: Optional[str] = None,
                           rated_by: str = "") -> VendorRating:
        """Create a rating for a vendor"""
        
        # Verify vendor exists
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            raise NotFound("Vendor not found")
        
        # Validate rating values
        if not (1.0 <= overall_rating <= 5.0):
            raise BadRequest("Overall rating must be between 1.0 and 5.0")
        
        # Create rating
        rating = VendorRating(
            vendor_id=vendor_id,
            shipment_id=shipment_id,
            overall_rating=overall_rating,
            quality_rating=quality_rating,
            timeliness_rating=timeliness_rating,
            communication_rating=communication_rating,
            cost_rating=cost_rating,
            comments=comments,
            rated_by=rated_by
        )
        
        # Save to database
        self._save_vendor_rating(rating)
        
        # Update vendor's average rating
        vendor.update_rating(overall_rating)
        self._save_vendor(vendor)
        
        # Update cache
        self.cache.set(f"vendor:{vendor_id}", vendor.to_dict(), ttl=3600)
        
        # Publish rating created event
        self.event_producer.publish('vendor.rating_created', {
            'vendor_id': vendor_id,
            'rating_id': rating.id,
            'shipment_id': shipment_id,
            'overall_rating': overall_rating,
            'rated_by': rated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return rating
    
    def get_vendor_ratings(self, vendor_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get ratings for a vendor"""
        
        # Verify vendor exists
        vendor = self.get_vendor(vendor_id)
        if not vendor:
            raise NotFound("Vendor not found")
        
        # Get ratings from database
        ratings_data = self._query_vendor_ratings(vendor_id, page, per_page)
        
        ratings = []
        for rating_data in ratings_data['items']:
            rating = self._dict_to_vendor_rating(rating_data)
            ratings.append(rating)
        
        return {
            'items': ratings,
            'page': page,
            'per_page': per_page,
            'total': ratings_data['total'],
            'pages': (ratings_data['total'] + per_page - 1) // per_page
        }
    
    def find_qualified_vendors(self, service_type: str, origin: str, destination: str,
                             min_rating: float = 3.0) -> List[Vendor]:
        """Find vendors qualified for a specific service"""
        
        # Parse service type
        try:
            parsed_service_type = ServiceType(service_type)
        except ValueError:
            raise BadRequest(f"Invalid service type: {service_type}")
        
        # Get qualified vendors from database
        vendors_data = self._query_qualified_vendors(parsed_service_type, origin, destination, min_rating)
        
        vendors = []
        for vendor_data in vendors_data:
            vendor = self._dict_to_vendor(vendor_data)
            if vendor.is_qualified_for_service(parsed_service_type, origin, destination):
                vendors.append(vendor)
        
        # Sort by performance score
        vendors.sort(key=lambda v: v.calculate_performance_score(), reverse=True)
        
        return vendors
    
    def get_vendor_analytics(self, date_from: Optional[str] = None,
                           date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get vendor analytics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_vendor_analytics_data(start_date, end_date)
        
        return {
            'total_vendors': analytics.get('total_vendors', 0),
            'active_vendors': analytics.get('active_vendors', 0),
            'new_vendors': analytics.get('new_vendors', 0),
            'average_rating': analytics.get('average_rating', 0),
            'vendors_by_service_type': analytics.get('vendors_by_service_type', {}),
            'vendors_by_country': analytics.get('vendors_by_country', {}),
            'vendors_by_status': analytics.get('vendors_by_status', {}),
            'top_rated_vendors': analytics.get('top_rated_vendors', []),
            'performance_distribution': analytics.get('performance_distribution', {}),
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            }
        }
    
    def create_onboarding_application(self, company_name: str, contact_name: str,
                                    email: str, phone: str, address: Optional[str] = None,
                                    city: Optional[str] = None, country: Optional[str] = None,
                                    service_types: List[str] = None,
                                    capabilities: List[str] = None,
                                    certifications: List[str] = None,
                                    business_license: Optional[str] = None,
                                    insurance_info: Optional[str] = None,
                                    references: List[Dict] = None) -> Dict[str, Any]:
        """Create a vendor onboarding application"""
        
        # Check if application with same email already exists
        existing = self._find_onboarding_application_by_email(email)
        if existing and existing['status'] == 'PENDING':
            raise Conflict("Pending application with this email already exists")
        
        # Create application
        application = {
            'id': str(uuid.uuid4()),
            'application_number': f"APP{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}",
            'company_name': company_name,
            'contact_name': contact_name,
            'email': email,
            'phone': phone,
            'address': address,
            'city': city,
            'country': country,
            'service_types': service_types or [],
            'capabilities': capabilities or [],
            'certifications': certifications or [],
            'business_license': business_license,
            'insurance_info': insurance_info,
            'references': references or [],
            'status': 'PENDING',
            'submitted_at': datetime.utcnow().isoformat(),
            'notes': None
        }
        
        # Save to database
        self._save_onboarding_application(application)
        
        # Publish application submitted event
        self.event_producer.publish('vendor.application_submitted', {
            'application_id': application['id'],
            'application_number': application['application_number'],
            'company_name': company_name,
            'email': email,
            'service_types': service_types,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return application
    
    def get_onboarding_applications(self, status: str = "PENDING",
                                  page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get vendor onboarding applications"""
        
        # Get applications from database
        applications_data = self._query_onboarding_applications(status, page, per_page)
        
        return {
            'items': applications_data['items'],
            'page': page,
            'per_page': per_page,
            'total': applications_data['total'],
            'pages': (applications_data['total'] + per_page - 1) // per_page
        }
    
    def approve_onboarding_application(self, application_id: str,
                                     approved_by: str, notes: Optional[str] = None) -> Vendor:
        """Approve a vendor onboarding application"""
        
        # Get application
        application = self._load_onboarding_application(application_id)
        if not application:
            raise NotFound("Application not found")
        
        if application['status'] != 'PENDING':
            raise Conflict("Application is not pending approval")
        
        # Create vendor from application
        vendor = self.create_vendor(
            company_name=application['company_name'],
            contact_name=application['contact_name'],
            email=application['email'],
            phone=application['phone'],
            address=application.get('address'),
            city=application.get('city'),
            country=application.get('country'),
            service_types=application.get('service_types', []),
            capabilities=application.get('capabilities', []),
            certifications=application.get('certifications', []),
            created_by=approved_by
        )
        
        # Update application status
        application['status'] = 'APPROVED'
        application['approved_by'] = approved_by
        application['approved_at'] = datetime.utcnow().isoformat()
        application['vendor_id'] = vendor.id
        application['notes'] = notes
        
        self._save_onboarding_application(application)
        
        # Publish application approved event
        self.event_producer.publish('vendor.application_approved', {
            'application_id': application_id,
            'vendor_id': vendor.id,
            'vendor_number': vendor.vendor_number,
            'approved_by': approved_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return vendor
    
    def export_vendors(self, filters: Dict[str, Any]) -> str:
        """Export vendors to CSV"""
        
        # Get vendors based on filters
        vendors_data = self._query_vendors_for_export(filters)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Vendor Number', 'Company Name', 'Contact Name', 'Email', 'Phone',
            'Country', 'Service Types', 'Status', 'Average Rating', 'Total Shipments',
            'On Time Delivery Rate', 'Performance Score', 'Created At'
        ])
        
        # Write data
        for vendor_data in vendors_data:
            writer.writerow([
                vendor_data.get('vendor_number', ''),
                vendor_data.get('company_name', ''),
                vendor_data.get('contact_name', ''),
                vendor_data.get('email', ''),
                vendor_data.get('phone', ''),
                vendor_data.get('country', ''),
                ', '.join(vendor_data.get('service_types', [])),
                vendor_data.get('status', ''),
                vendor_data.get('average_rating', 0),
                vendor_data.get('total_shipments', 0),
                vendor_data.get('on_time_delivery_rate', 0),
                vendor_data.get('performance_score', 0),
                vendor_data.get('created_at', '')
            ])
        
        return output.getvalue()
    
    def _find_vendor_by_email(self, email: str) -> Optional[Vendor]:
        """Find vendor by email"""
        # This would query the database
        # For now, return None
        return None
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _save_vendor(self, vendor: Vendor):
        """Save vendor to database"""
        # Mock implementation
        pass
    
    def _load_vendor(self, vendor_id: str) -> Optional[Vendor]:
        """Load vendor from database"""
        # Mock implementation - return a sample vendor for demo
        if vendor_id == "demo":
            vendor = Vendor(
                id=vendor_id,
                company_name="Global Logistics Solutions",
                contact_name="Mike Johnson",
                email="mike.johnson@globallogistics.com",
                phone="+1-555-0789",
                address="456 Shipping Lane",
                city="Los Angeles",
                country="USA",
                service_types=[ServiceType.OCEAN_FREIGHT, ServiceType.AIR_FREIGHT],
                status=VendorStatus.ACTIVE,
                average_rating=4.2,
                total_ratings=25,
                total_shipments=150,
                on_time_delivery_rate=92.5
            )
            return vendor
        return None
    
    def _query_vendors(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query vendors from database"""
        # Mock implementation
        demo_vendor = self._load_vendor("demo")
        if demo_vendor:
            return {
                'items': [demo_vendor.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _query_vendors_for_export(self, filters: Dict) -> List[Dict]:
        """Query vendors for export"""
        # Mock implementation
        demo_vendor = self._load_vendor("demo")
        if demo_vendor:
            return [demo_vendor.to_dict()]
        return []
    
    def _save_vendor_rating(self, rating: VendorRating):
        """Save vendor rating to database"""
        # Mock implementation
        pass
    
    def _query_vendor_ratings(self, vendor_id: str, page: int, per_page: int) -> Dict:
        """Query vendor ratings"""
        # Mock implementation
        return {'items': [], 'total': 0}
    
    def _query_qualified_vendors(self, service_type: ServiceType, origin: str, destination: str, min_rating: float) -> List[Dict]:
        """Query qualified vendors"""
        # Mock implementation
        demo_vendor = self._load_vendor("demo")
        if demo_vendor and service_type in demo_vendor.service_types:
            return [demo_vendor.to_dict()]
        return []
    
    def _get_vendor_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get vendor analytics data from database"""
        # Mock implementation
        return {
            'total_vendors': 45,
            'active_vendors': 38,
            'new_vendors': 3,
            'average_rating': 4.1,
            'vendors_by_service_type': {
                'OCEAN_FREIGHT': 25,
                'AIR_FREIGHT': 20,
                'LAND_FREIGHT': 15,
                'CUSTOMS_CLEARANCE': 12,
                'WAREHOUSING': 8
            },
            'vendors_by_country': {
                'USA': 15,
                'China': 8,
                'Germany': 6,
                'Singapore': 5,
                'UK': 4,
                'Other': 7
            },
            'vendors_by_status': {
                'ACTIVE': 38,
                'PENDING_APPROVAL': 4,
                'INACTIVE': 2,
                'SUSPENDED': 1
            },
            'top_rated_vendors': [
                {'name': 'Global Logistics Solutions', 'rating': 4.8},
                {'name': 'Ocean Express', 'rating': 4.6},
                {'name': 'Air Cargo Pro', 'rating': 4.5}
            ],
            'performance_distribution': {
                '90-100': 12,
                '80-89': 15,
                '70-79': 8,
                '60-69': 3,
                'Below 60': 2
            }
        }
    
    def _save_onboarding_application(self, application: Dict):
        """Save onboarding application to database"""
        # Mock implementation
        pass
    
    def _load_onboarding_application(self, application_id: str) -> Optional[Dict]:
        """Load onboarding application from database"""
        # Mock implementation
        return None
    
    def _find_onboarding_application_by_email(self, email: str) -> Optional[Dict]:
        """Find onboarding application by email"""
        # Mock implementation
        return None
    
    def _query_onboarding_applications(self, status: str, page: int, per_page: int) -> Dict:
        """Query onboarding applications"""
        # Mock implementation
        return {'items': [], 'total': 0}
    
    def _dict_to_vendor(self, data: Dict) -> Vendor:
        """Convert dictionary to Vendor object"""
        vendor = Vendor()
        vendor.id = data.get('id', '')
        vendor.vendor_number = data.get('vendor_number', '')
        vendor.company_name = data.get('company_name', '')
        vendor.contact_name = data.get('contact_name', '')
        vendor.email = data.get('email', '')
        vendor.phone = data.get('phone')
        vendor.status = VendorStatus(data.get('status', 'PENDING_APPROVAL'))
        vendor.service_types = [ServiceType(st) for st in data.get('service_types', [])]
        vendor.average_rating = data.get('average_rating', 0.0)
        vendor.total_ratings = data.get('total_ratings', 0)
        vendor.total_shipments = data.get('total_shipments', 0)
        vendor.on_time_delivery_rate = data.get('on_time_delivery_rate', 0.0)
        return vendor
    
    def _dict_to_vendor_rating(self, data: Dict) -> VendorRating:
        """Convert dictionary to VendorRating object"""
        rating = VendorRating()
        rating.id = data.get('id', '')
        rating.vendor_id = data.get('vendor_id', '')
        rating.shipment_id = data.get('shipment_id', '')
        rating.overall_rating = data.get('overall_rating', 0.0)
        rating.quality_rating = data.get('quality_rating')
        rating.timeliness_rating = data.get('timeliness_rating')
        rating.communication_rating = data.get('communication_rating')
        rating.cost_rating = data.get('cost_rating')
        rating.comments = data.get('comments')
        rating.rated_by = data.get('rated_by', '')
        return rating

