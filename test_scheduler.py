#!/usr/bin/env python3
"""
Test script for the photo processing scheduler
"""
import os
import sys
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variable to disable scheduler during test
os.environ['SCAN_INTERVAL_HOURS'] = '0'

from scheduler import PhotoScheduler, run_photo_scan, run_similarity_analysis

def test_individual_functions():
    """Test individual scheduler functions"""
    print("Testing individual scheduler functions...")
    
    print("\n1. Testing photo scan function...")
    try:
        result = run_photo_scan()
        print(f"   Photo scan result: {result}")
    except Exception as e:
        print(f"   Photo scan error: {e}")
    
    print("\n2. Testing similarity analysis function...")
    try:
        result = run_similarity_analysis()
        print(f"   Similarity analysis result: {result}")
    except Exception as e:
        print(f"   Similarity analysis error: {e}")

def test_scheduler_creation():
    """Test scheduler creation and configuration"""
    print("\n3. Testing scheduler creation...")
    try:
        scheduler = PhotoScheduler()
        status = scheduler.get_status()
        print(f"   Scheduler created successfully")
        print(f"   Status: {status}")
        return scheduler
    except Exception as e:
        print(f"   Scheduler creation error: {e}")
        return None

def main():
    print("FastFoto Scheduler Test")
    print("=" * 50)
    
    # Test individual functions
    test_individual_functions()
    
    # Test scheduler creation
    scheduler = test_scheduler_creation()
    
    if scheduler:
        print(f"\n4. Testing scheduler start/stop...")
        try:
            scheduler.start()
            print("   Scheduler started successfully")
            
            # Get status
            status = scheduler.get_status()
            print(f"   Running: {status['running']}")
            print(f"   Jobs: {len(status['jobs'])}")
            
            # Stop scheduler
            scheduler.stop()
            print("   Scheduler stopped successfully")
            
        except Exception as e:
            print(f"   Scheduler start/stop error: {e}")
    
    print(f"\nScheduler test completed!")

if __name__ == "__main__":
    main()