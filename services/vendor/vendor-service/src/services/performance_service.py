from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class PerformanceService:
    """Service for tracking vendor performance"""
    
    def __init__(self, db, cache, event_producer):
        self.db = db
        self.cache = cache
        self.event_producer = event_producer
    
    def get_vendor_performance(self, vendor_id: str,
                             date_from: Optional[str] = None,
                             date_to: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive vendor performance metrics"""
        
        # Parse date range
        start_date = self._parse_datetime(date_from) if date_from else datetime.utcnow() - timedelta(days=90)
        end_date = self._parse_datetime(date_to) if date_to else datetime.utcnow()
        
        # Get performance data from database
        performance_data = self._get_vendor_performance_data(vendor_id, start_date, end_date)
        
        return {
            'vendor_id': vendor_id,
            'period': {
                'from': start_date.isoformat(),
                'to': end_date.isoformat()
            },
            'overall_metrics': {
                'performance_score': performance_data.get('performance_score', 0),
                'total_shipments': performance_data.get('total_shipments', 0),
                'completed_shipments': performance_data.get('completed_shipments', 0),
                'cancelled_shipments': performance_data.get('cancelled_shipments', 0),
                'total_revenue': performance_data.get('total_revenue', 0),
                'average_shipment_value': performance_data.get('average_shipment_value', 0)
            },
            'delivery_performance': {
                'on_time_delivery_rate': performance_data.get('on_time_delivery_rate', 0),
                'early_delivery_rate': performance_data.get('early_delivery_rate', 0),
                'late_delivery_rate': performance_data.get('late_delivery_rate', 0),
                'average_delay_days': performance_data.get('average_delay_days', 0),
                'delivery_accuracy': performance_data.get('delivery_accuracy', 0)
            },
            'quality_metrics': {
                'average_rating': performance_data.get('average_rating', 0),
                'total_ratings': performance_data.get('total_ratings', 0),
                'quality_score': performance_data.get('quality_score', 0),
                'damage_rate': performance_data.get('damage_rate', 0),
                'customer_satisfaction': performance_data.get('customer_satisfaction', 0)
            },
            'communication_metrics': {
                'response_time_hours': performance_data.get('response_time_hours', 0),
                'communication_rating': performance_data.get('communication_rating', 0),
                'proactive_updates': performance_data.get('proactive_updates', 0),
                'issue_resolution_time': performance_data.get('issue_resolution_time', 0)
            },
            'cost_metrics': {
                'cost_competitiveness': performance_data.get('cost_competitiveness', 0),
                'cost_accuracy': performance_data.get('cost_accuracy', 0),
                'additional_charges_rate': performance_data.get('additional_charges_rate', 0),
                'invoice_accuracy': performance_data.get('invoice_accuracy', 0)
            },
            'compliance_metrics': {
                'documentation_accuracy': performance_data.get('documentation_accuracy', 0),
                'customs_clearance_success': performance_data.get('customs_clearance_success', 0),
                'regulatory_compliance': performance_data.get('regulatory_compliance', 0),
                'security_compliance': performance_data.get('security_compliance', 0)
            },
            'trend_analysis': {
                'performance_trend': performance_data.get('performance_trend', 'stable'),
                'improvement_areas': performance_data.get('improvement_areas', []),
                'strengths': performance_data.get('strengths', []),
                'monthly_performance': performance_data.get('monthly_performance', [])
            },
            'benchmarking': {
                'industry_percentile': performance_data.get('industry_percentile', 0),
                'peer_comparison': performance_data.get('peer_comparison', 'average'),
                'best_in_class_gap': performance_data.get('best_in_class_gap', 0)
            }
        }
    
    def calculate_performance_score(self, vendor_id: str) -> float:
        """Calculate overall performance score for a vendor"""
        
        performance = self.get_vendor_performance(vendor_id)
        
        # Weighted scoring
        weights = {
            'delivery': 0.30,
            'quality': 0.25,
            'communication': 0.20,
            'cost': 0.15,
            'compliance': 0.10
        }
        
        # Calculate component scores
        delivery_score = performance['delivery_performance']['on_time_delivery_rate']
        quality_score = (performance['quality_metrics']['average_rating'] / 5.0) * 100
        communication_score = (performance['communication_metrics']['communication_rating'] / 5.0) * 100
        cost_score = performance['cost_metrics']['cost_competitiveness']
        compliance_score = performance['compliance_metrics']['documentation_accuracy']
        
        # Calculate weighted score
        total_score = (
            delivery_score * weights['delivery'] +
            quality_score * weights['quality'] +
            communication_score * weights['communication'] +
            cost_score * weights['cost'] +
            compliance_score * weights['compliance']
        )
        
        return min(total_score, 100.0)
    
    def get_performance_trends(self, vendor_id: str, months: int = 12) -> Dict[str, Any]:
        """Get performance trends over time"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        # Get trend data from database
        trend_data = self._get_performance_trends_data(vendor_id, start_date, end_date)
        
        return {
            'vendor_id': vendor_id,
            'period_months': months,
            'trends': {
                'performance_score': trend_data.get('performance_score_trend', []),
                'on_time_delivery': trend_data.get('on_time_delivery_trend', []),
                'quality_rating': trend_data.get('quality_rating_trend', []),
                'shipment_volume': trend_data.get('shipment_volume_trend', []),
                'cost_efficiency': trend_data.get('cost_efficiency_trend', [])
            },
            'analysis': {
                'overall_direction': trend_data.get('overall_direction', 'stable'),
                'volatility': trend_data.get('volatility', 'low'),
                'seasonal_patterns': trend_data.get('seasonal_patterns', []),
                'key_events': trend_data.get('key_events', [])
            }
        }
    
    def compare_vendors(self, vendor_ids: List[str],
                       metrics: List[str] = None) -> Dict[str, Any]:
        """Compare performance across multiple vendors"""
        
        if not metrics:
            metrics = [
                'performance_score', 'on_time_delivery_rate', 'average_rating',
                'cost_competitiveness', 'total_shipments'
            ]
        
        comparison_data = {}
        
        for vendor_id in vendor_ids:
            performance = self.get_vendor_performance(vendor_id)
            vendor_metrics = {}
            
            for metric in metrics:
                if metric == 'performance_score':
                    vendor_metrics[metric] = performance['overall_metrics']['performance_score']
                elif metric == 'on_time_delivery_rate':
                    vendor_metrics[metric] = performance['delivery_performance']['on_time_delivery_rate']
                elif metric == 'average_rating':
                    vendor_metrics[metric] = performance['quality_metrics']['average_rating']
                elif metric == 'cost_competitiveness':
                    vendor_metrics[metric] = performance['cost_metrics']['cost_competitiveness']
                elif metric == 'total_shipments':
                    vendor_metrics[metric] = performance['overall_metrics']['total_shipments']
            
            comparison_data[vendor_id] = vendor_metrics
        
        # Calculate rankings
        rankings = {}
        for metric in metrics:
            metric_values = [(vendor_id, data[metric]) for vendor_id, data in comparison_data.items()]
            metric_values.sort(key=lambda x: x[1], reverse=True)
            rankings[metric] = [vendor_id for vendor_id, _ in metric_values]
        
        return {
            'vendors': comparison_data,
            'rankings': rankings,
            'metrics': metrics,
            'summary': {
                'best_overall': rankings.get('performance_score', [None])[0],
                'most_reliable': rankings.get('on_time_delivery_rate', [None])[0],
                'highest_rated': rankings.get('average_rating', [None])[0],
                'most_cost_effective': rankings.get('cost_competitiveness', [None])[0]
            }
        }
    
    def get_performance_alerts(self, vendor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get performance alerts for vendors"""
        
        # Get alerts from database
        alerts_data = self._get_performance_alerts_data(vendor_id)
        
        alerts = []
        for alert_data in alerts_data:
            alert = {
                'id': alert_data.get('id'),
                'vendor_id': alert_data.get('vendor_id'),
                'vendor_name': alert_data.get('vendor_name'),
                'alert_type': alert_data.get('alert_type'),
                'severity': alert_data.get('severity'),
                'metric': alert_data.get('metric'),
                'current_value': alert_data.get('current_value'),
                'threshold': alert_data.get('threshold'),
                'description': alert_data.get('description'),
                'created_at': alert_data.get('created_at'),
                'acknowledged': alert_data.get('acknowledged', False)
            }
            alerts.append(alert)
        
        return alerts
    
    def create_performance_report(self, vendor_id: str,
                                report_type: str = "comprehensive") -> Dict[str, Any]:
        """Create a comprehensive performance report"""
        
        performance = self.get_vendor_performance(vendor_id)
        trends = self.get_performance_trends(vendor_id)
        
        report = {
            'vendor_id': vendor_id,
            'report_type': report_type,
            'generated_at': datetime.utcnow().isoformat(),
            'executive_summary': {
                'overall_score': performance['overall_metrics']['performance_score'],
                'key_strengths': performance['trend_analysis']['strengths'],
                'improvement_areas': performance['trend_analysis']['improvement_areas'],
                'recommendation': self._generate_recommendation(performance)
            },
            'detailed_metrics': performance,
            'trend_analysis': trends,
            'action_items': self._generate_action_items(performance),
            'next_review_date': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        return report
    
    def _generate_recommendation(self, performance: Dict[str, Any]) -> str:
        """Generate performance recommendation"""
        
        score = performance['overall_metrics']['performance_score']
        
        if score >= 90:
            return "Excellent performance. Consider for preferred vendor status."
        elif score >= 80:
            return "Good performance. Monitor for consistency."
        elif score >= 70:
            return "Acceptable performance. Focus on improvement areas."
        elif score >= 60:
            return "Below average performance. Implement improvement plan."
        else:
            return "Poor performance. Consider vendor review or replacement."
    
    def _generate_action_items(self, performance: Dict[str, Any]) -> List[str]:
        """Generate action items based on performance"""
        
        action_items = []
        
        # Check delivery performance
        if performance['delivery_performance']['on_time_delivery_rate'] < 85:
            action_items.append("Improve on-time delivery performance")
        
        # Check quality metrics
        if performance['quality_metrics']['average_rating'] < 4.0:
            action_items.append("Address quality concerns and customer feedback")
        
        # Check communication
        if performance['communication_metrics']['response_time_hours'] > 24:
            action_items.append("Improve response time to customer inquiries")
        
        # Check compliance
        if performance['compliance_metrics']['documentation_accuracy'] < 95:
            action_items.append("Enhance documentation accuracy and compliance")
        
        return action_items
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            return None
    
    # Database operations (mock implementations)
    def _get_vendor_performance_data(self, vendor_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get vendor performance data from database"""
        # Mock implementation
        return {
            'performance_score': 85.5,
            'total_shipments': 45,
            'completed_shipments': 42,
            'cancelled_shipments': 3,
            'total_revenue': 125000.0,
            'average_shipment_value': 2777.78,
            'on_time_delivery_rate': 88.1,
            'early_delivery_rate': 15.5,
            'late_delivery_rate': 11.9,
            'average_delay_days': 1.2,
            'delivery_accuracy': 96.4,
            'average_rating': 4.2,
            'total_ratings': 38,
            'quality_score': 84.0,
            'damage_rate': 0.8,
            'customer_satisfaction': 87.5,
            'response_time_hours': 4.5,
            'communication_rating': 4.1,
            'proactive_updates': 92.3,
            'issue_resolution_time': 18.5,
            'cost_competitiveness': 82.0,
            'cost_accuracy': 94.5,
            'additional_charges_rate': 5.2,
            'invoice_accuracy': 97.8,
            'documentation_accuracy': 96.2,
            'customs_clearance_success': 98.5,
            'regulatory_compliance': 95.8,
            'security_compliance': 97.2,
            'performance_trend': 'improving',
            'improvement_areas': ['Cost optimization', 'Delivery speed'],
            'strengths': ['Communication', 'Documentation', 'Compliance'],
            'monthly_performance': [82, 84, 86, 85],
            'industry_percentile': 75,
            'peer_comparison': 'above_average',
            'best_in_class_gap': 12.5
        }
    
    def _get_performance_trends_data(self, vendor_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get performance trends data from database"""
        # Mock implementation
        return {
            'performance_score_trend': [80, 82, 84, 85, 86, 85],
            'on_time_delivery_trend': [85, 87, 89, 88, 90, 88],
            'quality_rating_trend': [4.0, 4.1, 4.2, 4.1, 4.3, 4.2],
            'shipment_volume_trend': [8, 9, 7, 10, 8, 9],
            'cost_efficiency_trend': [78, 80, 82, 81, 83, 82],
            'overall_direction': 'improving',
            'volatility': 'low',
            'seasonal_patterns': ['Q4 peak volume', 'Q1 slower period'],
            'key_events': [
                {'date': '2024-06-15', 'event': 'New warehouse opened'},
                {'date': '2024-07-20', 'event': 'Process improvement implemented'}
            ]
        }
    
    def _get_performance_alerts_data(self, vendor_id: Optional[str]) -> List[Dict]:
        """Get performance alerts data from database"""
        # Mock implementation
        alerts = []
        
        if not vendor_id or vendor_id == "demo":
            alerts.append({
                'id': 'alert-1',
                'vendor_id': 'demo',
                'vendor_name': 'Global Logistics Solutions',
                'alert_type': 'performance_decline',
                'severity': 'medium',
                'metric': 'on_time_delivery_rate',
                'current_value': 82.5,
                'threshold': 85.0,
                'description': 'On-time delivery rate has dropped below threshold',
                'created_at': '2024-08-20T10:30:00Z',
                'acknowledged': False
            })
        
        return alerts

