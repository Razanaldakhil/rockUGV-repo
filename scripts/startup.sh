#!/bin/bash
#
# RockUGV Startup Script
# Automatically starts the border surveillance system on boot
#
# Author: Border Surveillance Team
# Date: January 2026
#

set -e

# Configuration
PROJECT_DIR="/home/nvidia/rockUGV"
LOG_FILE="/home/nvidia/rockUGV/logs/startup.log"
CONTAINER_NAME="rockugv"
IMAGE_NAME="detection-api"

# Create log directory if not exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "RockUGV Startup Script Initiated"
log "=========================================="

# Navigate to project directory
cd "$PROJECT_DIR" || {
    log "ERROR: Project directory not found: $PROJECT_DIR"
    exit 1
}
log "Working directory: $(pwd)"

# Wait for Docker to be fully ready
log "Waiting for Docker service..."
for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
        log "Docker is ready"
        break
    fi
    log "Waiting for Docker... ($i/30)"
    sleep 2
done

# Check if Docker is available
if ! docker info >/dev/null 2>&1; then
    log "ERROR: Docker is not available"
    exit 1
fi

# Set maximum performance mode
log "Setting performance mode..."
sudo nvpmodel -m 2 2>/dev/null || log "WARNING: Could not set nvpmodel"
sudo jetson_clocks 2>/dev/null || log "WARNING: Could not set jetson_clocks"

# Check for camera
log "Checking camera..."
if [ -e /dev/video0 ]; then
    log "Camera detected at /dev/video0"
else
    log "WARNING: Camera not detected at /dev/video0"
fi

# Check for model file
if [ -f "$PROJECT_DIR/models/best.pt" ]; then
    log "Model file found: models/best.pt"
else
    log "WARNING: Model file not found, will use default yolov8n.pt"
fi

# Stop any existing container
log "Stopping existing container (if any)..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Start the container
log "Starting RockUGV container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    --runtime nvidia \
    --network host \
    --privileged \
    -v "$PROJECT_DIR/models:/app/models" \
    -v "$PROJECT_DIR/videos:/app/videos" \
    -v /dev:/dev \
    --device /dev/video0:/dev/video0 \
    "$IMAGE_NAME"

# Check if container started successfully
sleep 5
if docker ps | grep -q "$CONTAINER_NAME"; then
    log "Container started successfully"
    
    # Wait for API to be ready
    log "Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            log "API is ready and responding"
            break
        fi
        log "Waiting for API... ($i/30)"
        sleep 2
    done
    
    # Final health check
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        log "=========================================="
        log "RockUGV System Started Successfully!"
        log "Access at: http://$(hostname -I | awk '{print $1}'):8000"
        log "=========================================="
        exit 0
    else
        log "WARNING: API not responding, but container is running"
        exit 0
    fi
else
    log "ERROR: Container failed to start"
    docker logs "$CONTAINER_NAME" 2>&1 | tail -20 >> "$LOG_FILE"
    exit 1
fi
