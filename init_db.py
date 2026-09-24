#!/usr/bin/env python
"""
Database Initialization Script

This script initializes the database with sample data for testing.
Run this after first deployment.
"""

import os
import sys
from app import create_app, db

def init_db():
    """Initialize database with sample data"""
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        
        print("\n✓ Database initialization complete!")
        print("\nYou can now run: python run.py")

if __name__ == '__main__':
    init_db()
