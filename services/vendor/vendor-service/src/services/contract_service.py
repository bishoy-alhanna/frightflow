import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.exceptions import NotFound, Conflict, BadRequest

from models.contract import Contract, ContractTerm, ContractAmendment, ContractStatus, ContractType, AmendmentType

class ContractService:
    """Service for managing contracts"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def create_contract(self, vendor_id: str, contract_type: str,
                       title: Optional[str] = None, description: Optional[str] = None,
                       start_date: str = None, end_date: str = None,
                       value: Optional[float] = None, currency: str = "USD",
                       payment_terms: Optional[str] = None,
                       terms: List[Dict] = None, created_by: str = "") -> Contract:
        """Create a new contract"""
        
        # Validate contract type
        try:
            parsed_contract_type = ContractType(contract_type)
        except ValueError:
            raise BadRequest(f"Invalid contract type: {contract_type}")
        
        # Parse dates
        parsed_start_date = self._parse_datetime(start_date)
        parsed_end_date = self._parse_datetime(end_date)
        
        if not parsed_start_date:
            raise BadRequest("Start date is required")
        
        if parsed_end_date and parsed_end_date <= parsed_start_date:
            raise BadRequest("End date must be after start date")
        
        # Create contract
        contract = Contract(
            vendor_id=vendor_id,
            contract_type=parsed_contract_type,
            title=title or f"{parsed_contract_type.value} - {vendor_id}",
            description=description,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            value=value,
            currency=currency,
            payment_terms=payment_terms or "NET_30",
            created_by=created_by
        )
        
        # Add terms if provided
        if terms:
            for term_data in terms:
                term = ContractTerm(
                    contract_id=contract.id,
                    term_type=term_data.get('term_type', ''),
                    title=term_data.get('title', ''),
                    description=term_data.get('description', ''),
                    value=term_data.get('value'),
                    is_mandatory=term_data.get('is_mandatory', True)
                )
                contract.add_term(term)
        
        # Save to database
        self._save_contract(contract)
        
        # Cache the contract
        self.cache.set(f"contract:{contract.id}", contract.to_dict(), ttl=3600)
        
        # Publish contract created event
        self.event_producer.publish('contract.created', {
            'contract_id': contract.id,
            'contract_number': contract.contract_number,
            'vendor_id': vendor_id,
            'contract_type': contract_type,
            'value': value,
            'start_date': start_date,
            'end_date': end_date,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return contract
    
    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get a contract by ID"""
        
        # Try cache first
        cached = self.cache.get(f"contract:{contract_id}")
        if cached:
            contract_data = json.loads(cached) if isinstance(cached, str) else cached
            return self._dict_to_contract(contract_data)
        
        # Load from database
        contract = self._load_contract(contract_id)
        if contract:
            # Cache the result
            self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        return contract
    
    def get_contracts(self, vendor_id: Optional[str] = None,
                     status: Optional[str] = None, contract_type: Optional[str] = None,
                     page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get contracts with filtering and pagination"""
        
        # Build query filters
        filters = {}
        if vendor_id:
            filters['vendor_id'] = vendor_id
        if status:
            filters['status'] = status
        if contract_type:
            filters['contract_type'] = contract_type
        
        # Get contracts from database
        contracts_data = self._query_contracts(filters, page, per_page)
        
        contracts = []
        for contract_data in contracts_data['items']:
            contract = self._dict_to_contract(contract_data)
            contracts.append(contract)
        
        return {
            'items': contracts,
            'page': page,
            'per_page': per_page,
            'total': contracts_data['total'],
            'pages': (contracts_data['total'] + per_page - 1) // per_page
        }
    
    def update_contract(self, contract_id: str, updates: Dict[str, Any],
                       updated_by: str) -> Contract:
        """Update contract information"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise NotFound("Contract not found")
        
        if contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING_APPROVAL]:
            raise Conflict("Cannot update contract in current status")
        
        # Apply updates
        updatable_fields = [
            'title', 'description', 'value', 'currency', 'payment_terms',
            'minimum_volume', 'maximum_volume', 'service_level_targets',
            'penalties', 'auto_renewal', 'notice_period_days', 'notes'
        ]
        
        for field in updatable_fields:
            if field in updates:
                setattr(contract, field, updates[field])
        
        # Handle date updates
        if 'start_date' in updates:
            contract.start_date = self._parse_datetime(updates['start_date'])
        
        if 'end_date' in updates:
            contract.end_date = self._parse_datetime(updates['end_date'])
        
        # Handle tags separately
        if 'tags' in updates:
            contract.tags = updates['tags'] if isinstance(updates['tags'], list) else []
        
        contract.updated_at = datetime.utcnow()
        
        # Save to database
        self._save_contract(contract)
        
        # Update cache
        self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        # Publish contract updated event
        self.event_producer.publish('contract.updated', {
            'contract_id': contract_id,
            'contract_number': contract.contract_number,
            'updates': updates,
            'updated_by': updated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return contract
    
    def activate_contract(self, contract_id: str, approved_by: str) -> Contract:
        """Activate a contract"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise NotFound("Contract not found")
        
        if contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING_APPROVAL]:
            raise Conflict("Contract cannot be activated in current status")
        
        # Activate the contract
        contract.activate(approved_by)
        
        # Save to database
        self._save_contract(contract)
        
        # Update cache
        self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        # Publish contract activated event
        self.event_producer.publish('contract.activated', {
            'contract_id': contract_id,
            'contract_number': contract.contract_number,
            'vendor_id': contract.vendor_id,
            'approved_by': approved_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return contract
    
    def terminate_contract(self, contract_id: str, reason: str,
                          terminated_by: str) -> Contract:
        """Terminate a contract"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise NotFound("Contract not found")
        
        if contract.status != ContractStatus.ACTIVE:
            raise Conflict("Only active contracts can be terminated")
        
        # Terminate the contract
        contract.terminate(reason)
        
        # Save to database
        self._save_contract(contract)
        
        # Update cache
        self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        # Publish contract terminated event
        self.event_producer.publish('contract.terminated', {
            'contract_id': contract_id,
            'contract_number': contract.contract_number,
            'vendor_id': contract.vendor_id,
            'reason': reason,
            'terminated_by': terminated_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return contract
    
    def create_contract_amendment(self, contract_id: str, amendment_type: str,
                                description: str, changes: Dict[str, Any] = None,
                                effective_date: Optional[str] = None,
                                created_by: str = "") -> ContractAmendment:
        """Create an amendment to a contract"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise NotFound("Contract not found")
        
        if contract.status != ContractStatus.ACTIVE:
            raise Conflict("Can only amend active contracts")
        
        # Validate amendment type
        try:
            parsed_amendment_type = AmendmentType(amendment_type)
        except ValueError:
            raise BadRequest(f"Invalid amendment type: {amendment_type}")
        
        # Parse effective date
        parsed_effective_date = None
        if effective_date:
            parsed_effective_date = self._parse_datetime(effective_date)
        
        # Create amendment
        amendment = ContractAmendment(
            contract_id=contract_id,
            amendment_type=parsed_amendment_type,
            title=f"Amendment {len(contract.amendments) + 1} - {parsed_amendment_type.value}",
            description=description,
            changes=changes or {},
            effective_date=parsed_effective_date,
            created_by=created_by
        )
        
        # Add to contract
        contract.add_amendment(amendment)
        
        # Save to database
        self._save_contract(contract)
        
        # Update cache
        self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        # Publish amendment created event
        self.event_producer.publish('contract.amendment_created', {
            'contract_id': contract_id,
            'amendment_id': amendment.id,
            'amendment_type': amendment_type,
            'description': description,
            'created_by': created_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return amendment
    
    def approve_contract_amendment(self, contract_id: str, amendment_id: str,
                                 approved_by: str) -> ContractAmendment:
        """Approve a contract amendment"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise NotFound("Contract not found")
        
        # Find the amendment
        amendment = None
        for amend in contract.amendments:
            if amend.id == amendment_id:
                amendment = amend
                break
        
        if not amendment:
            raise NotFound("Amendment not found")
        
        if amendment.approved:
            raise Conflict("Amendment already approved")
        
        # Approve the amendment
        amendment.approve(approved_by)
        
        # Save to database
        self._save_contract(contract)
        
        # Update cache
        self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        # Publish amendment approved event
        self.event_producer.publish('contract.amendment_approved', {
            'contract_id': contract_id,
            'amendment_id': amendment_id,
            'amendment_type': amendment.amendment_type.value,
            'approved_by': approved_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return amendment
    
    def renew_contract(self, contract_id: str, new_end_date: str,
                      renewed_by: str) -> Contract:
        """Renew a contract"""
        
        contract = self.get_contract(contract_id)
        if not contract:
            raise NotFound("Contract not found")
        
        if contract.status != ContractStatus.ACTIVE:
            raise Conflict("Only active contracts can be renewed")
        
        # Parse new end date
        parsed_new_end_date = self._parse_datetime(new_end_date)
        if not parsed_new_end_date:
            raise BadRequest("Invalid new end date")
        
        if parsed_new_end_date <= datetime.utcnow():
            raise BadRequest("New end date must be in the future")
        
        # Renew the contract
        contract.renew(parsed_new_end_date, renewed_by)
        
        # Save to database
        self._save_contract(contract)
        
        # Update cache
        self.cache.set(f"contract:{contract_id}", contract.to_dict(), ttl=3600)
        
        # Publish contract renewed event
        self.event_producer.publish('contract.renewed', {
            'contract_id': contract_id,
            'contract_number': contract.contract_number,
            'vendor_id': contract.vendor_id,
            'new_end_date': new_end_date,
            'renewed_by': renewed_by,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return contract
    
    def get_expiring_contracts(self, days_threshold: int = 30) -> List[Contract]:
        """Get contracts expiring within the threshold"""
        
        # Get expiring contracts from database
        contracts_data = self._query_expiring_contracts(days_threshold)
        
        contracts = []
        for contract_data in contracts_data:
            contract = self._dict_to_contract(contract_data)
            if contract.is_expiring_soon(days_threshold):
                contracts.append(contract)
        
        return contracts
    
    def get_contract_analytics(self, date_from: Optional[str] = None,
                             date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get contract analytics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=30)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get analytics data from database
        analytics = self._get_contract_analytics_data(start_date, end_date)
        
        return {
            'total_contracts': analytics.get('total_contracts', 0),
            'active_contracts': analytics.get('active_contracts', 0),
            'expiring_contracts': analytics.get('expiring_contracts', 0),
            'total_contract_value': analytics.get('total_contract_value', 0),
            'contracts_by_type': analytics.get('contracts_by_type', {}),
            'contracts_by_status': analytics.get('contracts_by_status', {}),
            'average_contract_duration': analytics.get('average_contract_duration', 0),
            'renewal_rate': analytics.get('renewal_rate', 0),
            'top_contracts_by_value': analytics.get('top_contracts_by_value', []),
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            }
        }
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _save_contract(self, contract: Contract):
        """Save contract to database"""
        # Mock implementation
        pass
    
    def _load_contract(self, contract_id: str) -> Optional[Contract]:
        """Load contract from database"""
        # Mock implementation - return a sample contract for demo
        if contract_id == "demo":
            contract = Contract(
                id=contract_id,
                vendor_id="demo-vendor",
                contract_type=ContractType.MASTER_SERVICE_AGREEMENT,
                title="Master Service Agreement - Global Logistics",
                description="Comprehensive service agreement for ocean and air freight",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow() + timedelta(days=335),
                value=500000.0,
                currency="USD",
                payment_terms="NET_30",
                status=ContractStatus.ACTIVE
            )
            return contract
        return None
    
    def _query_contracts(self, filters: Dict, page: int, per_page: int) -> Dict:
        """Query contracts from database"""
        # Mock implementation
        demo_contract = self._load_contract("demo")
        if demo_contract:
            return {
                'items': [demo_contract.to_dict()],
                'total': 1
            }
        return {'items': [], 'total': 0}
    
    def _query_expiring_contracts(self, days_threshold: int) -> List[Dict]:
        """Query expiring contracts"""
        # Mock implementation
        return []
    
    def _get_contract_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get contract analytics data from database"""
        # Mock implementation
        return {
            'total_contracts': 25,
            'active_contracts': 18,
            'expiring_contracts': 3,
            'total_contract_value': 12500000.0,
            'contracts_by_type': {
                'MASTER_SERVICE_AGREEMENT': 12,
                'SPOT_RATE_AGREEMENT': 8,
                'VOLUME_COMMITMENT': 3,
                'SERVICE_LEVEL_AGREEMENT': 2
            },
            'contracts_by_status': {
                'ACTIVE': 18,
                'DRAFT': 4,
                'PENDING_APPROVAL': 2,
                'EXPIRED': 1
            },
            'average_contract_duration': 365,
            'renewal_rate': 85.0,
            'top_contracts_by_value': [
                {'vendor_name': 'Global Logistics Solutions', 'value': 2500000},
                {'vendor_name': 'Ocean Express', 'value': 1800000},
                {'vendor_name': 'Air Cargo Pro', 'value': 1200000}
            ]
        }
    
    def _dict_to_contract(self, data: Dict) -> Contract:
        """Convert dictionary to Contract object"""
        contract = Contract()
        contract.id = data.get('id', '')
        contract.contract_number = data.get('contract_number', '')
        contract.vendor_id = data.get('vendor_id', '')
        contract.contract_type = ContractType(data.get('contract_type', 'MASTER_SERVICE_AGREEMENT'))
        contract.title = data.get('title', '')
        contract.description = data.get('description')
        contract.status = ContractStatus(data.get('status', 'DRAFT'))
        contract.value = data.get('value')
        contract.currency = data.get('currency', 'USD')
        contract.payment_terms = data.get('payment_terms', 'NET_30')
        
        # Parse dates
        if data.get('start_date'):
            contract.start_date = self._parse_datetime(data['start_date'])
        if data.get('end_date'):
            contract.end_date = self._parse_datetime(data['end_date'])
        
        return contract

