# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Flask web application designed specifically for users with Epson FastFoto scanners to help them accurately date their scanned photos. The application scans a folder for images (including subfolders), displays them in a user-friendly web interface, and allows users to correct photo dates. The files follow FastFoto naming conventions to group the front and back sides of images together.

### Current Features
- **Individual Photo Processing**: Handle single photo pairs one at a time
- **Similarity Grouping**: Automatically group similar photos together using AI analysis (OpenCV, scikit-image)
- **Batch Date Updates**: Update entire groups of similar photos with the same date
- **Unknown Date Handling**: "Unknown" button sets photos to 1900-01-01 and processes them normally
- **File Collision Prevention**: Automatic filename collision handling with random suffixes
- **File Integrity Protection**: SHA256 hashing with automatic backup and rollback
- **Comprehensive Date Updates**: Updates file timestamps, EXIF data, and metadata
- **Thumbnail Generation**: Automatic thumbnail creation for fast web interface loading
- **Pagination Support**: Handle large photo collections efficiently (configurable items per page)
- **Docker Support**: Full containerization with development and production environments
- **Scheduled Processing**: Optional background scanning and similarity analysis

Once a photo has been given the correct date, it will not show up in the GUI anymore. The application uses a SQLite database to track processed photos and similarity analysis results.

## Current Repository Structure
```
D:\code\photodate-fix\
├── src/                          # Main application source code
│   ├── app.py                   # Main Flask application with PhotoManager class
│   ├── database.py              # SQLite database operations
│   ├── similarity_analyzer.py   # AI-powered photo similarity detection
│   ├── scheduler.py             # Background task scheduler (APScheduler)
│   ├── init_database.py         # Database initialization script
│   ├── cleanup_database.py      # Database maintenance utilities
│   ├── reset_similarity_analysis.py # Reset similarity data
│   ├── run_photo_processing.py  # Batch processing script
│   ├── generate_thumbnails.py   # Thumbnail generation utility
│   ├── static/                  # Web assets
│   │   ├── css/style.css       # Main stylesheet
│   │   └── js/app.js           # Frontend JavaScript with Unknown button logic
│   └── templates/               # Jinja2 HTML templates
│       └── index.html          # Main web interface
├── data/                        # Data directory (excluded from git)
│   ├── photos/
│   │   ├── unprocessed/        # Scanned photos awaiting processing
│   │   └── processed/YYYY/MM/  # Date-organized processed photos
│   ├── db/photo_scanner.db     # SQLite database
│   └── thumbs/                 # Generated thumbnails
├── requirements.txt             # Python dependencies (includes APScheduler)
├── Dockerfile                   # Production container
├── Dockerfile.dev              # Development container with live reload
├── docker-compose.yml          # Production Docker setup
├── docker-compose.dev.yml      # Development Docker setup with mounted code
├── dev.bat / dev.sh            # Quick Docker development startup
├── DEV_SETUP.md               # Comprehensive development guide
└── .env.example               # Environment configuration template
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify the values:

### Key Configuration Options

- **PHOTOS_PER_PAGE**: Number of photos displayed per page (default: 250)
- **PHOTOS_UNPROCESSED_DIR**: Directory for unprocessed photos
  - Docker: `/app/data/photos/unprocessed`
  - Local: `./data/photos/unprocessed`
- **PHOTOS_PROCESSED_DIR**: Directory for processed photos
  - Docker: `/app/data/photos/processed`
  - Local: `./data/photos/processed`
- **SIMILARITY_EPS**: Similarity tolerance for photo grouping (default: 0.3)
  - Lower values = stricter grouping (more groups)
  - Higher values = looser grouping (fewer, larger groups)
- **SIMILARITY_MIN_SAMPLES**: Minimum photos required for a group (default: 2)
- **FLASK_DEBUG**: Enable Flask debug mode (default: True for dev, False for prod)
- **FLASK_HOST**: Flask server host (default: 0.0.0.0)
- **FLASK_PORT**: Flask server port (default: 5000)
- **SCAN_INTERVAL_HOURS**: Automatic scanning interval (default: 1, set to 0 to disable)

## Development Setup

### Recommended: Docker Development (No Local Dependencies)

**Quick Start:**
```bash
# Windows
dev.bat

