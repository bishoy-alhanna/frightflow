"""
Shared Flask configuration and settings for freight platform services.
"""
import os
import logging
import json
from typing import Optional
from flask import Flask, request, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import uuid


class Config:
    """Base configuration class with common settings."""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://freight:freight@localhost:5432/freight_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Object Storage (MinIO)
    OBJECT_STORE_ENDPOINT = os.getenv('OBJECT_STORE_ENDPOINT', 'localhost:9000')
    OBJECT_STORE_ACCESS_KEY = os.getenv('OBJECT_STORE_ACCESS_KEY', 'minioadmin')
    OBJECT_STORE_SECRET_KEY = os.getenv('OBJECT_STORE_SECRET_KEY', 'minioadmin')
    OBJECT_STORE_SECURE = os.getenv('OBJECT_STORE_SECURE', 'false').lower() == 'true'
    OBJECT_STORE_BUCKET = os.getenv('OBJECT_STORE_BUCKET', 'freight-docs')
    
    # Kafka/Events
    KAFKA_BROKERS = os.getenv('KAFKA_BROKERS', 'localhost:9092')
    
    # Service
    SERVICE_NAME = os.getenv('SERVICE_NAME', 'freight-service')
    SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = 'json'  # json or text
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://freight:freight@localhost:5432/freight_test_db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL


def get_config():
    """Get configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()


def setup_logging(app: Flask):
    """Configure structured logging with correlation IDs."""
    
    class CorrelationIdFilter(logging.Filter):
        def filter(self, record):
            record.correlation_id = getattr(g, 'correlation_id', 'unknown')
            record.service_name = app.config['SERVICE_NAME']
            return True
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
    )
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    for handler in logging.root.handlers:
        handler.addFilter(correlation_filter)
    
    # JSON formatter for structured logging
    if app.config.get('LOG_FORMAT') == 'json':
        import json_logging
        json_logging.init_flask(enable_json=True)
        json_logging.init_request_instrument(app)


def setup_correlation_id_middleware(app: Flask):
    """Add correlation ID middleware to track requests."""
    
    @app.before_request
    def before_request():
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        g.correlation_id = correlation_id
    
    @app.after_request
    def after_request(response):
        response.headers['X-Correlation-ID'] = getattr(g, 'correlation_id', 'unknown')
        return response


def setup_error_handlers(app: Flask):
    """Setup common error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return {
            'error': 'Bad Request',
            'message': str(error.description),
            'correlation_id': getattr(g, 'correlation_id', 'unknown')
        }, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return {
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'correlation_id': getattr(g, 'correlation_id', 'unknown')
        }, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return {
            'error': 'Forbidden',
            'message': 'Insufficient permissions',
            'correlation_id': getattr(g, 'correlation_id', 'unknown')
        }, 403
    
    @app.errorhandler(404)
    def not_found(error):
        return {
            'error': 'Not Found',
            'message': 'Resource not found',
            'correlation_id': getattr(g, 'correlation_id', 'unknown')
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'correlation_id': getattr(g, 'correlation_id', 'unknown')
        }, 500


def create_base_app(service_name: str) -> Flask:
    """Create a base Flask app with common configuration."""
    app = Flask(service_name)
    
    # Load configuration
    config = get_config()
    config.SERVICE_NAME = service_name
    app.config.from_object(config)
    
    # Setup CORS for all origins
    CORS(app, origins="*", allow_headers="*", methods="*")
    
    # Setup middleware and handlers
    setup_logging(app)
    setup_correlation_id_middleware(app)
    setup_error_handlers(app)
    
    return app


def setup_health_endpoints(app: Flask, db: Optional[SQLAlchemy] = None):
    """Add health and readiness endpoints."""
    
    @app.route('/health')
    def health():
        """Health check endpoint."""
        return {
            'status': 'healthy',
            'service': app.config['SERVICE_NAME'],
            'version': app.config['SERVICE_VERSION'],
            'timestamp': str(uuid.uuid4())  # Simple timestamp alternative
        }
    
    @app.route('/ready')
    def ready():
        """Readiness check endpoint."""
        checks = {'status': 'ready'}
        
        # Check database connection if provided
        if db:
            try:
                db.session.execute('SELECT 1')
                checks['database'] = 'connected'
            except Exception as e:
                checks['database'] = f'error: {str(e)}'
                return checks, 503
        
        return checks
    
    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint placeholder."""
        # TODO: Implement actual Prometheus metrics
        return "# Prometheus metrics placeholder\n", 200, {'Content-Type': 'text/plain'}

