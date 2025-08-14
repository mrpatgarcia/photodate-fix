# PhotoDate Fix - Docker Setup

This document explains how to run PhotoDate Fix using Docker and Docker Compose.

## 🐳 Docker Overview

The application is containerized for easy deployment across Windows, Linux, and macOS systems. The Docker setup includes:

- **Minimal Python 3.11 slim image** for small footprint
- **Non-root user** for security
- **Persistent data volumes** for photos and database
- **Environment variable configuration**
- **Health checks** for container monitoring

## 📁 Project Structure

```
photodate-fix/
├── src/                    # Application source code
│   ├── app.py             # Main Flask application
│   ├── database.py        # Database management
│   ├── similarity_analyzer.py # AI photo similarity
│   ├── run_photo_processing.py # Batch processing
│   ├── static/            # CSS and JavaScript
│   ├── templates/         # HTML templates
│   └── requirements.txt   # Python dependencies
├── data/                  # Persistent data (mounted as volumes)
│   ├── photos/
│   │   ├── unprocessed/   # Place your FastFoto scans here
│   │   └── processed/     # Processed photos organized by date
│   └── db/               # SQLite database storage
├── Dockerfile            # Container build instructions
├── docker-compose.yml    # Multi-container orchestration
├── .dockerignore        # Files to exclude from build
└── .env                 # Environment configuration
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- FastFoto scanned photos ready for processing

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd photodate-fix

# Copy and customize environment file
cp .env.example .env
# Edit .env with your preferences (optional - defaults work fine)
```

### 2. Add Your Photos
```bash
# Place your FastFoto scanned photos in the data directory
cp /path/to/your/photos/* data/photos/unprocessed/
```

### 3. Run with Docker Compose
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### 4. Access the Application
- Open your browser to `http://localhost:5000`
- Process your photos using individual or batch methods
- Processed photos will be moved to `data/photos/processed/YYYY/MM/`

## ⚙️ Environment Configuration

The `.env` file controls application behavior:

```bash
# Pagination
PHOTOS_PER_PAGE=250

# Similarity Analysis
SIMILARITY_EPS=0.3          # Lower = stricter grouping
SIMILARITY_MIN_SAMPLES=2    # Minimum photos per group

# Flask Settings
FLASK_PORT=5000
FLASK_DEBUG=false           # Set to true for development
FLASK_SECRET_KEY=change-me  # Use a secure random key
```

## 🐳 Docker Commands

### Building and Running
```bash
# Build the image
docker-compose build

# Start in foreground (see logs)
docker-compose up

# Start in background
docker-compose up -d

# Rebuild and restart
docker-compose up --build -d
```

### Maintenance
```bash
# View logs
docker-compose logs -f fastfoto-scanner

# Execute commands in container
docker-compose exec fastfoto-scanner bash

# Run photo processing manually
docker-compose exec fastfoto-scanner python src/run_photo_processing.py

# Restart the service
docker-compose restart fastfoto-scanner
```

### Data Management
```bash
# Backup processed photos
docker run --rm -v $(pwd)/data:/backup alpine tar czf /backup/photos-backup.tar.gz -C /backup photos/processed

# Backup database
cp data/db/photo_scanner.db data/db/photo_scanner_backup_$(date +%Y%m%d).db
```

## 🔧 Advanced Configuration

### Custom Ports
To run on a different port, update your `.env`:
```bash
FLASK_PORT=8080
```
Then update `docker-compose.yml` ports mapping:
```yaml
ports:
  - "8080:5000"
```

### Volume Mounting
The Docker setup uses bind mounts for easy access to your photos:
- `./data/photos/unprocessed` → `/app/data/photos/unprocessed`
- `./data/photos/processed` → `/app/data/photos/processed`
- `./data/db` → `/app/data/db`

### Performance Tuning
For large photo collections, adjust these settings in `.env`:
```bash
PHOTOS_PER_PAGE=100        # Reduce for faster loading
SIMILARITY_EPS=0.5         # Increase for looser grouping
```

## 🐞 Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs fastfoto-scanner

# Verify environment file
cat .env

# Ensure data directories exist
ls -la data/photos/
```

### Permission Issues
```bash
# Fix ownership (Linux/macOS)
sudo chown -R $USER:$USER data/

# On Windows, ensure Docker has access to the drive
# Check Docker Desktop → Settings → Resources → File Sharing
```

### Database Issues
```bash
# Reset database
rm data/db/photo_scanner.db
docker-compose restart fastfoto-scanner
```

### Memory/CPU Issues
```bash
# Add resource limits to docker-compose.yml
services:
  fastfoto-scanner:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## 🔒 Security Notes

- Container runs as non-root user `scanner`
- No sensitive data in the Docker image
- Environment variables for configuration
- Health checks monitor application status
- Database and photos stored in mounted volumes (not in container)

## 🚀 Production Deployment

For production use:

1. **Update environment variables**:
   ```bash
   FLASK_DEBUG=false
   FLASK_SECRET_KEY=your-secure-random-key
   ```

2. **Use a reverse proxy** (nginx, Traefik, etc.)

3. **Set up regular backups** of the `data/` directory

4. **Monitor logs** and set up log rotation

5. **Consider using named volumes** instead of bind mounts for better performance

## 📱 Cross-Platform Notes

### Windows
- Ensure Docker Desktop has access to your drive
- Use PowerShell or Command Prompt
- Path separators in volumes are handled automatically

### Linux/macOS
- Standard Docker commands work as expected
- Consider file ownership when accessing mounted volumes
- Use `sudo` if needed for Docker commands

### WSL2 (Windows Subsystem for Linux)
- Works great with Docker Desktop
- Mount paths use Linux-style separators
- Performance is excellent for file operations