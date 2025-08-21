from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_from_directory
import os
import hashlib
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import piexif
from pathlib import Path
import re
from database import DatabaseManager
import time
import signal
import sys
import secrets
from dotenv import load_dotenv

# Load environment variables from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Custom Jinja2 filter to extract photo filename for serving
@app.template_filter('photo_filename')
def photo_filename_filter(filepath):
    """Extract the relative filename from a photo filepath for serving via /photos/ route"""
    if not filepath:
        return ''
    
    # Try to remove prefixes from the original path first (handles mixed separators)
    original_prefixes = [
        './data/photos/unprocessed\\',  # Windows mixed separator version
        './photos/unprocessed\\',       # Windows mixed separator version  
        './photos\\',                   # Windows mixed separator version
        'data/photos/unprocessed\\',
        'photos/unprocessed\\',
        'photos\\',
    ]
    
    for prefix in original_prefixes:
        if filepath.startswith(prefix):
            return filepath[len(prefix):]
    
    # Normalize path separators and try forward slash prefixes
    normalized_path = filepath.replace('\\', '/')
    
    normalized_prefixes = [
        './data/photos/unprocessed/',
        './photos/unprocessed/', 
        './photos/',
        'data/photos/unprocessed/',
        'photos/unprocessed/',
        'photos/',
    ]
    
    for prefix in normalized_prefixes:
        if normalized_path.startswith(prefix):
            return normalized_path[len(prefix):]
    
    # If no prefix matches, just return the filename part
    return os.path.basename(normalized_path)

# Configuration from environment variables with absolute paths
def get_absolute_path(env_path, default_relative_path):
    """Convert environment path to absolute path"""
    path = os.getenv(env_path, default_relative_path)
    if os.path.isabs(path):
        return path
    # Make relative paths relative to the project root (parent of src/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, path.lstrip('./'))

UNPROCESSED_DIR = get_absolute_path('PHOTOS_UNPROCESSED_DIR', './data/photos/unprocessed')
PROCESSED_DIR = get_absolute_path('PHOTOS_PROCESSED_DIR', './data/photos/processed')
THUMBS_DIR = get_absolute_path('THUMBS_DIR', './data/thumbs')
PHOTOS_DIR = os.path.dirname(os.path.dirname(UNPROCESSED_DIR))  # Parent of photos directory
PHOTOS_PER_PAGE = int(os.getenv('PHOTOS_PER_PAGE', '250'))

# File filtering settings
IGNORE_FILE_PATTERNS = [pattern.strip() for pattern in os.getenv('IGNORE_FILE_PATTERNS', 'SYNOFILE_,.DS_Store,Thumbs.db').split(',') if pattern.strip()]

print(f"INFO: Using absolute paths:")
print(f"INFO: UNPROCESSED_DIR = {UNPROCESSED_DIR}")
print(f"INFO: PROCESSED_DIR = {PROCESSED_DIR}")
print(f"INFO: THUMBS_DIR = {THUMBS_DIR}")
print(f"INFO: IGNORE_FILE_PATTERNS = {IGNORE_FILE_PATTERNS}")
print(f"INFO: Current working directory = {os.getcwd()}")

