#!/usr/bin/env python3
"""
Script to clean up stale database entries for files that no longer exist on disk.
This resolves issues where photos appear in the database but the actual files are missing.
"""

import os
from database import DatabaseManager

def cleanup_stale_entries():
    """Remove database entries for files that don't exist on disk"""
    db = DatabaseManager()
    
    print("Starting database cleanup...")
    
    # Use the new cleanup method
    missing_count = db.cleanup_missing_photos()
    
    if missing_count > 0:
        print(f"Successfully cleaned up {missing_count} missing photo entries")
    else:
        print("No missing photos found - database is clean!")
    
    # Show current database stats
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM photos')
    total_photos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM photos WHERE processed_date IS NOT NULL')
    processed_photos = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM photos WHERE ignored_date IS NOT NULL')
    ignored_photos = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\nDatabase Statistics:")
    print(f"  Total photos: {total_photos}")
    print(f"  Processed photos: {processed_photos}")
    print(f"  Ignored photos: {ignored_photos}")
    print(f"  Unprocessed photos: {total_photos - processed_photos - ignored_photos}")

if __name__ == '__main__':
    cleanup_stale_entries()