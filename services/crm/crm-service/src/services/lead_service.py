import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.lead import Lead, LeadStatus, LeadSource, LeadPriority
from models.customer import Customer, CustomerStatus

class LeadService:
    """Service for managing leads"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_lead(self, company_name: str, contact_name: str, email: str,
                   phone: Optional[str] = None, source: str = "WEBSITE",
                   estimated_value: Optional[float] = None, notes: Optional[str] = None,
                   assigned_to: Optional[str] = None, created_by: str = "") -> Lead:
        """Create a new lead"""
        
        # Check if lead with same email already exists
        existing = self._find_lead_by_email(email)
        if existing and existing.status not in [LeadStatus.CONVERTED, LeadStatus.LOST, LeadStatus.DISQUALIFIED]:
            raise Conflict("Active lead with this email already exists")
        
        # Parse source
        try:
            lead_source = LeadSource(source)
        except ValueError:
            lead_source = LeadSource.OTHER
        
        # Create lead
        lead = Lead(
            company_name=company_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            source=lead_source,
            estimated_value=estimated_value,
            notes=notes,
            assigned_to=assigned_to,
            created_by=created_by
        )
        
        # Set initial probability based on source
        source_probabilities = {
            LeadSource.REFERRAL: 60,
            LeadSource.PARTNER: 50,
            LeadSource.WEBSITE: 30,
            LeadSource.TRADE_SHOW: 40,
            LeadSource.SOCIAL_MEDIA: 20,
            LeadSource.EMAIL_CAMPAIGN: 15,
            LeadSource.COLD_CALL: 10,
            LeadSource.ADVERTISEMENT: 15,
            LeadSource.OTHER: 20
        }
        lead.probability = source_probabilities.get(lead_source, 20)
        
        # Save to database
        self._save_lead(lead)
        
        # Cache the lead
        self.cache.set(f"lead:{lead.id}", lead.to_dict(), ttl=3600)
        
        # Publish lead created event
        self.event_producer.publish('lead.created', {
            'lead_id': lead.id,
            'lead_number': lead.lead_number,
            'company_name': lead.company_name,
            'email': lead.email,
            'source': lead.source.value,
            'estimated_value': lead.estimated_value,
            'assigned_to': lead.assigned_to,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return lead
    
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a lead by ID"""
        
        # Try cache first
        cached = self.cache.get(f"lead:{lead_id}")
        if cached:
            lead_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_lead(lead_data)
        
        # Load from database
        lead = self._load_lead(lead_id)
        if lead:
            # Cache the result
            self.cache.set(f"lead:{lead_id}", lead.to_dict(), ttl=3600)
        
        return lead
    
    def get_leads(self, search: str = "", status: Optional[str] = None,
                 source: Optional[str] = None, assigned_to: Optional[str] = None,
                 page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get leads with filtering and pagination"""
        
        # Build query filters
        filters = {}
        if search:
            filters['search'] = search
        if status:
            filters['status'] = status
        if source:
            filters['source'] = source
        if assigned_to:
            filters['assigned_to'] = assigned_to
        
        # Get leads from database
        leads_data = self._query_leads(filters, page, per_page)
        
        leads = []
        for lead_data in leads_data['items']:
            lead = self._dict_to_lead(lead_data)
            leads.append(lead)
        
        return {
            'items': leads,
            'page': page,
            'per_page': per_page,
            'total': leads_data['total'],
            'pages': (leads_data['total'] + per_page - 1) // per_page
        }
    
    def update_lead(self, lead_id: str, updates: Dict[str, Any],
                   updated_by: str) -> Lead:
        """Update lead information"""
        
        lead = self.get_lead(lead_id)
        if not lead:
            raise NotFound("Lead not found")
        
        # Apply updates
        updatable_fields = [
            'company_name', 'contact_name', 'title', 'email', 'phone', 'mobile',
            'website', 'address', 'city', 'state', 'country', 'postal_code',
            'estimated_value', 'probability', 'requirements', 'notes',
            'assigned_to', 'next_follow_up'
        ]
        
        for field in updatable_fields:
            if field in updates:
                if field == 'next_follow_up' and updates[field]:
                    setattr(lead, field, self._parse_datetime(updates[field]))
                else:
                    setattr(lead, field, updates[field])
        
        # Handle status update
        if 'status' in updates:
            try:
                new_status = LeadStatus(updates['status'])
                lead.update_status(new_status, updates.get('status_notes'))
            except ValueError:
                raise BadRequest(f"Invalid status: {updates['status']}")
        
        # Handle priority update
        if 'priority' in updates:
            try:
                lead.priority = LeadPriority(updates['priority'])
            except ValueError:
                raise BadRequest(f"Invalid priority: {updates['priority']}")
        
        lead.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_lead(lead)
        
        # Update cache
        self.cache.set(f"lead:{lead_id}", lead.to_dict(), ttl=3600)
        
        # Publish lead updated event
        self.event_producer.publish('lead.updated', {
            'lead_id': lead_id,
            'lead_number': lead.lead_number,
            'updates': updates,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return lead
    
    def convert_lead_to_customer(self, lead_id: str, additional_data: Dict[str, Any],
                                converted_by: str) -> Customer:
        """Convert a lead to a customer"""
        
        lead = self.get_lead(lead_id)
        if not lead:
            raise NotFound("Lead not found")
        
        if lead.status == LeadStatus.CONVERTED:
            raise Conflict("Lead has already been converted")
        
        if lead.status in [LeadStatus.LOST, LeadStatus.DISQUALIFIED]:
            raise Conflict("Cannot convert a lost or disqualified lead")
        
        # Create customer from lead data
        from services.customer_service import CustomerService
        customer_service = CustomerService(self.db, self.cache, self.event_producer)
        
        customer_data = {
            'company_name': lead.company_name,
            'contact_name': lead.contact_name,
            'email': lead.email,
            'phone': lead.phone,
            'address': lead.address,
            'city': lead.city,
            'country': lead.country,
            'postal_code': lead.postal_code,
            **additional_data  # Allow override with additional data
        }
        
        customer = customer_service.create_customer(
            **customer_data,
            created_by=converted_by
        )
        
        # Update lead status
        lead.convert_to_customer(customer.id, converted_by)
        
        # Save lead
        self._save_lead(lead)
        
        # Update cache
        self.cache.set(f"lead:{lead_id}", lead.to_dict(), ttl=3600)
        
        # Publish lead converted event
        self.event_producer.publish('lead.converted', {
            'lead_id': lead_id,
            'lead_number': lead.lead_number,
            'customer_id': customer.id,
            'customer_number': customer.customer_number,
            'converted_by': converted_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return customer
    
    def mark_lead_as_lost(self, lead_id: str, reason: str, updated_by: str) -> Lead:
        """Mark a lead as lost"""
        
        lead = self.get_lead(lead_id)
        if not lead:
            raise NotFound("Lead not found")
        
        if lead.status in [LeadStatus.CONVERTED, LeadStatus.LOST, LeadStatus.DISQUALIFIED]:
            raise Conflict("Lead cannot be marked as lost in current status")
        
        # Mark as lost
        lead.mark_as_lost(reason)
        
        # Save to database
        self._save_lead(lead)
        
        # Update cache
        self.cache.set(f"lead:{lead_id}", lead.to_dict(), ttl=3600)
        
        # Publish lead lost event
        self.event_producer.publish('lead.lost', {
            'lead_id': lead_id,
            'lead_number': lead.lead_number,
            'reason': reason,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return lead
    
    def get_lead_analytics(self, date_from: Optional[str] = None,
                          date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get lead analytics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_lead_analytics_data(start_date, end_date)
        
        return {
            'total_leads': analytics.get('total_leads', 0),
            'new_leads': analytics.get('new_leads', 0),
            'qualified_leads': analytics.get('qualified_leads', 0),
            'converted_leads': analytics.get('converted_leads', 0),
            'lost_leads': analytics.get('lost_leads', 0),
            'conversion_rate': analytics.get('conversion_rate', 0),
            'average_lead_score': analytics.get('average_lead_score', 0),
            'average_conversion_time': analytics.get('average_conversion_time', 0),
            'leads_by_source': analytics.get('leads_by_source', {}),
            'leads_by_status': analytics.get('leads_by_status', {}),
            'top_performing_sources': analytics.get('top_performing_sources', []),
            'pipeline_value': analytics.get('pipeline_value', 0),
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            }
        }
    
    def get_stale_leads(self, days_threshold: int = 30) -> List[Lead]:
        """Get stale leads that need follow-up"""
        
        # Get stale leads from database
        stale_leads_data = self._query_stale_leads(days_threshold)
        
        leads = []
        for lead_data in stale_leads_data:
            lead = self._dict_to_lead(lead_data)
            leads.append(lead)
        
        return leads
    
    def get_leads_requiring_follow_up(self) -> List[Lead]:
        """Get leads that require follow-up today"""
        
        # Get leads with follow-up date <= today
        leads_data = self._query_leads_for_follow_up()
        
        leads = []
        for lead_data in leads_data:
            lead = self._dict_to_lead(lead_data)
            leads.append(lead)
        
        return leads
    
    def _find_lead_by_email(self, email: str) -> Optional[Lead]:
        """Find lead by email"""
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
    def _save_lead(self, lead: Lead):
        """Save lead to database"""
        # Mock implementation
        pass
    
    def _load_lead(self, lead_id: str) -> Optional[Lead]:
        """Load lead from database"""
        # Mock implementation - return a sample lead for demo
        if lead_id == "demo":
            lead = Lead(
                id=lead_id,
                company_name="TechStart Inc",
                contact_name="Jane Doe",
                email="jane.doe@techstart.com",
                phone="+1-555-0456",
                source=LeadSource.WEBSITE,
                status=LeadStatus.QUALIFIED,
                estimated_value=25000.0,
                probability=70,
                requirements="Need regular shipments from US to Europe",
                assigned_to="sales-rep-1"
            )
            return lead
        return None
    
    def _query_leads(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query leads from database"""
        # Mock implementation
        demo_lead = self._load_lead("demo")
        if demo_lead:
            return {
                'items': [demo_lead.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _query_stale_leads(self, days_threshold: int) -> List[Dict]:
        """Query stale leads"""
        # Mock implementation
        return []
    
    def _query_leads_for_follow_up(self) -> List[Dict]:
        """Query leads requiring follow-up"""
        # Mock implementation
        return []
    
    def _get_lead_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get lead analytics data from database"""
        # Mock implementation
        return {
            'total_leads': 85,
            'new_leads': 12,
            'qualified_leads': 25,
            'converted_leads': 8,
            'lost_leads': 15,
            'conversion_rate': 32.0,
            'average_lead_score': 45,
            'average_conversion_time': 18.5,
            'leads_by_source': {
                'WEBSITE': 35,
                'REFERRAL': 20,
                'EMAIL_CAMPAIGN': 15,
                'SOCIAL_MEDIA': 10,
                'OTHER': 5
            },
            'leads_by_status': {
                'NEW': 15,
                'CONTACTED': 20,
                'QUALIFIED': 25,
                'PROPOSAL_SENT': 10,
                'NEGOTIATION': 5,
                'CONVERTED': 8,
                'LOST': 2
            },
            'top_performing_sources': [
                {'source': 'REFERRAL', 'conversion_rate': 45.0},
                {'source': 'WEBSITE', 'conversion_rate': 28.5},
                {'source': 'EMAIL_CAMPAIGN', 'conversion_rate': 20.0}
            ],
            'pipeline_value': 450000.0
        }
    
    def _dict_to_lead(self, data: Dict) -> Lead:
        """Convert dictionary to Lead object"""
        lead = Lead()
        lead.id = data.get('id', '')
        lead.lead_number = data.get('lead_number', '')
        lead.company_name = data.get('company_name', '')
        lead.contact_name = data.get('contact_name', '')
        lead.email = data.get('email', '')
        lead.phone = data.get('phone')
        lead.source = LeadSource(data.get('source', 'WEBSITE'))
        lead.status = LeadStatus(data.get('status', 'NEW'))
        lead.estimated_value = data.get('estimated_value')
        lead.probability = data.get('probability', 0)
        return lead

