"""
Database initialization script for quotation service.
"""
import os
import sys

# Add shared libraries to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.main import create_app
from shared.database import db
from src.services.pricing_engine import PricingEngine

def init_database():
    """Initialize database with tables and sample data."""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        # Seed pricing rules
        print("Seeding sample pricing rules...")
        pricing_engine = PricingEngine()
        pricing_engine.seed_sample_pricing_rules()
        print("Sample pricing rules seeded successfully!")
        
        print("Database initialization completed!")

if __name__ == '__main__':
    init_database()

