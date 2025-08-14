# PhotoDate Fix

A Flask web application designed specifically for **Epson FastFoto scanner** users to help accurately date their scanned photos. This tool solves the common problem of scanned photos having incorrect dates by providing an intuitive interface to review and correct photo dates, with automatic updates to EXIF data, file timestamps, and metadata.

## 🎯 Why This Tool?

When using Epson FastFoto scanners, photos often get scanned with incorrect dates (usually the scan date rather than when the photo was actually taken). This application helps you:

- **Review scanned photos** with their front and back sides paired together
- **Correct dates efficiently** using individual or batch update methods
- **Automatically group similar photos** for faster processing
- **Safely update all date information** in files (EXIF, timestamps, metadata)
- **Track processed photos** so they don't appear again

## ✨ Features

### 🖼️ Smart Photo Management
- **Automatic photo pairing**: Groups front and back sides of photos based on FastFoto naming conventions
- **AI-powered similarity grouping**: Uses computer vision to group similar or duplicate photos
- **Recursive folder scanning**: Processes photos in subdirectories
- **Multiple format support**: JPG, PNG, GIF, BMP, TIFF

### 🔄 Flexible Processing Options
- **Individual photo processing**: Handle one photo pair at a time
- **Batch date updates**: Set the same date for entire groups of similar photos
- **Real-time preview**: Click any photo to view full size
- **Progress tracking**: Visual feedback for all operations

### 🛡️ File Safety & Integrity
- **Automatic backups**: Creates backup copies before any modification
- **SHA256 integrity checking**: Detects file corruption and auto-restores
- **Atomic operations**: All related files succeed or fail together
- **Transaction-based database**: Ensures data consistency

### 💻 User-Friendly Interface
- **Responsive web design**: Works on desktop and mobile
- **Pagination support**: Handles large photo collections
- **Modal photo viewer**: Full-size photo inspection
- **Keyboard shortcuts**: Efficient navigation and input

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher (for native installation)
- Docker and Docker Compose (for Docker installation)
- Epson FastFoto scanned photos (or similar naming convention)

### Installation Options

#### Option 1: Docker (Recommended)
```bash
# 1. Clone the repository
git clone <repository-url>
cd photodate-fix

# 2. Configure environment (optional)
cp .env.example .env
# Edit .env with your preferences

# 3. Add your scanned photos to data/photos/unprocessed/

# 4. Run with Docker
docker-compose up -d

# 5. Access at http://localhost:5000
```

For detailed Docker setup instructions, see [docker-README.md](docker-README.md).

#### Option 2: Native Installation

#### Windows (Recommended)
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/photodate-fix.git
cd photodate-fix

# 2. Run the automated setup
setup_venv.bat
install_grouping_deps.bat

# 3. Configure application settings
copy .env.example .env
# Edit .env file with your preferred settings (optional - defaults work fine)

# 4. Add your scanned photos to the photos/unprocessed/ directory

# 5. Run the application
venv\Scripts\activate.bat
python app.py
```

#### Linux/macOS
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/photodate-fix.git
cd photodate-fix

# 2. Set up virtual environment
./setup_venv.sh
source venv/bin/activate

# 3. Install additional dependencies
pip install opencv-python scikit-image numpy

# 4. Configure application settings
cp .env.example .env
# Edit .env file with your preferred settings (optional - defaults work fine)

# 5. Add your scanned photos to the photos/unprocessed/ directory

# 6. Run the application
python app.py
```

### First Time Setup
1. Place your FastFoto scanned photos in the `photos/unprocessed/` directory
2. Open your browser to `http://localhost:5000`
3. The application will automatically scan and group your photos
4. Start correcting dates using individual or batch methods

## 📁 FastFoto Naming Convention

The application recognizes Epson FastFoto naming patterns:

```
FastFoto_0001.jpg        # Front of photo
FastFoto_0001_a.jpg      # Back of the same photo
FastFoto_0001_b.jpg      # Additional variant/duplicate
```

