import sqlite3
import json
import os
import time
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Database path - can be overridden via environment with absolute path handling
def get_absolute_database_path():
    """Convert database path to absolute path"""
    path = os.getenv('DATABASE_PATH', './data/db/photo_scanner.db')
    if os.path.isabs(path):
        return path
    # Make relative paths relative to the project root (parent of src/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, path.lstrip('./'))

DATABASE_PATH = get_absolute_database_path()

class DatabaseManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        # Ensure database directory exists with proper error handling
        try:
            db_dir = os.path.dirname(self.db_path)
            print(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
            
            # Verify directory was created and is writable
            if not os.path.exists(db_dir):
                raise OSError(f"Failed to create database directory: {db_dir}")
            if not os.access(db_dir, os.W_OK):
                raise OSError(f"Database directory is not writable: {db_dir}")
                
            print(f"Database directory ready: {db_dir}")
            print(f"Database path: {self.db_path}")
            
        except Exception as e:
            print(f"Error setting up database directory: {e}")
            raise
            
        self.init_database()
        self.run_migrations()
        self.migrate_from_json()
    
    def get_connection(self):
        """Get a database connection with proper concurrency settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 30 second timeout for locks
            check_same_thread=False  # Allow multi-threading
        )
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=1000')
        conn.execute('PRAGMA temp_store=memory')
        conn.execute('PRAGMA busy_timeout=30000')  # 30 second busy timeout
        
        return conn
    
    def execute_with_retry(self, operation_func, max_retries=3):
        """Execute a database operation with retry logic for handling locks"""
        for attempt in range(max_retries):
            try:
                return operation_func()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Database locked, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
            except Exception as e:
                # Don't retry other exceptions
                raise
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            print(f"Initializing database at: {self.db_path}")
            conn = self.get_connection()
            cursor = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
        
        # Photos table - main photo metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                base_name TEXT NOT NULL,
                file_type TEXT NOT NULL,  -- 'front', 'back', 'variant'
                default_date TEXT,  -- extracted from EXIF or file creation date (YYYY-MM-DD format)
                processed_date TIMESTAMP,
                ignored_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Photo groups table - for similar photo groupings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Photo group memberships - many-to-many relationship
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo_group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos (id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES photo_groups (id) ON DELETE CASCADE,
                UNIQUE (photo_id, group_id)
            )
        ''')
        
        # Photo embeddings - for similarity analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                embedding_type TEXT NOT NULL,  -- 'face', 'scene', 'combined'
                embedding_data BLOB NOT NULL,  -- serialized numpy array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos (id) ON DELETE CASCADE,
                UNIQUE (photo_id, embedding_type)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_base_name ON photos (base_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_processed ON photos (processed_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_ignored ON photos (ignored_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_members_photo ON photo_group_members (photo_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_members_group ON photo_group_members (group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_photo ON photo_embeddings (photo_id)')
        
        try:
            conn.commit()
            print("Database tables and indexes created successfully")
        except Exception as e:
            print(f"Error committing database changes: {e}")
            raise
        finally:
            conn.close()
    
    def run_migrations(self):
        """Run database migrations for schema updates"""
        try:
            print("Running database migrations...")
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if default_date column exists
            cursor.execute("PRAGMA table_info(photos)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'default_date' not in columns:
                print("Adding default_date column to photos table...")
                cursor.execute('ALTER TABLE photos ADD COLUMN default_date TEXT')
                conn.commit()
                print("✓ Added default_date column")
            
            conn.close()
            print("Database migrations completed")
            
        except Exception as e:
            print(f"Error running database migrations: {e}")
            # Don't raise - migrations are optional
    
    def migrate_from_json(self):
        """Migrate existing JSON data to SQLite if files exist"""
        # Migrate processed photos
        if os.path.exists('processed_photos.json'):
            try:
                with open('processed_photos.json', 'r') as f:
                    processed_photos = json.load(f)
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for filepath in processed_photos:
                    cursor.execute('''
                        INSERT OR IGNORE INTO photos (filepath, base_name, file_type, processed_date)
                        VALUES (?, ?, ?, ?)
                    ''', (filepath, self._extract_base_name(os.path.basename(filepath)), 
                          self._determine_file_type(os.path.basename(filepath)), datetime.now()))
                
                conn.commit()
                conn.close()
                
                # Backup and remove old file
                os.rename('processed_photos.json', 'processed_photos.json.backup')
                print("Migrated processed_photos.json to database")
                
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Migrate ignored photos
        if os.path.exists('ignored_photos.json'):
            try:
                with open('ignored_photos.json', 'r') as f:
                    ignored_photos = json.load(f)
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for filepath in ignored_photos:
                    cursor.execute('''
                        INSERT OR IGNORE INTO photos (filepath, base_name, file_type, ignored_date)
                        VALUES (?, ?, ?, ?)
                    ''', (filepath, self._extract_base_name(os.path.basename(filepath)), 
                          self._determine_file_type(os.path.basename(filepath)), datetime.now()))
                
                conn.commit()
                conn.close()
                
                # Backup and remove old file
                os.rename('ignored_photos.json', 'ignored_photos.json.backup')
                print("Migrated ignored_photos.json to database")
                
            except (json.JSONDecodeError, FileNotFoundError):
                pass
    
    def _extract_base_name(self, filename: str) -> str:
        """Extract base name from filename (copied from PhotoManager)"""
        import re
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
    
    def _determine_file_type(self, filename: str) -> str:
        """Determine if file is front, back, or variant"""
        if filename.endswith('_a.jpg') or filename.endswith('_a.jpeg'):
            return 'front'
        elif filename.endswith('_b.jpg') or filename.endswith('_b.jpeg'):
            return 'back'
        else:
            return 'variant'
    
    # Photo operations
    def get_all_photo_paths(self) -> List[str]:
        """Get all photo file paths from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT filepath FROM photos')
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result
    
    def get_all_photos(self) -> List[Dict]:
        """Get all photos from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT filepath, base_name, file_type FROM photos')
        result = [{'filepath': row[0], 'base_name': row[1], 'file_type': row[2]} for row in cursor.fetchall()]
        conn.close()
        return result
    
    def batch_add_photos(self, photos: List[Tuple[str, str, str, str]]):
        """Batch add multiple photos to database with default dates"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executemany('''
            INSERT OR IGNORE INTO photos (filepath, base_name, file_type, default_date) 
            VALUES (?, ?, ?, ?)
        ''', photos)
        
        conn.commit()
        conn.close()
    
    def add_photo(self, filepath: str, base_name: str, file_type: str, default_date: str = None) -> int:
        """Add a new photo to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO photos (filepath, base_name, file_type, default_date, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (filepath, base_name, file_type, default_date))
        
        photo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return photo_id
    
    def mark_photo_processed(self, old_filepath: str, new_filepath: str = None):
        """Mark a photo as processed and update its filepath if moved"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if new_filepath:
            # Update both the processed status and the new filepath
            cursor.execute('''
                UPDATE photos 
                SET filepath = ?, processed_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE filepath = ?
            ''', (new_filepath, old_filepath))
        else:
            # Just mark as processed without changing filepath
            cursor.execute('''
                UPDATE photos 
                SET processed_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE filepath = ?
            ''', (old_filepath,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected == 0:
            print(f"Warning: No photo found in database with filepath: {old_filepath}")
        
        return rows_affected > 0
    
    def cleanup_missing_photos(self) -> int:
        """Remove database entries for photos that no longer exist on disk"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all photos
        cursor.execute('SELECT id, filepath FROM photos')
        all_photos = cursor.fetchall()
        
        missing_photo_ids = []
        for photo in all_photos:
            photo_id, filepath = photo
            if not os.path.exists(filepath):
                missing_photo_ids.append(photo_id)
                print(f"Found missing photo: {filepath}")
        
        if missing_photo_ids:
            # Remove from photo_group_members first (foreign key constraint)
            placeholders = ','.join('?' * len(missing_photo_ids))
            cursor.execute(f'DELETE FROM photo_group_members WHERE photo_id IN ({placeholders})', missing_photo_ids)
            
            # Remove from photo_embeddings
            cursor.execute(f'DELETE FROM photo_embeddings WHERE photo_id IN ({placeholders})', missing_photo_ids)
            
            # Remove from photos table
            cursor.execute(f'DELETE FROM photos WHERE id IN ({placeholders})', missing_photo_ids)
            
            print(f"Cleaned up {len(missing_photo_ids)} missing photos from database")
        
        conn.commit()
        conn.close()
        
        return len(missing_photo_ids)
    
    def mark_photo_ignored(self, filepath: str):
        """Mark a photo as ignored"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE photos 
            SET ignored_date = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE filepath = ?
        ''', (filepath,))
        
        conn.commit()
        conn.close()
    
    def get_processed_photos(self) -> List[str]:
        """Get list of processed photo filepaths"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT filepath FROM photos WHERE processed_date IS NOT NULL')
        results = [row['filepath'] for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_ignored_photos(self) -> List[str]:
        """Get list of ignored photo filepaths"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT filepath FROM photos WHERE ignored_date IS NOT NULL')
        results = [row['filepath'] for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_unprocessed_photos(self) -> List[Dict]:
        """Get list of unprocessed and unignored photos grouped by base_name"""
        def _get_photos():
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT filepath, base_name, file_type, default_date
                FROM photos 
                WHERE processed_date IS NULL AND ignored_date IS NULL
                ORDER BY base_name, file_type
            ''')
            
            results = cursor.fetchall()
            conn.close()
            return results
        
        results = self.execute_with_retry(_get_photos)
        
        # Group by base_name
        photo_pairs = {}
        for row in results:
            base_name = row['base_name']
            if base_name not in photo_pairs:
                photo_pairs[base_name] = {
                    'front': None, 
                    'back': None, 
                    'variants': [], 
                    'default_date': None
                }
            
            if row['file_type'] == 'front':
                photo_pairs[base_name]['front'] = row['filepath']
                # Use the front photo's default date for the pair
                if row['default_date']:
                    photo_pairs[base_name]['default_date'] = row['default_date']
            elif row['file_type'] == 'back':
                photo_pairs[base_name]['back'] = row['filepath']
                # If no front photo default date, use back photo's
                if not photo_pairs[base_name]['default_date'] and row['default_date']:
                    photo_pairs[base_name]['default_date'] = row['default_date']
            else:
                photo_pairs[base_name]['variants'].append(row['filepath'])
        
        return photo_pairs
    
    # Group operations
    def create_photo_group(self, name: str = None, description: str = None, similarity_score: float = None) -> int:
        """Create a new photo group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO photo_groups (name, description, similarity_score)
            VALUES (?, ?, ?)
        ''', (name, description, similarity_score))
        
        group_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return group_id
    
    def add_photo_to_group(self, photo_filepath: str, group_id: int, similarity_score: float = None):
        """Add a photo to a group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get photo_id
        cursor.execute('SELECT id FROM photos WHERE filepath = ?', (photo_filepath,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        photo_id = result['id']
        
        cursor.execute('''
            INSERT OR REPLACE INTO photo_group_members (photo_id, group_id, similarity_score)
            VALUES (?, ?, ?)
        ''', (photo_id, group_id, similarity_score))
        
        conn.commit()
        conn.close()
        return True
    
    def get_photo_groups(self) -> List[Dict]:
        """Get all photo groups with their members using optimized single query"""
        def _get_groups():
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Single query to get all groups and their photos
            cursor.execute('''
                SELECT pg.id as group_id, pg.name, pg.description, pg.similarity_score, pg.created_at,
                       p.filepath, p.base_name, p.file_type, pgm.similarity_score as member_score
                FROM photo_groups pg
                LEFT JOIN photo_group_members pgm ON pg.id = pgm.group_id
                LEFT JOIN photos p ON pgm.photo_id = p.id
                ORDER BY pg.created_at DESC, p.base_name, p.file_type
            ''')
            
            results = cursor.fetchall()
            conn.close()
            return results
        
        results = self.execute_with_retry(_get_groups)
        
        # Group the results
        groups_dict = {}
        for row in results:
            row_dict = dict(row)
            group_id = row_dict['group_id']
            
            if group_id not in groups_dict:
                groups_dict[group_id] = {
                    'id': group_id,
                    'name': row_dict['name'],
                    'description': row_dict['description'],
                    'similarity_score': row_dict['similarity_score'],
                    'created_at': row_dict['created_at'],
                    'photos': [],
                    'photo_count': 0
                }
            
            # Only add photo if it exists (LEFT JOIN might return None)
            if row_dict['filepath']:
                groups_dict[group_id]['photos'].append({
                    'filepath': row_dict['filepath'],
                    'base_name': row_dict['base_name'],
                    'file_type': row_dict['file_type'],
                    'similarity_score': row_dict['member_score']
                })
                groups_dict[group_id]['photo_count'] += 1
        
        return list(groups_dict.values())
    
    # Embedding operations
    def store_photo_embedding(self, photo_filepath: str, embedding_type: str, embedding_data: bytes):
        """Store photo embedding for similarity analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get photo_id
        cursor.execute('SELECT id FROM photos WHERE filepath = ?', (photo_filepath,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False
        
        photo_id = result['id']
        
        cursor.execute('''
            INSERT OR REPLACE INTO photo_embeddings (photo_id, embedding_type, embedding_data)
            VALUES (?, ?, ?)
        ''', (photo_id, embedding_type, embedding_data))
        
        conn.commit()
        conn.close()
        return True
    
    def get_photo_embeddings(self, embedding_type: str = None) -> List[Tuple[str, bytes]]:
        """Get photo embeddings for similarity analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if embedding_type:
            cursor.execute('''
                SELECT p.filepath, pe.embedding_data
                FROM photos p
                JOIN photo_embeddings pe ON p.id = pe.photo_id
                WHERE pe.embedding_type = ?
            ''', (embedding_type,))
            results = [(row['filepath'], row['embedding_data']) for row in cursor.fetchall()]
        else:
            cursor.execute('''
                SELECT p.filepath, pe.embedding_data, pe.embedding_type
                FROM photos p
                JOIN photo_embeddings pe ON p.id = pe.photo_id
            ''')
            results = [(row['filepath'], row['embedding_data']) for row in cursor.fetchall()]
        
        conn.close()
        return results