class PhotoManager:
    def __init__(self):
        self.db = DatabaseManager()
        self._cache = {}
        self._cache_timeout = 60  # Cache for 60 seconds
    
    def get_processed_photos(self):
        """Get set of processed photo filepaths"""
        return set(self.db.get_processed_photos())
    
    def get_ignored_photos(self):
        """Get set of ignored photo filepaths"""
        return set(self.db.get_ignored_photos())
    
    def calculate_file_hash(self, filepath):
        hash_sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except IOError:
            return None
    
    def create_backup(self, filepath):
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)
        return backup_path
    
    def verify_file_integrity(self, filepath, original_hash):
        current_hash = self.calculate_file_hash(filepath)
        return current_hash == original_hash
    
    def restore_from_backup(self, filepath):
        backup_path = f"{filepath}.backup"
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, filepath)
            os.remove(backup_path)
            return True
        return False
    
    def ignore_photo_set(self, base_name, photo_pairs):
        """Mark all files in a photo set as ignored"""
        if base_name in photo_pairs:
            pair = photo_pairs[base_name]
            for filepath in [pair['front'], pair['back']] + pair.get('variants', []):
                if filepath:
                    # Add to database if not already there
                    default_date = self.extract_original_date(filepath)
                    self.db.add_photo(filepath, base_name, self._determine_file_type(os.path.basename(filepath)), default_date)
                    # Mark as ignored
                    self.db.mark_photo_ignored(filepath)
            return True
        return False
    
    def _get_cached(self, key):
        """Get cached value if still valid"""
        if key in self._cache:
            cached_time, value = self._cache[key]
            if time.time() - cached_time < self._cache_timeout:
                return value
        return None
    
    def _set_cache(self, key, value):
        """Set cached value"""
        self._cache[key] = (time.time(), value)
    
    def scan_photos(self):
        # Check cache first
        cached = self._get_cached('scan_photos')
        if cached is not None:
            return cached
        
        processed_photos = self.get_processed_photos()
        ignored_photos = self.get_ignored_photos()
        
        # Get existing photos from database to avoid duplicate insertions
        existing_photos = set(self.db.get_all_photo_paths())
        
        photo_pairs = {}
        new_photos_to_add = []
        
        for root, dirs, files in os.walk(UNPROCESSED_DIR):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp')):
                    # Skip files matching ignore patterns
                    if self.should_ignore_file(file):
                        continue
                        
                    filepath = os.path.join(root, file)
                    
                    # Skip processed or ignored photos
                    if filepath in processed_photos or filepath in ignored_photos:
                        continue
                    
                    base_name = self.extract_base_name(file)
                    if base_name not in photo_pairs:
                        photo_pairs[base_name] = {'front': None, 'back': None, 'variants': [], 'default_date': None}
                    
                    # Only add to database if not already there
                    if filepath not in existing_photos:
                        # Extract default date for this photo
                        default_date = self.extract_original_date(filepath)
                        new_photos_to_add.append((filepath, base_name, self._determine_file_type(file), default_date))
                    
                    if file.endswith('_a.jpg') or file.endswith('_a.jpeg'):
                        # If there's already a front (base file), move it to variants
                        if photo_pairs[base_name]['front']:
                            photo_pairs[base_name]['variants'].append(photo_pairs[base_name]['front'])
                        photo_pairs[base_name]['front'] = filepath
                    elif file.endswith('_b.jpg') or file.endswith('_b.jpeg'):
                        # If there's already a back (base file), move it to variants
                        if photo_pairs[base_name]['back']:
                            photo_pairs[base_name]['variants'].append(photo_pairs[base_name]['back'])
                        photo_pairs[base_name]['back'] = filepath
                    else:
                        # Base file without suffix - could be either front or back if no _a/_b exists
                        if not photo_pairs[base_name]['front']:
                            photo_pairs[base_name]['front'] = filepath
                        elif not photo_pairs[base_name]['back']:
                            photo_pairs[base_name]['back'] = filepath
                        else:
                            photo_pairs[base_name]['variants'].append(filepath)
        
        # Batch add new photos to database
        if new_photos_to_add:
            self.db.batch_add_photos(new_photos_to_add)
        
        # Generate thumbnails for new photos
        if new_photos_to_add:
            new_photo_paths = [photo[0] for photo in new_photos_to_add]  # Extract filepaths from tuples
            print(f"Generating thumbnails for {len(new_photo_paths)} new photos...")
            self.batch_generate_thumbnails(new_photo_paths)
        
        result = {k: v for k, v in photo_pairs.items() if v['front'] or v['back']}
        
        # Cache the result
        self._set_cache('scan_photos', result)
        
        return result
    
    def get_unprocessed_photo_pairs(self):
        """Get unprocessed photo pairs from database only (no file system scanning)"""
        # Check cache first
        cached = self._get_cached('unprocessed_pairs')
        if cached is not None:
            return cached
        
        # Use database method that includes default dates
        photo_pairs = self.db.get_unprocessed_photos()
        
        result = {k: v for k, v in photo_pairs.items() if v['front'] or v['back']}
        
        # Cache the result
        self._set_cache('unprocessed_pairs', result)
        
        return result
    
    def get_cached_photo_groups(self):
        """Get photo groups with caching"""
        # Check cache first
        cached = self._get_cached('photo_groups')
        if cached is not None:
            return cached
        
        # Get from database
        photo_groups = self.db.get_photo_groups()
        
        # Cache the result
        self._set_cache('photo_groups', photo_groups)
        
        return photo_groups
    
    def _determine_file_type(self, filename: str) -> str:
        """Determine if file is front, back, or variant"""
        if filename.endswith('_a.jpg') or filename.endswith('_a.jpeg'):
            return 'front'
        elif filename.endswith('_b.jpg') or filename.endswith('_b.jpeg'):
            return 'back'
        else:
            return 'variant'
    
    def extract_base_name(self, filename):
        patterns = [
            r'^(\d{4}-\d{2}-\d{2}_)?(.+?)(_[ab])?\.jpe?g$',
            r'^(.+?)(_[ab])?\.jpe?g$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename, re.IGNORECASE)
            if match:
                if match.group(1) and match.group(1).endswith('_'):
                    return match.group(2)
                else:
                    return match.group(1) if match.group(1) else match.group(2)
        
        return os.path.splitext(filename)[0]
    
    def should_ignore_file(self, filename):
        """Check if a file should be ignored based on filename patterns"""
        filename = os.path.basename(filename)
        for pattern in IGNORE_FILE_PATTERNS:
            if pattern in filename:
                return True
        return False
    
    def update_photo_date(self, filepath, new_date):
        try:
            original_hash = self.calculate_file_hash(filepath)
            if not original_hash:
                return False, "Could not calculate file hash"
            
            backup_path = self.create_backup(filepath)
            
            try:
                timestamp = datetime.strptime(new_date, '%Y-%m-%d').timestamp()
                
                os.utime(filepath, (timestamp, timestamp))
                
                self.update_exif_date(filepath, new_date)
                
                if not self.verify_file_integrity(filepath, original_hash):
                    with Image.open(filepath) as img:
                        img.verify()
                
                # Move photo to processed folder
                new_filepath = self.move_photo_to_processed(filepath, new_date)
                
                # Mark photo as processed with both old and new filepath
                self.db.mark_photo_processed(filepath, new_filepath)
                
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                
                return True, "Photo date updated successfully"
                
            except Exception as e:
                self.restore_from_backup(filepath)
                return False, f"Error updating photo: {str(e)}"
                
        except Exception as e:
            return False, f"Error processing photo: {str(e)}"
    
    def update_exif_date(self, filepath, new_date):
        try:
            date_obj = datetime.strptime(new_date, '%Y-%m-%d')
            date_string = date_obj.strftime('%Y:%m:%d %H:%M:%S')
            
            try:
                exif_dict = piexif.load(filepath)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            exif_dict['0th'][piexif.ImageIFD.DateTime] = date_string
            exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_string
            exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_string
            
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, filepath)
            
        except Exception as e:
            print(f"Warning: Could not update EXIF data for {filepath}: {e}")
    
    def extract_original_date(self, filepath):
        """Extract original date from photo EXIF data or file creation time"""
        try:
            # First try to get date from EXIF data
            try:
                exif_dict = piexif.load(filepath)
                
                # Try DateTimeOriginal first (when photo was taken)
                if 'Exif' in exif_dict and piexif.ExifIFD.DateTimeOriginal in exif_dict['Exif']:
                    date_str = exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal].decode('ascii')
                    date_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                    return date_obj.strftime('%Y-%m-%d')
                
                # Try DateTime as fallback
                if '0th' in exif_dict and piexif.ImageIFD.DateTime in exif_dict['0th']:
                    date_str = exif_dict['0th'][piexif.ImageIFD.DateTime].decode('ascii')
                    date_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                    return date_obj.strftime('%Y-%m-%d')
                    
            except Exception as e:
                print(f"Warning: Could not read EXIF date from {filepath}: {e}")
            
            # Fallback to file creation time
            try:
                stat_result = os.stat(filepath)
                # Use creation time (Windows) or modification time (Unix)
                creation_time = getattr(stat_result, 'st_birthtime', stat_result.st_mtime)
                date_obj = datetime.fromtimestamp(creation_time)
                
                # Skip obviously wrong dates (like 1800s or future dates)
                if date_obj.year < 1900 or date_obj.year > 2030:
                    return None
                    
                return date_obj.strftime('%Y-%m-%d')
            except Exception as e:
                print(f"Warning: Could not get file creation date from {filepath}: {e}")
            
            return None
            
        except Exception as e:
            print(f"Error extracting date from {filepath}: {e}")
            return None
    
    def generate_thumbnail(self, filepath, thumbnail_size=(300, 300)):
        """Generate a thumbnail for a photo and save it to the thumbs directory"""
        try:
            # Create thumbs directory if it doesn't exist
            os.makedirs(THUMBS_DIR, exist_ok=True)
            
            # Get the filename from the original path
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            
            # Create thumbnail filename (add _thumb suffix to avoid conflicts)
            thumb_filename = f"{name}_thumb{ext}"
            thumb_path = os.path.join(THUMBS_DIR, thumb_filename)
            
            # Skip if thumbnail already exists and is newer than original
            if os.path.exists(thumb_path):
                try:
                    if os.path.getmtime(thumb_path) >= os.path.getmtime(filepath):
                        return thumb_path
                except (OSError, ValueError):
                    # If we can't get file times, regenerate thumbnail
                    pass
            
            # Open and resize the image
            with Image.open(filepath) as img:
                # Convert to RGB if needed (handles RGBA, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create thumbnail with aspect ratio preserved
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail with high quality
                img.save(thumb_path, 'JPEG', quality=85, optimize=True)
                
            print(f"Generated thumbnail: {thumb_path}")
            return thumb_path
            
        except Exception as e:
            print(f"Warning: Could not generate thumbnail for {filepath}: {e}")
            return None
    
    def batch_generate_thumbnails(self, photo_paths):
        """Generate thumbnails for multiple photos"""
        generated_count = 0
        for filepath in photo_paths:
            if self.generate_thumbnail(filepath):
                generated_count += 1
        print(f"Generated {generated_count} thumbnails out of {len(photo_paths)} photos")
        return generated_count
    
    def move_photo_to_processed(self, filepath, date):
        """Move photo from unprocessed to processed folder with YYYY/MM structure and date prefix"""
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            year = date_obj.strftime('%Y')
            month = date_obj.strftime('%m')
            date_prefix = date_obj.strftime('%Y-%m-%d')
            
            # Create the processed directory structure
            processed_dir = os.path.join(PROCESSED_DIR, year, month)
            os.makedirs(processed_dir, exist_ok=True)
            
            # Get the filename and add date prefix
            original_filename = os.path.basename(filepath)
            
            # Check if filename already has a date prefix (in case of re-processing)
            if original_filename.startswith(date_prefix + '_'):
                # Already has the correct prefix
                base_filename = original_filename
            elif len(original_filename) > 10 and original_filename[10] == '_' and original_filename[:10].count('-') == 2:
                # Has a different date prefix, replace it
                base_filename = date_prefix + '_' + original_filename[11:]
            else:
                # No date prefix, add it
                base_filename = date_prefix + '_' + original_filename
            
            # Handle filename collisions by adding random suffix
            new_filename = base_filename
            new_filepath = os.path.join(processed_dir, new_filename)
            
            # If file exists, generate unique filename with random suffix
            if os.path.exists(new_filepath):
                # Split filename and extension
                filename_without_ext, file_ext = os.path.splitext(base_filename)
                
                # Try up to 100 times to find a unique filename
                for attempt in range(100):
                    # Generate 6-character random suffix
                    random_suffix = secrets.token_hex(3)  # 3 bytes = 6 hex chars
                    new_filename = f"{filename_without_ext}_{random_suffix}{file_ext}"
                    new_filepath = os.path.join(processed_dir, new_filename)
                    
                    # If this filename doesn't exist, we can use it
                    if not os.path.exists(new_filepath):
                        break
                else:
                    # If we couldn't find a unique name after 100 attempts, use timestamp
                    timestamp_suffix = str(int(time.time() * 1000))  # milliseconds
                    new_filename = f"{filename_without_ext}_{timestamp_suffix}{file_ext}"
                    new_filepath = os.path.join(processed_dir, new_filename)
                
                print(f"File collision detected - using unique filename: {new_filename}")
            
            # Move the file
            shutil.move(filepath, new_filepath)
            
            print(f"Moved {original_filename} to {new_filename} in {processed_dir}")
            return new_filepath
        except Exception as e:
            print(f"Warning: Could not move photo to processed folder: {e}")
            return filepath  # Return original path if move failed

