#!/usr/bin/env python3
"""
Database initialization script for PhotoDate Fix
Ensures the database and all required tables are created before the app starts
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def init_database():
    """Initialize the database and verify it's working"""
    try:
        print("FastFoto Database Initialization")
        print("=" * 40)
        
        # Import database manager
        from database import DatabaseManager, DATABASE_PATH
        
        print(f"Database path: {DATABASE_PATH}")
        print(f"Database directory: {os.path.dirname(DATABASE_PATH)}")
        
        # Check if database directory exists
        db_dir = os.path.dirname(DATABASE_PATH)
        if os.path.exists(db_dir):
            print(f"✓ Database directory exists: {db_dir}")
        else:
            print(f"✗ Database directory missing: {db_dir}")
        
        # Initialize database
        print("\nInitializing database...")
        db_manager = DatabaseManager()
        
        # Test connection
        print("Testing database connection...")
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✓ Found {len(tables)} tables in database")
        
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
        print("\n✓ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)