import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

# Import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))
from config import Config
from database import Database
from cache import Cache
from events import EventProducer

# Import analytics routes
from src.routes.analytics import analytics_bp
from src.routes.reports import reports_bp
from src.routes.dashboards import dashboards_bp
from src.routes.metrics import metrics_bp

# Custom JSON encoder for handling special data types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
config = Config()
app.config.update(config.get_flask_config())
app.json_encoder = CustomJSONEncoder

# Enable CORS for all routes
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"])

# JWT configuration
jwt = JWTManager(app)

# Initialize services
db = Database(config.DATABASE_URL)
cache = Cache(config.REDIS_URL)
event_producer = EventProducer(config.KAFKA_BOOTSTRAP_SERVERS)

# Store services in app context for access in routes
app.db = db
app.cache = cache
app.event_producer = event_producer

# Register blueprints
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
app.register_blueprint(reports_bp, url_prefix='/api/reports')
app.register_blueprint(dashboards_bp, url_prefix='/api/dashboards')
app.register_blueprint(metrics_bp, url_prefix='/api/metrics')

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = db.health_check()
        
        # Check cache connection
        cache_status = cache.health_check()
        
        # Check event producer
        event_status = event_producer.health_check()
        
        overall_status = all([db_status, cache_status, event_status])
        
        return jsonify({
            'status': 'healthy' if overall_status else 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'analytics-service',
            'version': '1.0.0',
            'checks': {
                'database': 'ok' if db_status else 'error',
                'cache': 'ok' if cache_status else 'error',
                'events': 'ok' if event_status else 'error'
            }
        }), 200 if overall_status else 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'analytics-service',
            'error': str(e)
        }), 503

# Metrics endpoint for Prometheus
@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# Error handlers
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handle HTTP exceptions"""
    return jsonify({
        'error': e.name,
        'message': e.description,
        'status_code': e.code,
        'timestamp': datetime.utcnow().isoformat()
    }), e.code

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle unexpected exceptions"""
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'status_code': 500,
        'timestamp': datetime.utcnow().isoformat()
    }), 500

# Request/Response logging middleware
@app.before_request
def log_request_info():
    """Log request information"""
    if request.endpoint != 'health_check' and request.endpoint != 'metrics':
        print(f"Analytics Service - {request.method} {request.url} - {datetime.utcnow().isoformat()}")

@app.after_request
def log_response_info(response):
    """Log response information"""
    if request.endpoint != 'health_check' and request.endpoint != 'metrics':
        print(f"Analytics Service - Response {response.status_code} - {datetime.utcnow().isoformat()}")
    return response

# Static file serving for frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve static files"""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return jsonify({
                'service': 'analytics-service',
                'version': '1.0.0',
                'status': 'running',
                'timestamp': datetime.utcnow().isoformat(),
                'endpoints': {
                    'analytics': '/api/analytics',
                    'reports': '/api/reports',
                    'dashboards': '/api/dashboards',
                    'metrics': '/api/metrics',
                    'health': '/health'
                }
            })

if __name__ == '__main__':
    print("Starting Analytics Service...")
    print(f"Environment: {config.ENVIRONMENT}")
    print(f"Database: {config.DATABASE_URL}")
    print(f"Cache: {config.REDIS_URL}")
    print(f"Events: {config.KAFKA_BOOTSTRAP_SERVERS}")
    
    app.run(host='0.0.0.0', port=5000, debug=config.DEBUG)