# Linux/Mac  
chmod +x dev.sh && ./dev.sh

# Manual
docker-compose -f docker-compose.dev.yml up --build
```

**Features:**
- ✅ No local Python dependencies needed
- ✅ Live code updates (mounted volumes)
- ✅ All dependencies included in container
- ✅ Access at http://localhost:5000
- ✅ Automatic .env and data directory creation

### Alternative: Local Python Development

**Prerequisites:**
- Python 3.11+ required
- All dependencies in `requirements.txt`

**Quick Setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Run application
python src/app.py
```

**Using Setup Scripts:**
```bash
# Windows: Creates venv, installs deps, runs app
run_dev.bat

# Cross-platform: Handles dependencies automatically  
python run_dev.py
```

## Architecture Notes

### Core Components
- **PhotoManager Class** (`src/app.py`): Handles all photo operations including scanning, date updates, file integrity, and collision prevention
- **SimilarityAnalyzer Class** (`src/similarity_analyzer.py`): AI-powered photo similarity detection and grouping using computer vision
- **DatabaseManager Class** (`src/database.py`): SQLite database operations for photo tracking and similarity groups
- **PhotoScheduler Class** (`src/scheduler.py`): Background task scheduling with APScheduler
- **Flask Routes** (`src/app.py`): Web interface with individual/batch date updates and Unknown button handling
- **File Integrity System**: SHA256 hashing with backup/restore capability for safe file modifications

### Photo Processing Pipeline
1. **Scan**: Recursively scan `data/photos/unprocessed`, excluding already processed files
2. **Thumbnail Generation**: Create thumbnails for fast web interface loading
3. **Similarity Analysis**: Analyze photos using computer vision (OpenCV, scikit-image) to detect similar images
4. **Group Creation**: Create similarity groups and pair photos based on FastFoto naming convention
5. **Web Display**: Show individual photos and similarity groups with pagination
6. **Date Processing**: Handle date updates, Unknown button (1900-01-01), and batch operations
7. **File Operations**: Update timestamps, EXIF data, handle filename collisions, move to processed folder
8. **Database Update**: Track processed photos and maintain similarity group relationships

### FastFoto Naming Convention Support
- `FastFoto_XXXX.jpg` - Front/primary image from Epson FastFoto scanner
- `FastFoto_XXXX_a.jpg` - Back of the same photo  
- `FastFoto_XXXX_b.jpg` - Additional variants or duplicates
- `YYYY-MM-DD_FastFoto_XXXX.jpg` - Date-prefixed versions (moved to processed folder)
- `YYYY-MM-DD_FastFoto_XXXX_randomsuffix.jpg` - Collision-prevented versions
- Supports subfolders within the unprocessed directory
- Processed photos organized in `data/photos/processed/YYYY/MM/` structure
- Handles various formats: JPG, JPEG, PNG, GIF, BMP, TIFF

### Web Interface Features
- **Individual Photos Section**: Process single photo pairs with manual date entry
- **Similarity Groups Section**: View and process groups of similar photos together
- **Unknown Button**: Sets date to 1900-01-01 and processes photos normally (replaces old "Ignore" functionality)
- **Batch Date Updates**: Set one date for entire groups of similar photos
- **Photo Modal**: Click any photo to view full size with loading states
- **Pagination**: Handle large photo collections efficiently (configurable page size)
- **Real-time Status Messages**: Feedback for all operations with error details
- **Responsive Design**: Works on desktop and mobile devices

## Recent Changes & Current State

### Unknown Date Functionality
- **Unknown Button**: Renamed from "Ignore" - now sets photos to 1900-01-01 and processes them fully
- **Behavior**: Identical to Update Date but with automatic date of 1900-01-01
- **Processing**: Photos are moved to processed folder, timestamps updated, EXIF data modified

### File Collision Prevention
- **Automatic Handling**: Detects filename collisions when moving to processed folder
- **Random Suffixes**: Uses cryptographically secure random 6-character hex suffixes
- **Extension Preservation**: Maintains original file type/extension
- **Fallback Logic**: 100 random attempts, then timestamp suffix if needed
- **Example**: `2023-05-15_FastFoto_1234_a3f2b1.jpg`

