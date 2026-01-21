#!/bin/bash
#
# RockUGV Shutdown Script
# Gracefully stops the border surveillance system
#
# Author: Border Surveillance Team
# Date: January 2026
#

set -e

# Configuration
CONTAINER_NAME="rockugv"
LOG_FILE="/home/nvidia/rockUGV/logs/startup.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "RockUGV Shutdown Script Initiated"
log "=========================================="

# Stop the container gracefully
log "Stopping RockUGV container..."
if docker ps | grep -q "$CONTAINER_NAME"; then
    docker stop "$CONTAINER_NAME" --time 30
    log "Container stopped"
else
    log "Container was not running"
fi

# Remove the container
log "Removing container..."
docker rm "$CONTAINER_NAME" 2>/dev/null || true

log "=========================================="
log "RockUGV System Stopped"
log "=========================================="
