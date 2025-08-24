"""
Quotation Service - Digital Freight Platform
Handles dynamic pricing, quote generation, and quote acceptance.
"""
import os
import sys

# Add shared libraries to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from flask import Flask, send_from_directory
from shared.config import create_base_app, setup_health_endpoints
from shared.database import init_db, db
from shared.cache import init_cache
from shared.storage import init_storage
from shared.events import init_events
from shared.auth import init_auth

# Import quotation-specific modules
from src.models.quotation import Quote, PricingRule, QuoteItem
from src.routes.quotation import quotation_bp

def create_app():
    """Create and configure the quotation service Flask app."""
    app = create_base_app('quotation-service')
    
    # Override some config for quotation service
    app.config['SERVICE_NAME'] = 'quotation-service'
    app.config['SERVICE_VERSION'] = '1.0.0'
    
    # Use PostgreSQL instead of SQLite for production
    if not app.config.get('DATABASE_URL'):
        app.config['DATABASE_URL'] = 'postgresql://freight:freight@localhost:5432/freight_db'
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['DATABASE_URL']
    
    # Initialize extensions
    db_instance = init_db(app)
    init_cache(app)
    init_storage(app)
    init_events(app)
    init_auth(app)
    
    # Register blueprints
    app.register_blueprint(quotation_bp, url_prefix='/api/v1')
    
    # Setup health endpoints
    setup_health_endpoints(app, db_instance)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Serve static files (for any frontend if needed)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return {"message": "Quotation Service API", "version": "1.0.0", "status": "running"}, 200

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            # Return API info instead of serving index.html for API service
            return {"message": "Quotation Service API", "version": "1.0.0", "status": "running"}, 200
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8101, debug=True)

