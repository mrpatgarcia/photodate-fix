#!/usr/bin/env python3
"""
Generate thumbnails for existing photos in the FastFoto Date Scanner
Run this script to create thumbnails for photos that were added before thumbnail functionality
"""
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def generate_all_thumbnails():
    """Generate thumbnails for all existing photos"""
    try:
        print("FastFoto Thumbnail Generator")
        print("=" * 40)
        
        # Import app components
        from app import PhotoManager, UNPROCESSED_DIR, THUMBS_DIR, IGNORE_FILE_PATTERNS
        
        print(f"Unprocessed photos directory: {UNPROCESSED_DIR}")
        print(f"Thumbnails directory: {THUMBS_DIR}")
        
        # Create thumbs directory if it doesn't exist
        os.makedirs(THUMBS_DIR, exist_ok=True)
        
        # Find all image files in unprocessed directory
        photo_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        photo_paths = []
        
        for root, dirs, files in os.walk(UNPROCESSED_DIR):
            for file in files:
                if any(file.lower().endswith(ext) for ext in photo_extensions):
                    # Skip files matching ignore patterns
                    should_ignore = False
                    for pattern in IGNORE_FILE_PATTERNS:
                        if pattern in file:
                            should_ignore = True
                            break
                    
                    if not should_ignore:
                        photo_paths.append(os.path.join(root, file))
        
        print(f"Found {len(photo_paths)} photos to process")
        
        if not photo_paths:
            print("No photos found to generate thumbnails for")
            return True
        
        # Initialize photo manager
        photo_manager = PhotoManager()
        
        # Generate thumbnails
        print("Generating thumbnails...")
        generated_count = photo_manager.batch_generate_thumbnails(photo_paths)
        
        print(f"\nSuccessfully generated {generated_count} thumbnails")
        print(f"Thumbnail directory: {THUMBS_DIR}")
        
        # List some examples
        if generated_count > 0:
            thumb_files = os.listdir(THUMBS_DIR)
            print(f"\nExample thumbnails created:")
            for i, thumb_file in enumerate(thumb_files[:5]):
                print(f"  - {thumb_file}")
            if len(thumb_files) > 5:
                print(f"  ... and {len(thumb_files) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"Error generating thumbnails: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = generate_all_thumbnails()
    sys.exit(0 if success else 1)