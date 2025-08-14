# Use Python 3.11 slim image for minimal footprint
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies for OpenCV and image processing
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Create entrypoint script directly in Dockerfile with permission fixing
RUN echo '#!/bin/bash\n\
set -e\n\
echo "FastFoto Date Scanner - Container Starting"\n\
echo "=========================================="\n\
\n\
# Fix permissions on mounted volumes\n\
echo "Fixing volume permissions..."\n\
chown -R scanner:scanner /app/data || echo "Warning: Could not change ownership of /app/data"\n\
chmod -R 755 /app/data || echo "Warning: Could not change permissions of /app/data"\n\
\n\
# Switch to scanner user\n\
echo "Switching to scanner user..."\n\
export PYTHONPATH="/app/src:$PYTHONPATH"\n\
\n\
# Initialize database as scanner user\n\
echo "Initializing database..."\n\
su -s /bin/bash scanner -c "python src/init_database.py"\n\
if [ $? -ne 0 ]; then\n\
    echo "Database initialization failed, exiting..."\n\
    exit 1\n\
fi\n\
\n\
echo "Database initialization completed successfully"\n\
echo "Starting Flask application..."\n\
exec su -s /bin/bash scanner -c "python src/app.py"' > entrypoint.sh && chmod +x entrypoint.sh

# Create data directories with proper permissions
RUN mkdir -p /app/data/photos/unprocessed \
             /app/data/photos/processed \
             /app/data/db \
             /app/data/thumbs && \
    chmod -R 755 /app/data

# Create non-root user for security
RUN groupadd -r scanner && useradd -r -g scanner scanner && \
    chown -R scanner:scanner /app

# Note: Don't switch to non-root user yet - need to fix permissions at runtime

# Set Python path to include src directory
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Expose Flask port
EXPOSE 5000

# Health check using the dedicated endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command - use entrypoint script
CMD ["./entrypoint.sh"]