import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, BadRequest

from models.customer import CustomerInteraction, InteractionType

class InteractionService:
    """Service for managing customer interactions"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_interaction(self, customer_id: str, interaction_type: str,
                          subject: str, description: str,
                          contact_person: Optional[str] = None,
                          outcome: Optional[str] = None,
                          follow_up_date: Optional[str] = None,
                          created_by: str = "") -> CustomerInteraction:
        """Create a new customer interaction"""
        
        # Validate interaction type
        try:
            int_type = InteractionType(interaction_type)
        except ValueError:
            raise BadRequest(f"Invalid interaction type: {interaction_type}")
        
        # Parse follow-up date
        follow_up_dt = None
        if follow_up_date:
            follow_up_dt = self._parse_datetime(follow_up_date)
        
        # Create interaction
        interaction = CustomerInteraction(
            customer_id=customer_id,
            interaction_type=int_type,
            subject=subject,
            description=description,
            contact_person=contact_person,
            outcome=outcome,
            follow_up_date=follow_up_dt,
            created_by=created_by
        )
        
        # Save to database
        self._save_interaction(interaction)
        
        # Update customer's last contact date
        self._update_customer_last_contact(customer_id)
        
        # Publish interaction created event
        self.event_producer.publish('customer.interaction_created', {
            'interaction_id': interaction.id,
            'customer_id': customer_id,
            'interaction_type': interaction_type,
            'subject': subject,
            'has_follow_up': follow_up_date is not None,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return interaction
    
    def get_interaction(self, interaction_id: str) -> Optional[CustomerInteraction]:
        """Get an interaction by ID"""
        
        # Try cache first
        cached = self.cache.get(f"interaction:{interaction_id}")
        if cached:
            interaction_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_interaction(interaction_data)
        
        # Load from database
        interaction = self._load_interaction(interaction_id)
        if interaction:
            # Cache the result
            self.cache.set(f"interaction:{interaction_id}", interaction.to_dict(), ttl=3600)
        
        return interaction
    
    def get_customer_interactions(self, customer_id: str,
                                 interaction_type: Optional[str] = None,
                                 page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get interactions for a customer"""
        
        # Build query filters
        filters = {'customer_id': customer_id}
        if interaction_type:
            filters['interaction_type'] = interaction_type
        
        # Get interactions from database
        interactions_data = self._query_interactions(filters, page, per_page)
        
        interactions = []
        for interaction_data in interactions_data['items']:
            interaction = self._dict_to_interaction(interaction_data)
            interactions.append(interaction)
        
        return {
            'items': interactions,
            'page': page,
            'per_page': per_page,
            'total': interactions_data['total'],
            'pages': (interactions_data['total'] + per_page - 1) // per_page
        }
    
    def update_interaction(self, interaction_id: str, updates: Dict[str, Any],
                          updated_by: str) -> CustomerInteraction:
        """Update an interaction"""
        
        interaction = self.get_interaction(interaction_id)
        if not interaction:
            raise NotFound("Interaction not found")
        
        # Apply updates
        updatable_fields = ['subject', 'description', 'contact_person', 'outcome']
        
        for field in updatable_fields:
            if field in updates:
                setattr(interaction, field, updates[field])
        
        # Handle follow-up date
        if 'follow_up_date' in updates:
            interaction.follow_up_date = self._parse_datetime(updates['follow_up_date'])
        
        # Handle follow-up completion
        if 'follow_up_completed' in updates:
            interaction.follow_up_completed = bool(updates['follow_up_completed'])
        
        interaction.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_interaction(interaction)
        
        # Update cache
        self.cache.set(f"interaction:{interaction_id}", interaction.to_dict(), ttl=3600)
        
        # Publish interaction updated event
        self.event_producer.publish('customer.interaction_updated', {
            'interaction_id': interaction_id,
            'customer_id': interaction.customer_id,
            'updates': updates,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return interaction
    
    def complete_follow_up(self, interaction_id: str, outcome: str,
                          completed_by: str) -> CustomerInteraction:
        """Mark a follow-up as completed"""
        
        interaction = self.get_interaction(interaction_id)
        if not interaction:
            raise NotFound("Interaction not found")
        
        if not interaction.follow_up_date:
            raise BadRequest("Interaction does not have a follow-up date")
        
        if interaction.follow_up_completed:
            raise BadRequest("Follow-up already completed")
        
        # Mark as completed
        interaction.follow_up_completed = True
        interaction.outcome = outcome
        interaction.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_interaction(interaction)
        
        # Update cache
        self.cache.set(f"interaction:{interaction_id}", interaction.to_dict(), ttl=3600)
        
        # Publish follow-up completed event
        self.event_producer.publish('customer.follow_up_completed', {
            'interaction_id': interaction_id,
            'customer_id': interaction.customer_id,
            'outcome': outcome,
            'completed_by': completed_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return interaction
    
    def get_pending_follow_ups(self, assigned_to: Optional[str] = None,
                              overdue_only: bool = False) -> List[CustomerInteraction]:
        """Get pending follow-ups"""
        
        # Build query filters
        filters = {
            'follow_up_completed': False,
            'has_follow_up': True
        }
        
        if assigned_to:
            filters['created_by'] = assigned_to
        
        if overdue_only:
            filters['overdue'] = True
        
        # Get interactions from database
        interactions_data = self._query_pending_follow_ups(filters)
        
        interactions = []
        for interaction_data in interactions_data:
            interaction = self._dict_to_interaction(interaction_data)
            interactions.append(interaction)
        
        return interactions
    
    def get_interaction_summary(self, customer_id: str) -> Dict[str, Any]:
        """Get interaction summary for a customer"""
        
        # Get summary data from database
        summary = self._get_interaction_summary_data(customer_id)
        
        return {
            'total_interactions': summary.get('total_interactions', 0),
            'last_interaction_date': summary.get('last_interaction_date'),
            'interactions_by_type': summary.get('interactions_by_type', {}),
            'pending_follow_ups': summary.get('pending_follow_ups', 0),
            'overdue_follow_ups': summary.get('overdue_follow_ups', 0),
            'recent_interactions': summary.get('recent_interactions', [])
        }
    
    def get_interaction_analytics(self, date_from: Optional[str] = None,
                                 date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get interaction analytics"""
        
        # Parse date range
        from datetime import timedelta
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_interaction_analytics_data(start_date, end_date)
        
        return {
            'total_interactions': analytics.get('total_interactions', 0),
            'interactions_by_type': analytics.get('interactions_by_type', {}),
            'interactions_by_user': analytics.get('interactions_by_user', {}),
            'average_interactions_per_customer': analytics.get('average_interactions_per_customer', 0),
            'follow_up_completion_rate': analytics.get('follow_up_completion_rate', 0),
            'most_active_customers': analytics.get('most_active_customers', []),
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            }
        }
    
    def _update_customer_last_contact(self, customer_id: str):
        """Update customer's last contact date"""
        # This would update the customer record
        # For now, just publish an event
        self.event_producer.publish('customer.last_contact_updated', {
            'customer_id': customer_id,
            'last_contact_date': datetime.utcnow().isoformat()
        })
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _save_interaction(self, interaction: CustomerInteraction):
        """Save interaction to database"""
        # Mock implementation
        pass
    
    def _load_interaction(self, interaction_id: str) -> Optional[CustomerInteraction]:
        """Load interaction from database"""
        # Mock implementation
        return None
    
    def _query_interactions(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query interactions from database"""
        # Mock implementation
        return {'items': [], 'total': 0}
    
    def _query_pending_follow_ups(self, filters: Dict) -> List[Dict]:
        """Query pending follow-ups"""
        # Mock implementation
        return []
    
    def _get_interaction_summary_data(self, customer_id: str) -> Dict:
        """Get interaction summary data"""
        # Mock implementation
        return {
            'total_interactions': 5,
            'last_interaction_date': '2024-08-15T10:30:00Z',
            'interactions_by_type': {
                'CALL': 2,
                'EMAIL': 2,
                'MEETING': 1
            },
            'pending_follow_ups': 1,
            'overdue_follow_ups': 0,
            'recent_interactions': []
        }
    
    def _get_interaction_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get interaction analytics data"""
        # Mock implementation
        return {
            'total_interactions': 150,
            'interactions_by_type': {
                'CALL': 60,
                'EMAIL': 45,
                'MEETING': 25,
                'QUOTE_REQUEST': 15,
                'SUPPORT': 5
            },
            'interactions_by_user': {
                'user1': 50,
                'user2': 40,
                'user3': 35,
                'user4': 25
            },
            'average_interactions_per_customer': 2.5,
            'follow_up_completion_rate': 85.0,
            'most_active_customers': [
                {'customer_name': 'Acme Corp', 'interactions': 8},
                {'customer_name': 'Global Logistics', 'interactions': 6},
                {'customer_name': 'Ocean Freight', 'interactions': 5}
            ]
        }
    
    def _dict_to_interaction(self, data: Dict) -> CustomerInteraction:
        """Convert dictionary to CustomerInteraction object"""
        interaction = CustomerInteraction()
        interaction.id = data.get('id', '')
        interaction.customer_id = data.get('customer_id', '')
        interaction.interaction_type = InteractionType(data.get('interaction_type', 'OTHER'))
        interaction.subject = data.get('subject', '')
        interaction.description = data.get('description', '')
        interaction.contact_person = data.get('contact_person')
        interaction.outcome = data.get('outcome')
        interaction.follow_up_completed = data.get('follow_up_completed', False)
        interaction.created_by = data.get('created_by', '')
        return interaction

