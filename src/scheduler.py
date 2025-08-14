#!/usr/bin/env python3
"""
Scheduled task manager for PhotoDate Fix
Runs photo scanning and similarity analysis on a regular interval
"""
import os
import sys
import time
import logging
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def setup_logging():
    """Set up logging for scheduled tasks"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/app/data/db/scheduler.log', mode='a') if os.path.exists('/app/data') else logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def run_photo_scan():
    """Run photo scanning task"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting scheduled photo scan...")
        
        # Import here to avoid circular imports
        from app import PhotoManager
        
        # Initialize photo manager and run scan
        photo_manager = PhotoManager()
        photo_pairs = photo_manager.scan_photos()
        
        logger.info(f"Photo scan completed - found {len(photo_pairs)} photo sets")
        return True
        
    except Exception as e:
        logger.error(f"Error during scheduled photo scan: {e}")
        return False

def run_similarity_analysis():
    """Run similarity analysis task"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting scheduled similarity analysis...")
        
        # Import here to avoid circular imports
        from similarity_analyzer import SimilarityAnalyzer
        
        # Get configuration from environment
        eps = float(os.getenv('SIMILARITY_EPS', '0.3'))
        min_samples = int(os.getenv('SIMILARITY_MIN_SAMPLES', '2'))
        photos_dir = os.getenv('PHOTOS_UNPROCESSED_DIR', './data/photos/unprocessed')
        
        # Initialize analyzer and run
        analyzer = SimilarityAnalyzer(photos_dir)
        
        # Compute embeddings for new photos
        analyzer.compute_embeddings_for_all_photos()
        
        # Find similar groups
        groups = analyzer.find_similar_groups(eps=eps, min_samples=min_samples)
        
        # Store groups in database
        analyzer.create_photo_groups_in_database(groups)
        
        logger.info(f"Similarity analysis completed - found {len(groups)} similar groups")
        return True
        
    except Exception as e:
        logger.error(f"Error during scheduled similarity analysis: {e}")
        return False

def run_full_photo_processing():
    """Run complete photo processing (scan + similarity analysis)"""
    logger = logging.getLogger(__name__)
    
    # Add small random delay to reduce concurrent access probability
    delay = random.uniform(0, 30)  # 0-30 second random delay
    logger.info(f"Starting scheduled photo processing in {delay:.1f} seconds...")
    time.sleep(delay)
    
    logger.info("Starting scheduled photo processing...")
    
    try:
        # Run photo scan first
        scan_success = run_photo_scan()
        
        # Run similarity analysis if scan was successful
        analysis_success = False
        if scan_success:
            analysis_success = run_similarity_analysis()
        
        if scan_success and analysis_success:
            logger.info("Scheduled photo processing completed successfully")
        elif scan_success:
            logger.warning("Photo scan completed but similarity analysis failed")
        else:
            logger.error("Photo scan failed - skipping similarity analysis")
        
        return scan_success and analysis_success
        
    except Exception as e:
        logger.error(f"Unexpected error during scheduled photo processing: {e}")
        return False

class PhotoScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.logger = setup_logging()
        self.scan_interval_hours = int(os.getenv('SCAN_INTERVAL_HOURS', '1'))
        
    def start(self):
        """Start the scheduler"""
        if self.scan_interval_hours <= 0:
            self.logger.info("Scheduled photo processing is disabled (SCAN_INTERVAL_HOURS=0)")
            return
        
        self.logger.info(f"Starting photo processing scheduler - interval: {self.scan_interval_hours} hours")
        
        # Add job to run photo processing on interval
        self.scheduler.add_job(
            func=run_full_photo_processing,
            trigger=IntervalTrigger(hours=self.scan_interval_hours),
            id='photo_processing',
            name='Photo Scanning and Similarity Analysis',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )
        
        # Run initial scan after a short delay
        self.scheduler.add_job(
            func=run_full_photo_processing,
            trigger='date',
            run_date=datetime.now(),
            id='initial_photo_scan',
            name='Initial Photo Scan',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.logger.info("Photo processing scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Photo processing scheduler stopped")
    
    def get_status(self):
        """Get scheduler status"""
        if not self.scheduler.running:
            return {"running": False, "jobs": []}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
        
        return {
            "running": True,
            "interval_hours": self.scan_interval_hours,
            "jobs": jobs
        }

def main():
    """Main function for running scheduler standalone"""
    scheduler = PhotoScheduler()
    
    try:
        scheduler.start()
        
        # Keep the script running
        while True:
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\nReceived interrupt signal - shutting down scheduler...")
        scheduler.stop()
        sys.exit(0)
    except Exception as e:
        scheduler.logger.error(f"Scheduler error: {e}")
        scheduler.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()