#!/usr/bin/env python3
"""
Photo Processing and Grouping Batch Script

This script performs photo discovery, database updates, and similarity analysis.
It should be run periodically to keep the photo database up-to-date and group similar photos.
It's designed to be CPU-only and can run in the background without interfering with the web UI.

Usage:
    python run_photo_processing.py [--eps 0.3] [--min-samples 2] [--force] [--scan-only]

Arguments:
    --eps: DBSCAN clustering epsilon parameter (default: 0.3)
           Lower values = more strict grouping
           Higher values = more loose grouping
    --min-samples: Minimum photos required for a group (default: 2)
    --force: Force re-computation of embeddings for all photos
    --scan-only: Only scan for new photos, skip similarity analysis
"""

import argparse
import sys
import os
import time
from datetime import datetime
from similarity_analyzer import SimilarityAnalyzer
from dotenv import load_dotenv

# Load environment variables from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def log_message(message: str):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def main():
    # Get default values from environment variables
    default_eps = float(os.getenv('SIMILARITY_EPS', '0.3'))
    default_min_samples = int(os.getenv('SIMILARITY_MIN_SAMPLES', '2'))
    
    # Get absolute path for photos directory
    def get_absolute_path(env_path, default_relative_path):
        """Convert environment path to absolute path"""
        path = os.getenv(env_path, default_relative_path)
        if os.path.isabs(path):
            return path
        # Make relative paths relative to the project root (parent of src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, path.lstrip('./'))
    
    default_photos_dir = get_absolute_path('PHOTOS_UNPROCESSED_DIR', './data/photos/unprocessed')
    
    parser = argparse.ArgumentParser(description="Run photo processing and similarity analysis")
    parser.add_argument('--eps', type=float, default=default_eps, 
                       help=f'DBSCAN epsilon parameter (default: {default_eps})')
    parser.add_argument('--min-samples', type=int, default=default_min_samples,
                       help=f'Minimum samples for DBSCAN clustering (default: {default_min_samples})')
    parser.add_argument('--force', action='store_true',
                       help='Force re-computation of all embeddings')
    parser.add_argument('--scan-only', action='store_true',
                       help='Only scan for new photos, skip similarity analysis')
    parser.add_argument('--photos-dir', type=str, default=default_photos_dir,
                       help=f'Photos directory path (default: {default_photos_dir})')
    
    args = parser.parse_args()
    
    if args.scan_only:
        log_message("Starting photo scanning...")
    else:
        log_message("Starting photo processing and grouping analysis...")
        log_message(f"Parameters: eps={args.eps}, min_samples={args.min_samples}, force={args.force}")
    
    start_time = time.time()
    
    try:
        # Check if photos directory exists
        if not os.path.exists(args.photos_dir):
            log_message(f"Error: Photos directory '{args.photos_dir}' does not exist")
            return 1
        
        # Step 1: Scan for new photos and add them to database
        log_message("Scanning for new photos...")
        from app import PhotoManager
        photo_manager = PhotoManager()
        photo_pairs = photo_manager.scan_photos()  # This will add new photos to database
        
        total_new_photos = sum(1 for pair in photo_pairs.values() 
                              for photo in [pair['front'], pair['back']] + pair['variants'] 
                              if photo)
        log_message(f"Found {len(photo_pairs)} photo sets ({total_new_photos} individual photos)")
        
        # If scan-only mode, exit here
        if args.scan_only:
            elapsed_time = time.time() - start_time
            log_message(f"Photo scanning completed successfully in {elapsed_time:.2f} seconds")
            return 0
        
        # Initialize analyzer for similarity analysis
        analyzer = SimilarityAnalyzer(photos_dir=args.photos_dir)
        
        # Step 2: Compute embeddings
        log_message("Computing photo embeddings...")
        if args.force:
            log_message("Force mode: Re-computing all embeddings")
            # Clear existing embeddings if force mode
            conn = analyzer.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM photo_embeddings WHERE embedding_type = 'combined'")
            conn.commit()
            conn.close()
        
        analyzer.compute_embeddings_for_all_photos()
        
        # Step 3: Find similar groups
        log_message("Finding similar photo groups...")
        groups = analyzer.find_similar_groups(eps=args.eps, min_samples=args.min_samples)
        
        if not groups:
            log_message("No similar photo groups found")
            elapsed_time = time.time() - start_time
            log_message(f"Photo processing completed successfully in {elapsed_time:.2f} seconds")
            return 0
        
        log_message(f"Found {len(groups)} potential photo groups:")
        for i, group in enumerate(groups):
            log_message(f"  Group {i+1}: {len(group)} photos")
            for filepath in group[:3]:  # Show first 3 photos
                log_message(f"    - {os.path.basename(filepath)}")
            if len(group) > 3:
                log_message(f"    - ... and {len(group) - 3} more")
        
        # Step 4: Store groups in database
        log_message("Storing photo groups in database...")
        analyzer.create_photo_groups_in_database(groups)
        
        elapsed_time = time.time() - start_time
        log_message(f"Photo processing and grouping analysis completed successfully in {elapsed_time:.2f} seconds")
        log_message(f"Created {len(groups)} photo groups")
        
        return 0
        
    except KeyboardInterrupt:
        log_message("Analysis interrupted by user")
        return 1
    except Exception as e:
        log_message(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)