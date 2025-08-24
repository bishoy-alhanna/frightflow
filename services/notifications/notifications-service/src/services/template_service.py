import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.notification import NotificationTemplate, NotificationType, NotificationChannel

class TemplateService:
    """Service for managing notification templates"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_template(self, name: str, template_type: str, subject: str,
                       content: str, variables: List[str] = None,
                       channels: List[str] = None, created_by: str = "") -> NotificationTemplate:
        """Create a new notification template"""
        
        # Check if template with same name already exists
        existing = self._find_template_by_name(name)
        if existing:
            raise Conflict("Template with this name already exists")
        
        # Parse template type
        try:
            parsed_type = NotificationType(template_type.upper())
        except ValueError:
            raise BadRequest(f"Invalid template type: {template_type}")
        
        # Parse channels
        parsed_channels = []
        if channels:
            for channel in channels:
                try:
                    parsed_channels.append(NotificationChannel(channel.upper()))
                except ValueError:
                    raise BadRequest(f"Invalid channel: {channel}")
        else:
            parsed_channels = [NotificationChannel.EMAIL]
        
        # Create template
        template = NotificationTemplate(
            name=name,
            template_type=parsed_type,
            subject=subject,
            content=content,
            variables=variables or [],
            supported_channels=parsed_channels,
            created_by=created_by
        )
        
        # Save to database
        self._save_template(template)
        
        # Cache the template
        self.cache.set(f"template:{template.id}", template.to_dict(), ttl=3600)
        self.cache.set(f"template:name:{name}", template.to_dict(), ttl=3600)
        
        # Publish template created event
        self.event_producer.publish('template.created', {
            'template_id': template.id,
            'name': name,
            'template_type': template_type,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return template
    
    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get a template by ID"""
        
        # Try cache first
        cached = self.cache.get(f"template:{template_id}")
        if cached:
            template_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_template(template_data)
        
        # Load from database
        template = self._load_template(template_id)
        if template:
            # Cache the result
            self.cache.set(f"template:{template_id}", template.to_dict(), ttl=3600)
        
        return template
    
    def get_template_by_name(self, name: str) -> Optional[NotificationTemplate]:
        """Get a template by name"""
        
        # Try cache first
        cached = self.cache.get(f"template:name:{name}")
        if cached:
            template_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_template(template_data)
        
        # Load from database
        template = self._find_template_by_name(name)
        if template:
            # Cache the result
            self.cache.set(f"template:name:{name}", template.to_dict(), ttl=3600)
        
        return template
    
    def get_templates(self, template_type: Optional[str] = None,
                     page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get templates with filtering and pagination"""
        
        # Build query filters
        filters = {}
        if template_type:
            filters['template_type'] = template_type
        
        # Get templates from database
        templates_data = self._query_templates(filters, page, per_page)
        
        templates = []
        for template_data in templates_data['items']:
            template = self._dict_to_template(template_data)
            templates.append(template)
        
        return {
            'items': templates,
            'page': page,
            'per_page': per_page,
            'total': templates_data['total'],
            'pages': (templates_data['total'] + per_page - 1) // per_page
        }
    
    def update_template(self, template_id: str, updates: Dict[str, Any],
                       updated_by: str) -> NotificationTemplate:
        """Update a template"""
        
        template = self.get_template(template_id)
        if not template:
            raise NotFound("Template not found")
        
        # Apply updates
        updatable_fields = [
            'name', 'subject', 'content', 'html_content', 'variables',
            'sample_data', 'description', 'tags'
        ]
        
        for field in updatable_fields:
            if field in updates:
                setattr(template, field, updates[field])
        
        # Handle channels separately
        if 'channels' in updates:
            parsed_channels = []
            for channel in updates['channels']:
                try:
                    parsed_channels.append(NotificationChannel(channel.upper()))
                except ValueError:
                    raise BadRequest(f"Invalid channel: {channel}")
            template.supported_channels = parsed_channels
        
        # Handle active status
        if 'is_active' in updates:
            template.is_active = bool(updates['is_active'])
        
        template.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_template(template)
        
        # Update cache
        self.cache.set(f"template:{template_id}", template.to_dict(), ttl=3600)
        if template.name:
            self.cache.set(f"template:name:{template.name}", template.to_dict(), ttl=3600)
        
        # Publish template updated event
        self.event_producer.publish('template.updated', {
            'template_id': template_id,
            'name': template.name,
            'updates': updates,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return template
    
    def delete_template(self, template_id: str, deleted_by: str):
        """Delete a template"""
        
        template = self.get_template(template_id)
        if not template:
            raise NotFound("Template not found")
        
        # Check if template is in use
        if self._is_template_in_use(template_id):
            raise Conflict("Cannot delete template that is currently in use")
        
        # Delete from database
        self._delete_template(template_id)
        
        # Remove from cache
        self.cache.delete(f"template:{template_id}")
        self.cache.delete(f"template:name:{template.name}")
        
        # Publish template deleted event
        self.event_producer.publish('template.deleted', {
            'template_id': template_id,
            'name': template.name,
            'deleted_by': deleted_by,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def render_template(self, template_id: str, data: Dict[str, Any]) -> Dict[str, str]:
        """Render a template with provided data"""
        
        template = self.get_template(template_id)
        if not template:
            raise NotFound("Template not found")
        
        if not template.is_active:
            raise BadRequest("Template is not active")
        
        # Validate template data
        missing_vars = template.validate_data(data)
        if missing_vars:
            raise BadRequest(f"Missing template variables: {', '.join(missing_vars)}")
        
        # Render template
        rendered = template.render(data)
        
        return rendered
    
    def preview_template(self, template_id: str) -> Dict[str, str]:
        """Preview a template with sample data"""
        
        template = self.get_template(template_id)
        if not template:
            raise NotFound("Template not found")
        
        # Use sample data for preview
        sample_data = template.sample_data or self._get_default_sample_data(template.template_type)
        
        # Render template with sample data
        rendered = template.render(sample_data)
        
        return {
            'subject': rendered['subject'],
            'content': rendered['content'],
            'html_content': rendered['html_content'],
            'sample_data': sample_data
        }
    
    def get_templates_by_type(self, template_type: str) -> List[NotificationTemplate]:
        """Get all active templates for a specific type"""
        
        # Parse template type
        try:
            parsed_type = NotificationType(template_type.upper())
        except ValueError:
            raise BadRequest(f"Invalid template type: {template_type}")
        
        # Get templates from database
        templates_data = self._query_templates_by_type(parsed_type)
        
        templates = []
        for template_data in templates_data:
            template = self._dict_to_template(template_data)
            if template.is_active:
                templates.append(template)
        
        return templates
    
    def clone_template(self, template_id: str, new_name: str, created_by: str) -> NotificationTemplate:
        """Clone an existing template"""
        
        original = self.get_template(template_id)
        if not original:
            raise NotFound("Template not found")
        
        # Check if new name already exists
        existing = self._find_template_by_name(new_name)
        if existing:
            raise Conflict("Template with this name already exists")
        
        # Create cloned template
        cloned = NotificationTemplate(
            name=new_name,
            template_type=original.template_type,
            subject=original.subject,
            content=original.content,
            html_content=original.html_content,
            variables=original.variables.copy(),
            sample_data=original.sample_data.copy(),
            supported_channels=original.supported_channels.copy(),
            description=f"Cloned from {original.name}",
            tags=original.tags.copy(),
            created_by=created_by
        )
        
        # Save to database
        self._save_template(cloned)
        
        # Cache the template
        self.cache.set(f"template:{cloned.id}", cloned.to_dict(), ttl=3600)
        self.cache.set(f"template:name:{new_name}", cloned.to_dict(), ttl=3600)
        
        # Publish template cloned event
        self.event_producer.publish('template.cloned', {
            'original_template_id': template_id,
            'new_template_id': cloned.id,
            'new_name': new_name,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return cloned
    
    def get_template_analytics(self, template_id: str) -> Dict[str, Any]:
        """Get analytics for a specific template"""
        
        template = self.get_template(template_id)
        if not template:
            raise NotFound("Template not found")
        
        # Get analytics data from database
        analytics = self._get_template_analytics_data(template_id)
        
        return {
            'template_id': template_id,
            'template_name': template.name,
            'usage_stats': {
                'total_uses': analytics.get('total_uses', 0),
                'last_used': analytics.get('last_used'),
                'unique_recipients': analytics.get('unique_recipients', 0),
                'success_rate': analytics.get('success_rate', 0)
            },
            'performance': {
                'delivery_rate': analytics.get('delivery_rate', 0),
                'read_rate': analytics.get('read_rate', 0),
                'click_rate': analytics.get('click_rate', 0),
                'unsubscribe_rate': analytics.get('unsubscribe_rate', 0)
            },
            'channel_breakdown': analytics.get('channel_breakdown', {}),
            'recent_usage': analytics.get('recent_usage', [])
        }
    
    def _get_default_sample_data(self, template_type: NotificationType) -> Dict[str, Any]:
        """Get default sample data for a template type"""
        
        sample_data_map = {
            NotificationType.QUOTE_CREATED: {
                'customer_name': 'John Doe',
                'quote_number': 'QT240824001',
                'origin': 'Los Angeles, CA',
                'destination': 'New York, NY',
                'total_cost': '$2,450.00',
                'valid_until': '2024-09-15'
            },
            NotificationType.SHIPMENT_STATUS_UPDATE: {
                'customer_name': 'Jane Smith',
                'shipment_number': 'SH240824001',
                'status': 'In Transit',
                'location': 'Chicago, IL',
                'estimated_delivery': '2024-08-28'
            },
            NotificationType.BOOKING_CONFIRMED: {
                'customer_name': 'Mike Johnson',
                'booking_number': 'BK240824001',
                'pickup_date': '2024-08-26',
                'delivery_date': '2024-08-30'
            }
        }
        
        return sample_data_map.get(template_type, {
            'customer_name': 'Customer Name',
            'company_name': 'FreightFlow',
            'date': datetime.now().strftime('%Y-%m-%d')
        })
    
    # Database operations (mock implementations)
    def _save_template(self, template: NotificationTemplate):
        """Save template to database"""
        # Mock implementation
        pass
    
    def _load_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Load template from database"""
        # Mock implementation - return sample templates for demo
        sample_templates = {
            "quote-created": NotificationTemplate(
                id="quote-created",
                name="Quote Created",
                template_type=NotificationType.QUOTE_CREATED,
                subject="Your freight quote {{quote_number}} is ready",
                content="Dear {{customer_name}},\n\nYour freight quote from {{origin}} to {{destination}} is ready for review.\n\nQuote Number: {{quote_number}}\nTotal Cost: {{total_cost}}\nValid Until: {{valid_until}}\n\nPlease review and confirm your booking.\n\nBest regards,\nFreightFlow Team",
                variables=['customer_name', 'quote_number', 'origin', 'destination', 'total_cost', 'valid_until'],
                supported_channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            )
        }
        
        return sample_templates.get(template_id)
    
    def _find_template_by_name(self, name: str) -> Optional[NotificationTemplate]:
        """Find template by name"""
        # Mock implementation
        return None
    
    def _query_templates(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query templates from database"""
        # Mock implementation
        sample_template = self._load_template("quote-created")
        if sample_template:
            return {
                'items': [sample_template.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _query_templates_by_type(self, template_type: NotificationType) -> List[Dict]:
        """Query templates by type"""
        # Mock implementation
        sample_template = self._load_template("quote-created")
        if sample_template and sample_template.template_type == template_type:
            return [sample_template.to_dict()]
        return []
    
    def _delete_template(self, template_id: str):
        """Delete template from database"""
        # Mock implementation
        pass
    
    def _is_template_in_use(self, template_id: str) -> bool:
        """Check if template is currently in use"""
        # Mock implementation
        return False
    
    def _get_template_analytics_data(self, template_id: str) -> Dict:
        """Get template analytics data from database"""
        # Mock implementation
        return {
            'total_uses': 125,
            'last_used': '2024-08-24T10:30:00Z',
            'unique_recipients': 98,
            'success_rate': 96.8,
            'delivery_rate': 98.4,
            'read_rate': 78.2,
            'click_rate': 12.5,
            'unsubscribe_rate': 0.8,
            'channel_breakdown': {
                'EMAIL': 85,
                'IN_APP': 40
            },
            'recent_usage': [
                {'date': '2024-08-24', 'count': 8},
                {'date': '2024-08-23', 'count': 12},
                {'date': '2024-08-22', 'count': 6}
            ]
        }
    
    def _dict_to_template(self, data: Dict) -> NotificationTemplate:
        """Convert dictionary to NotificationTemplate object"""
        template = NotificationTemplate()
        template.id = data.get('id', '')
        template.name = data.get('name', '')
        template.template_type = NotificationType(data.get('template_type', 'SYSTEM_ALERT'))
        template.subject = data.get('subject', '')
        template.content = data.get('content', '')
        template.html_content = data.get('html_content')
        template.variables = data.get('variables', [])
        template.sample_data = data.get('sample_data', {})
        template.supported_channels = [NotificationChannel(ch) for ch in data.get('supported_channels', ['EMAIL'])]
        template.is_active = data.get('is_active', True)
        template.version = data.get('version', 1)
        template.description = data.get('description')
        template.tags = data.get('tags', [])
        template.created_by = data.get('created_by', '')
        return template