photo_manager = PhotoManager()

@app.route('/')
def index():
    import time as perf_time
    start_time = perf_time.time()
    
    page = request.args.get('page', 1, type=int)
    per_page = PHOTOS_PER_PAGE  # Photos per page from environment
    
    # Get individual unprocessed photos from database only
    step1_time = perf_time.time()
    photo_pairs = photo_manager.get_unprocessed_photo_pairs()
    print(f"  - get_unprocessed_photo_pairs: {perf_time.time() - step1_time:.3f}s")
    
    # Get similarity groups for unprocessed photos
    step2_time = perf_time.time()
    similarity_groups = []
    photo_groups = photo_manager.get_cached_photo_groups()
    print(f"  - get_cached_photo_groups: {perf_time.time() - step2_time:.3f}s")
    
    # Skip expensive similarity processing if no groups exist
    if not photo_groups:
        print("  - No similarity groups found, skipping group processing")
        ungrouped_pairs = photo_pairs
        grouped_base_names = set()
    else:
        # Cache these sets to avoid repeated calls in loops
        step3_time = perf_time.time()
        processed_photos_set = set(photo_manager.get_processed_photos())
        ignored_photos_set = set(photo_manager.get_ignored_photos())
        print(f"  - get processed/ignored sets: {perf_time.time() - step3_time:.3f}s")
        
        # Convert similarity groups to the same format as photo_pairs for display
        # Key change: if ANY photo from a base_name is in a similarity group,
        # include ALL photos for that base_name in the group
        step4_time = perf_time.time()
        for group in photo_groups:
            # Get base_names that have photos in this group
            grouped_base_names = set()
            for photo in group['photos']:
                if photo['filepath'] not in processed_photos_set and photo['filepath'] not in ignored_photos_set:
                    grouped_base_names.add(photo['base_name'])
            
            # For each base_name in this group, include ALL its photos (front, back, variants)
            group_photos = {}
            for base_name in grouped_base_names:
                if base_name in photo_pairs:  # Get all photos for this base_name
                    group_photos[base_name] = photo_pairs[base_name].copy()
            
            if group_photos:  # Only add groups that have unprocessed photos
                similarity_groups.append({
                    'group_id': group['id'],
                    'group_name': group['name'],
                    'group_description': group['description'],
                    'similarity_score': group['similarity_score'],
                    'photo_pairs': group_photos
                })
        print(f"  - similarity group processing: {perf_time.time() - step4_time:.3f}s")
        
        # Get base_names that are in similarity groups
        step5_time = perf_time.time()
        grouped_base_names = set()
        for group in similarity_groups:
            for base_name in group['photo_pairs'].keys():
                grouped_base_names.add(base_name)
        
        # Filter out grouped base_names from individual photo_pairs
        # If a base_name is in ANY similarity group, exclude it entirely from individual photos
        ungrouped_pairs = {}
        for base_name, pair in photo_pairs.items():
            if base_name not in grouped_base_names:
                ungrouped_pairs[base_name] = pair
    
    # Combine ungrouped pairs and similarity groups for pagination
    all_items = []
    
    # Add similarity groups first so they appear on early pages
    for group in similarity_groups:
        all_items.append({
            'type': 'group',
            'group_data': group
        })
    
    # Add individual photos after groups
    for base_name, pair in ungrouped_pairs.items():
        all_items.append({
            'type': 'individual',
            'base_name': base_name,
            'photo_pairs': pair
        })
    
    # Calculate pagination
    step6_time = perf_time.time()
    total_items = len(all_items)
    total_pages = (total_items + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get items for current page
    page_items = all_items[start_idx:end_idx]
    print(f"  - pagination: {perf_time.time() - step6_time:.3f}s")
    
    # Separate individual photos and groups for current page
    paginated_ungrouped_pairs = {}
    paginated_similarity_groups = []
    
    for item in page_items:
        if item['type'] == 'individual':
            paginated_ungrouped_pairs[item['base_name']] = item['photo_pairs']
        else:
            paginated_similarity_groups.append(item['group_data'])
    
    # Performance logging
    end_time = perf_time.time()
    elapsed = end_time - start_time
    print(f"Index route took {elapsed:.3f} seconds to load")
    
    return render_template('index.html', 
                         photo_pairs=paginated_ungrouped_pairs, 
                         similarity_groups=paginated_similarity_groups,
                         current_page=page,
                         total_pages=total_pages,
                         total_items=total_items)


@app.route('/photos/<path:filename>')
def serve_photo(filename):
    """Serve photos from the unprocessed directory using absolute paths"""
    try:
        return send_from_directory(UNPROCESSED_DIR, filename)
        
    except OSError as e:
        # Handle files with invalid timestamps or other OS errors
        if e.errno == 22:  # Invalid argument - usually invalid timestamp
            print(f"WARNING: File {filename} has invalid timestamp, serving with custom headers")
            full_path = os.path.join(UNPROCESSED_DIR, filename)
            if os.path.exists(full_path):
                # Read and serve the file manually without timestamp
                from flask import Response
                with open(full_path, 'rb') as f:
                    data = f.read()
                
                # Determine content type
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    mimetype = 'image/jpeg'
                elif filename.lower().endswith('.png'):
                    mimetype = 'image/png'
                elif filename.lower().endswith('.gif'):
                    mimetype = 'image/gif'
                elif filename.lower().endswith(('.tiff', '.tif')):
                    mimetype = 'image/tiff'
                else:
                    mimetype = 'application/octet-stream'
                
                return Response(data, mimetype=mimetype)
            else:
                return "File not found", 404
        else:
            # Re-raise other OSErrors
            raise


@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serve thumbnail images from the thumbs directory"""
    try:
        # Remove _thumb suffix if present to get original filename, then add it back
        if filename.endswith('_thumb.jpg') or filename.endswith('_thumb.jpeg'):
            thumb_filename = filename
        else:
            # Add _thumb suffix to filename
            name, ext = os.path.splitext(filename)
            thumb_filename = f"{name}_thumb{ext}"
        
        thumb_path = os.path.join(THUMBS_DIR, thumb_filename)
        
        # If thumbnail doesn't exist, try to generate it from the original
        if not os.path.exists(thumb_path):
            # Try to find the original photo
            original_path = os.path.join(UNPROCESSED_DIR, filename)
            if os.path.exists(original_path):
                print(f"Generating missing thumbnail for {filename}")
                generated_thumb = photo_manager.generate_thumbnail(original_path)
                if generated_thumb:
                    return send_from_directory(THUMBS_DIR, thumb_filename)
        
        if os.path.exists(thumb_path):
            return send_from_directory(THUMBS_DIR, thumb_filename)
        else:
            # Fallback to original photo if thumbnail generation failed
            return serve_photo(filename)
            
    except Exception as e:
        print(f"Error serving thumbnail {filename}: {e}")
        # Fallback to original photo
        return serve_photo(filename)


@app.route('/ignore_photos', methods=['POST'])
def ignore_photos():
    data = request.get_json()
    base_name = data.get('base_name')
    
    if not base_name:
        return jsonify({'success': False, 'message': 'Missing base_name'})
    
    photo_pairs = photo_manager.get_unprocessed_photo_pairs()
    if base_name not in photo_pairs:
        return jsonify({'success': False, 'message': 'Photo pair not found'})
    
    success = photo_manager.ignore_photo_set(base_name, photo_pairs)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Photo set {base_name} ignored successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to ignore photo set'
        })

@app.route('/update_date', methods=['POST'])
def update_date():
    data = request.get_json()
    base_name = data.get('base_name')
    new_date = data.get('date')
    
    if not base_name or not new_date:
        return jsonify({'success': False, 'message': 'Missing base_name or date'})
    
    try:
        datetime.strptime(new_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD'})
    
    photo_pairs = photo_manager.get_unprocessed_photo_pairs()
    if base_name not in photo_pairs:
        return jsonify({'success': False, 'message': 'Photo pair not found'})
    
    pair = photo_pairs[base_name]
    results = []
    
    for filepath in [pair['front'], pair['back']] + pair.get('variants', []):
        if filepath and os.path.exists(filepath):
            success, message = photo_manager.update_photo_date(filepath, new_date)
            results.append({'file': os.path.basename(filepath), 'success': success, 'message': message})
    
    all_success = all(r['success'] for r in results)
    
    return jsonify({
        'success': all_success,
        'message': 'All photos updated successfully' if all_success else 'Some photos failed to update',
        'results': results
    })

@app.route('/search', methods=['GET'])
def search_photos():
    """Search for photos by filename across all unprocessed photos"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': True,
                'results': [],
                'message': 'No search query provided'
            })
        
        # Get all unprocessed photos from database
        photo_manager = PhotoManager()
        photo_pairs = photo_manager.get_unprocessed_photo_pairs()
        photo_groups = photo_manager.get_cached_photo_groups()
        
        # Search through individual photos and similarity groups
        search_results = []
        
        # Search individual photos
        for base_name, pair in photo_pairs.items():
            # Search in base name and individual filenames
            if query.lower() in base_name.lower():
                search_results.append({
                    'type': 'individual',
                    'base_name': base_name,
                    'front': pair.get('front'),
                    'back': pair.get('back'),
                    'variants': pair.get('variants', []),
                    'match_type': 'base_name'
                })
                continue
            
            # Search in individual file paths
            files_to_search = []
            if pair.get('front'):
                files_to_search.append(('front', pair['front']))
            if pair.get('back'):
                files_to_search.append(('back', pair['back']))
            for variant in pair.get('variants', []):
                files_to_search.append(('variant', variant))
            
            for file_type, filepath in files_to_search:
                filename = os.path.basename(filepath)
                if query.lower() in filename.lower():
                    search_results.append({
                        'type': 'individual',
                        'base_name': base_name,
                        'front': pair.get('front'),
                        'back': pair.get('back'),
                        'variants': pair.get('variants', []),
                        'match_type': f'filename_{file_type}',
                        'matched_file': filename
                    })
                    break  # Only add once per photo pair
        
        # Groups are excluded from search results as requested
        
        return jsonify({
            'success': True,
            'results': search_results,
            'query': query,
            'total_results': len(search_results)
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR: Search failed: {str(e)}")
        print(f"ERROR: Full traceback:")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Search failed: {str(e)}',
            'results': []
        })

