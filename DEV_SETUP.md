# Development Setup Guide

## Recommended: Pure Docker Development (No Local Dependencies)

The cleanest way to develop - uses Docker for everything, no Python setup needed on your machine.

### Quick Start

**Windows:**
```bash
# Just double-click this file or run from command line
dev.bat
```

**Linux/Mac:**
```bash
# Make executable and run
chmod +x dev.sh
./dev.sh
```

**Manual Docker command:**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### What This Does:
- ✅ **No local Python dependencies needed**
- ✅ Mounts your source code for live updates (no rebuild needed)  
- ✅ Includes all dependencies automatically in container
- ✅ Runs with Flask debug mode enabled
- ✅ Disables background scheduled tasks
- ✅ Maps to http://localhost:5000
- ✅ Creates necessary data directories

### Making Code Changes:
Just edit files in your IDE - changes are reflected immediately in the running container!

## Alternative: Local Python Development

Only use this if you prefer to run Python directly on your machine:

```bash
# Install all dependencies locally
pip install -r requirements.txt

# Run the app
python src/app.py
```

Or use the local development scripts:
- `run_dev.bat` (Windows) 
- `run_dev.py` (Cross-platform)

## Development Features

### Live Code Updates

With the development container, any changes you make to:
- `src/` files (Python code)
- `static/` files (CSS, JS)  
- `templates/` files (HTML)
- `requirements.txt`

Will automatically reload the application without rebuilding the container.

### Environment Variables

Create a `.env` file in the root directory:

```env
# Copy from .env.example and customize
FLASK_DEBUG=true
PHOTOS_PER_PAGE=100
SIMILARITY_EPS=0.3
SCAN_INTERVAL_HOURS=0  # Disable scheduled tasks in dev
```

## Troubleshooting

### Missing Dependencies
If you get import errors, the `requirements.txt` file now includes all necessary dependencies:
- Flask==2.3.3
- APScheduler==3.10.4
- Pillow==10.0.1
- And more...

### Port Conflicts
If port 5000 is in use, modify the port in:
- `.env` file: `FLASK_PORT=5001`
- `docker-compose.dev.yml`: Change the ports mapping

### File Permissions (Linux/Mac)
If you have permission issues with mounted volumes:
```bash
sudo chown -R $USER:$USER ./data
```

## Production Deployment

For production, use the standard docker-compose.yml:
```bash
docker-compose up -d --build
```

This uses the optimized production Dockerfile without development features.