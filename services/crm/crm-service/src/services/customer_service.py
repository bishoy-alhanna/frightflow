import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.customer import Customer, Contact, CustomerNote, CustomerStatus, ContactType

class CustomerService:
    """Service for managing customers"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_customer(self, company_name: str, contact_name: str, email: str,
                       phone: Optional[str] = None, address: Optional[str] = None,
                       city: Optional[str] = None, country: Optional[str] = None,
                       postal_code: Optional[str] = None, tax_id: Optional[str] = None,
                       credit_limit: float = 0.0, payment_terms: str = "NET_30",
                       created_by: str = "") -> Customer:
        """Create a new customer"""
        
        # Check if customer with same email already exists
        existing = self._find_customer_by_email(email)
        if existing:
            raise Conflict("Customer with this email already exists")
        
        # Create customer
        customer = Customer(
            company_name=company_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            country=country,
            postal_code=postal_code,
            tax_id=tax_id,
            credit_limit=credit_limit,
            payment_terms=payment_terms,
            created_by=created_by
        )
        
        # Add primary contact
        primary_contact = Contact(
            customer_id=customer.id,
            contact_type=ContactType.PRIMARY,
            name=contact_name,
            email=email,
            phone=phone,
            is_primary=True
        )
        customer.add_contact(primary_contact)
        
        # Save to database
        self._save_customer(customer)
        
        # Cache the customer
        self.cache.set(f"customer:{customer.id}", customer.to_dict(), ttl=3600)
        
        # Publish customer created event
        self.event_producer.publish('customer.created', {
            'customer_id': customer.id,
            'customer_number': customer.customer_number,
            'company_name': customer.company_name,
            'email': customer.email,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return customer
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get a customer by ID"""
        
        # Try cache first
        cached = self.cache.get(f"customer:{customer_id}")
        if cached:
            customer_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_customer(customer_data)
        
        # Load from database
        customer = self._load_customer(customer_id)
        if customer:
            # Cache the result
            self.cache.set(f"customer:{customer_id}", customer.to_dict(), ttl=3600)
        
        return customer
    
    def get_customers(self, search: str = "", status: Optional[str] = None,
                     country: Optional[str] = None, page: int = 1, per_page: int = 20,
                     sort_by: str = "created_at", sort_order: str = "desc") -> Dict[str, Any]:
        """Get customers with filtering and pagination"""
        
        # Build query filters
        filters = {}
        if search:
            filters['search'] = search
        if status:
            filters['status'] = status
        if country:
            filters['country'] = country
        
        # Get customers from database
        customers_data = self._query_customers(filters, page, per_page, sort_by, sort_order)
        
        customers = []
        for customer_data in customers_data['items']:
            customer = self._dict_to_customer(customer_data)
            customers.append(customer)
        
        return {
            'items': customers,
            'page': page,
            'per_page': per_page,
            'total': customers_data['total'],
            'pages': (customers_data['total'] + per_page - 1) // per_page
        }
    
    def update_customer(self, customer_id: str, updates: Dict[str, Any],
                       updated_by: str) -> Customer:
        """Update customer information"""
        
        customer = self.get_customer(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        # Apply updates
        updatable_fields = [
            'company_name', 'contact_name', 'email', 'phone', 'mobile', 'website',
            'address', 'city', 'state', 'country', 'postal_code', 'tax_id',
            'industry', 'company_size', 'annual_revenue', 'credit_limit',
            'payment_terms', 'currency', 'account_manager', 'sales_rep', 'notes'
        ]
        
        for field in updatable_fields:
            if field in updates:
                setattr(customer, field, updates[field])
        
        # Handle tags separately
        if 'tags' in updates:
            customer.tags = updates['tags'] if isinstance(updates['tags'], list) else []
        
        customer.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_customer(customer)
        
        # Update cache
        self.cache.set(f"customer:{customer_id}", customer.to_dict(), ttl=3600)
        
        # Publish customer updated event
        self.event_producer.publish('customer.updated', {
            'customer_id': customer_id,
            'customer_number': customer.customer_number,
            'updates': updates,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return customer
    
    def update_customer_status(self, customer_id: str, is_active: bool,
                              reason: Optional[str] = None, updated_by: str = "") -> Customer:
        """Update customer status"""
        
        customer = self.get_customer(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        old_status = customer.status
        
        if is_active:
            customer.activate()
        else:
            customer.deactivate(reason)
        
        # Save to database
        self._save_customer(customer)
        
        # Update cache
        self.cache.set(f"customer:{customer_id}", customer.to_dict(), ttl=3600)
        
        # Publish status change event
        self.event_producer.publish('customer.status_changed', {
            'customer_id': customer_id,
            'customer_number': customer.customer_number,
            'old_status': old_status.value,
            'new_status': customer.status.value,
            'reason': reason,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return customer
    
    def create_customer_note(self, customer_id: str, content: str,
                            is_private: bool = False, created_by: str = "") -> CustomerNote:
        """Create a note for a customer"""
        
        # Verify customer exists
        customer = self.get_customer(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        # Create note
        note = CustomerNote(
            customer_id=customer_id,
            content=content,
            is_private=is_private,
            created_by=created_by
        )
        
        # Save to database
        self._save_customer_note(note)
        
        # Publish note created event
        self.event_producer.publish('customer.note_created', {
            'customer_id': customer_id,
            'note_id': note.id,
            'is_private': is_private,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return note
    
    def get_customer_notes(self, customer_id: str, user_id: str) -> List[CustomerNote]:
        """Get notes for a customer"""
        
        # Verify customer exists
        customer = self.get_customer(customer_id)
        if not customer:
            raise NotFound("Customer not found")
        
        # Get notes from database
        notes_data = self._query_customer_notes(customer_id, user_id)
        
        notes = []
        for note_data in notes_data:
            note = self._dict_to_customer_note(note_data)
            notes.append(note)
        
        return notes
    
    def get_customer_stats(self, customer_id: str) -> Dict[str, Any]:
        """Get customer statistics"""
        
        # This would query various services for customer statistics
        # For now, return mock data
        return {
            'total_quotes': 15,
            'total_bookings': 8,
            'total_shipments': 12,
            'total_revenue': 45000.00,
            'average_shipment_value': 3750.00,
            'last_quote_date': '2024-08-15T10:30:00Z',
            'last_booking_date': '2024-08-10T14:20:00Z',
            'customer_lifetime_value': 125000.00,
            'payment_history': {
                'on_time_payments': 95.5,
                'average_payment_days': 28,
                'outstanding_amount': 2500.00
            }
        }
    
    def get_customer_analytics(self, date_from: Optional[str] = None,
                              date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get customer analytics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_customer_analytics_data(start_date, end_date)
        
        return {
            'total_customers': analytics.get('total_customers', 0),
            'active_customers': analytics.get('active_customers', 0),
            'new_customers': analytics.get('new_customers', 0),
            'churned_customers': analytics.get('churned_customers', 0),
            'customer_growth_rate': analytics.get('customer_growth_rate', 0),
            'average_customer_value': analytics.get('average_customer_value', 0),
            'top_customers': analytics.get('top_customers', []),
            'customers_by_country': analytics.get('customers_by_country', {}),
            'customers_by_industry': analytics.get('customers_by_industry', {}),
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            }
        }
    
    def export_customers(self, filters: Dict[str, Any]) -> str:
        """Export customers to CSV"""
        
        # Get customers based on filters
        customers_data = self._query_customers_for_export(filters)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Customer Number', 'Company Name', 'Contact Name', 'Email', 'Phone',
            'Country', 'Status', 'Customer Since', 'Credit Limit', 'Payment Terms',
            'Account Manager', 'Created At'
        ])
        
        # Write data
        for customer_data in customers_data:
            writer.writerow([
                customer_data.get('customer_number', ''),
                customer_data.get('company_name', ''),
                customer_data.get('contact_name', ''),
                customer_data.get('email', ''),
                customer_data.get('phone', ''),
                customer_data.get('country', ''),
                customer_data.get('status', ''),
                customer_data.get('customer_since', ''),
                customer_data.get('credit_limit', 0),
                customer_data.get('payment_terms', ''),
                customer_data.get('account_manager', ''),
                customer_data.get('created_at', '')
            ])
        
        return output.getvalue()
    
    def _find_customer_by_email(self, email: str) -> Optional[Customer]:
        """Find customer by email"""
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
    def _save_customer(self, customer: Customer):
        """Save customer to database"""
        # Mock implementation
        pass
    
    def _load_customer(self, customer_id: str) -> Optional[Customer]:
        """Load customer from database"""
        # Mock implementation - return a sample customer for demo
        if customer_id == "demo":
            customer = Customer(
                id=customer_id,
                company_name="Acme Corporation",
                contact_name="John Smith",
                email="john.smith@acme.com",
                phone="+1-555-0123",
                address="123 Business Ave",
                city="New York",
                country="USA",
                postal_code="10001",
                status=CustomerStatus.ACTIVE,
                credit_limit=50000.0,
                payment_terms="NET_30"
            )
            return customer
        return None
    
    def _query_customers(self, filters: Dict, page: int, per_page: int,
                        sort_by: str, sort_order: str) -> Dict:
        """Query customers from database"""
        # Mock implementation
        demo_customer = self._load_customer("demo")
        if demo_customer:
            return {
                'items': [demo_customer.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _query_customers_for_export(self, filters: Dict) -> List[Dict]:
        """Query customers for export"""
        # Mock implementation
        demo_customer = self._load_customer("demo")
        if demo_customer:
            return [demo_customer.to_dict()]
        return []
    
    def _save_customer_note(self, note: CustomerNote):
        """Save customer note to database"""
        # Mock implementation
        pass
    
    def _query_customer_notes(self, customer_id: str, user_id: str) -> List[Dict]:
        """Query customer notes"""
        # Mock implementation
        return []
    
    def _get_customer_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get customer analytics data from database"""
        # Mock implementation
        return {
            'total_customers': 250,
            'active_customers': 220,
            'new_customers': 15,
            'churned_customers': 3,
            'customer_growth_rate': 6.4,
            'average_customer_value': 15750.00,
            'top_customers': [
                {'name': 'Acme Corp', 'value': 125000},
                {'name': 'Global Logistics', 'value': 98000},
                {'name': 'Ocean Freight Co', 'value': 87500}
            ],
            'customers_by_country': {
                'USA': 120,
                'Canada': 45,
                'Mexico': 35,
                'UK': 25,
                'Germany': 25
            },
            'customers_by_industry': {
                'Manufacturing': 80,
                'Retail': 60,
                'Technology': 45,
                'Automotive': 35,
                'Other': 30
            }
        }
    
    def _dict_to_customer(self, data: Dict) -> Customer:
        """Convert dictionary to Customer object"""
        customer = Customer()
        customer.id = data.get('id', '')
        customer.customer_number = data.get('customer_number', '')
        customer.company_name = data.get('company_name', '')
        customer.contact_name = data.get('contact_name', '')
        customer.email = data.get('email', '')
        customer.phone = data.get('phone')
        customer.status = CustomerStatus(data.get('status', 'PROSPECT'))
        return customer
    
    def _dict_to_customer_note(self, data: Dict) -> CustomerNote:
        """Convert dictionary to CustomerNote object"""
        note = CustomerNote()
        note.id = data.get('id', '')
        note.customer_id = data.get('customer_id', '')
        note.content = data.get('content', '')
        note.is_private = data.get('is_private', False)
        note.created_by = data.get('created_by', '')
        return note