### Docker Development Environment
- **Live Code Updates**: Changes reflected immediately without container rebuild
- **Development Container**: `Dockerfile.dev` with mounted source code
- **Production Container**: `Dockerfile` optimized for deployment
- **Quick Scripts**: `dev.bat`/`dev.sh` for instant setup

### Database & Dependencies
- **Requirements File**: All dependencies now centralized in `requirements.txt`
- **APScheduler Support**: Background task scheduling included
- **SQLite Database**: `data/db/photo_scanner.db` for all persistence
- **Legacy Support**: Still reads `processed_photos.json` if database unavailable

## Common Development Tasks

### Adding New Photos for Testing
1. Place photos in `data/photos/unprocessed/` directory
2. Follow FastFoto naming convention for proper pairing
3. Refresh web interface or restart app to see new photos
4. Run similarity analysis: `python src/run_photo_processing.py`

### Processing Individual Photos
1. Open web interface at `http://localhost:5000`
2. Navigate to "Individual Photos" section  
3. Enter correct date OR click "Unknown" for 1900-01-01
4. Photos are updated and moved to `data/photos/processed/YYYY/MM/`

### Processing Photo Groups (Batch Updates)
1. Navigate to similarity groups in web interface
2. Review grouped photos for accuracy
3. Enter date in batch date field at bottom of group
4. Click "Batch Update Dates" - all photos get same date and are moved

### Database Management
- **View Data**: Use any SQLite browser on `data/db/photo_scanner.db`
- **Cleanup**: `python src/cleanup_database.py` - removes entries for missing files
- **Reset Similarity**: `python src/reset_similarity_analysis.py` - clears similarity data
- **Initialize**: `python src/init_database.py` - creates fresh database

### Development Debugging
- **Container Logs**: `docker-compose -f docker-compose.dev.yml logs -f`
- **File Integrity**: Check for `.backup` files if operations fail
- **Database Issues**: App gracefully falls back to JSON file storage
- **EXIF Problems**: Logged as warnings but don't stop processing

## Important Implementation Details

### File Safety & Integrity
- **Backup Creation**: Always creates `.backup` files before modifications
- **SHA256 Verification**: Integrity checking before and after file operations
- **Atomic Operations**: All file operations succeed or fail together
- **Automatic Rollback**: Corruption detection triggers automatic restore from backup
- **Transaction Safety**: Database operations use transactions with rollback capability

### Date Handling & Formats
- **Input Format**: YYYY-MM-DD (HTML date input standard)
- **EXIF Format**: YYYY:MM:DD HH:MM:SS (automatically converted)
- **File Timestamps**: Unix timestamp (converted from input date)
- **Special Dates**: 1900-01-01 for unknown dates, handles edge cases gracefully
- **Batch Processing**: Applies same date to all photos in similarity group

### Error Handling & Recovery
- **Graceful Degradation**: Missing EXIF support doesn't stop processing
- **Network Resilience**: Frontend handles connection errors and retries
- **File Recovery**: Automatic backup restoration on any file corruption
- **Database Resilience**: Falls back to JSON storage if SQLite unavailable
- **Detailed Logging**: Comprehensive error tracking for debugging
- **User Feedback**: Clear error messages and success confirmations in web interface

### Performance & Scalability  
- **Thumbnail System**: Fast loading with lazy loading and error handling
- **Pagination**: Configurable page sizes for large photo collections
- **Background Processing**: Optional scheduled scanning to reduce on-demand load
- **Similarity Caching**: Database storage of similarity analysis results
- **Efficient Scanning**: Only processes new/changed files

## File Locations for Reference
- **Main App**: `src/app.py` (Flask routes, PhotoManager class, file operations)
- **Frontend JS**: `src/static/js/app.js` (Unknown button logic, form handling)  
- **Database**: `src/database.py` (SQLite operations, schema management)
- **Similarity**: `src/similarity_analyzer.py` (Computer vision, grouping algorithms)
- **Scheduler**: `src/scheduler.py` (Background tasks, APScheduler integration)
- **Templates**: `src/templates/index.html` (Main web interface)
- **Configuration**: `.env` (environment variables, copied from `.env.example`)

This project is actively maintained and includes comprehensive error handling, file safety measures, and modern development tooling for reliable photo processing workflows.