After processing, files are moved to organized folders with date prefixes:
```
photos/processed/2023/07/2023-07-15_FastFoto_0001.jpg
photos/processed/2023/07/2023-07-15_FastFoto_0001_a.jpg
```

## 🔧 Usage

### Individual Photo Processing
1. Navigate to the "Individual Photos" section
2. Review each photo pair (front and back)
3. Enter the correct date for the photo
4. Click "Update Date" - all related files are updated and moved to organized date folders
5. Processed photos disappear from the interface and are moved to `photos/processed/YYYY/MM/`

### Batch Processing with Similarity Groups
1. Run similarity analysis: `run_photo_processing.bat` (Windows) or `python run_photo_processing.py`
2. Review automatically grouped similar photos
3. Enter a date in the batch date field at the bottom of each group
4. Click "Batch Update Dates" to update all photos in the group and move them to organized date folders
5. Entire groups disappear once processed and moved to `photos/processed/YYYY/MM/`

### Advanced Operations
```bash
# Batch process all photos with similarity analysis
run_photo_processing.bat

# Scan for new photos only (no similarity analysis)
scan_photos_only.bat

# Clean up database entries for moved/deleted files
python cleanup_database.py

# Reset all similarity analysis (regroup photos)
python reset_similarity_analysis.py
```

## 🏗️ Architecture

### Core Components
- **PhotoManager**: Handles photo scanning, date updates, and file operations
- **SimilarityAnalyzer**: AI-powered photo similarity detection using OpenCV
- **Database Module**: SQLite database for tracking processed photos and groups
- **Web Interface**: Flask-based responsive web application

### Data Storage
- **SQLite Database** (`photo_scanner.db`): Primary data storage
- **Legacy JSON Support** (`processed_photos.json`): Backwards compatibility
- **Automatic Backups**: `.backup` files created before any modification

### Safety Features
- File integrity verification using SHA256 hashes
- Automatic rollback on corruption detection
- Atomic file operations (all succeed or all fail)
- Transaction-based database operations

## 🛠️ Development

### Project Structure

#### Docker Structure (Recommended)
```
photodate-fix/
├── src/                    # Application source code
│   ├── app.py             # Main Flask application
│   ├── database.py        # Database management
│   ├── similarity_analyzer.py # AI photo similarity
│   ├── static/            # CSS and JavaScript
│   ├── templates/         # HTML templates
│   └── requirements.txt   # Python dependencies
├── data/                  # Persistent data (Docker volumes)
│   ├── photos/
│   │   ├── unprocessed/   # Your scanned photos
│   │   └── processed/     # Processed photos by date
│   └── db/               # SQLite database
├── Dockerfile            # Container build instructions
├── docker-compose.yml    # Docker orchestration
└── .env                 # Environment configuration
```

## 🐛 Troubleshooting

### Common Issues

**Photos not appearing in interface:**
- Ensure photos are in `photos/unprocessed/` directory
- Check that files follow FastFoto naming convention
- Run `cleanup_database.py` to remove orphaned entries

**Similarity grouping not working:**
- Install required dependencies: `pip install opencv-python scikit-image numpy`
- Run `reset_similarity_analysis.py` to reprocess groupings

**Date updates failing:**
- Check file permissions (photos should be writable)
- Verify EXIF support for your image format
- Review backup files (`.backup` extension) for recovery

**Database issues:**
- Delete `photo_scanner.db` to reset (will reprocess all photos)

## 📝 License

This project is licensed under the MIT License

## 🙏 Acknowledgments

- Built for the Epson FastFoto scanner community
- Uses OpenCV and scikit-image for computer vision features
- Flask framework for the web interface

## 🔗 Related Projects

- [Epson FastFoto Software](https://epson.com/fastfoto) - Official Epson scanning software
- [ExifTool](https://exiftool.org/) - Command-line application for reading/writing EXIF data

---

**Made with ❤️ for FastFoto users who want their photos properly dated!**