@app.route('/scheduler_status', methods=['GET'])
def scheduler_status():
    """Get scheduler status information"""
    try:
        # Import here to avoid issues if scheduler not initialized
        from scheduler import PhotoScheduler
        
        # Create temporary scheduler instance to get status
        temp_scheduler = PhotoScheduler()
        status = temp_scheduler.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting scheduler status: {str(e)}'
        })

# Global scheduler instance for signal handling
scheduler = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    if scheduler:
        print("Stopping scheduler...")
        scheduler.stop()
    print("Flask app shutting down...")
    sys.exit(0)

def health_check():
    """Simple health check endpoint"""
    return "OK", 200

if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("PhotoDate Fix - Initializing...")
    
    try:
        # Create required directories
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        os.makedirs(UNPROCESSED_DIR, exist_ok=True)
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        os.makedirs(THUMBS_DIR, exist_ok=True)
        print("✓ Directories created/verified")
        
        # Initialize and start scheduler
        print("Initializing scheduler...")
        from scheduler import PhotoScheduler
        scheduler = PhotoScheduler()
        scheduler.start()
        print("✓ Scheduler initialized")
        
        # Add health check endpoint
        app.add_url_rule('/health', 'health_check', health_check)
        
        # Flask configuration from environment variables
        debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        port = int(os.getenv('FLASK_PORT', '5000'))
        
        scan_interval = int(os.getenv('SCAN_INTERVAL_HOURS', '1'))
        
        print(f"\nStarting PhotoDate Fix...")
        print(f"  Host: {host}:{port}")
        print(f"  Debug mode: {debug_mode}")
        print(f"  Photos directory: {UNPROCESSED_DIR}")
        print(f"  Processed directory: {PROCESSED_DIR}")
        print(f"  Scheduled processing: {'Enabled' if scan_interval > 0 else 'Disabled'}")
        if scan_interval > 0:
            print(f"  Scan interval: {scan_interval} hours")
        print("  Health check: /health")
        print("\nServer starting...")
        
        # Start Flask with proper configuration for Docker
        app.run(
            debug=debug_mode,
            host=host,
            port=port,
            threaded=True,
            use_reloader=False  # Disable reloader in production/Docker
        )
        
    except Exception as e:
        print(f"Error starting application: {e}")
        if scheduler:
            print("Stopping scheduler...")
            scheduler.stop()
        sys.exit(1)