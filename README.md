# 🪨 RockUGV - AI Border Surveillance System

> Camouflaged Rock-Based AI Border Surveillance with Real-Time Detection and Tracking

![Platform](https://img.shields.io/badge/Platform-Jetson%20Orin%20Nano-green)
![Model](https://img.shields.io/badge/Model-YOLO-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-Private-red)

## 📋 Overview

This repository contains the deployment files for the RockUGV border surveillance system. The system runs YOLO-based object detection on NVIDIA Jetson Orin Nano Super, deployed inside camouflaged rock housings for covert perimeter monitoring.

### Key Features

- **Real-time Detection**: YOLO model optimized for edge deployment
- **USB Camera Support**: Works with standard USB cameras
- **Docker Containerized**: Easy deployment and reproducibility
- **GPU Accelerated**: TensorRT optimization for Jetson platform
- **FastAPI Interface**: REST API for video streaming and inference

## 🗂️ Project Structure

```
rockUGV/
├── Dockerfile              # Docker build configuration
├── docker-compose.yml      # Container orchestration
├── app/
│   ├── main.py            # FastAPI application
│   ├── camera.py          # USB camera handler
│   └── requirements.txt   # Python dependencies (inside container)
├── models/
│   └── best.pt            # Trained YOLO model weights
├── videos/                 # Optional: test videos
└── docs/
    ├── SETUP_GUIDE.md     # Detailed setup instructions
    ├── TROUBLESHOOTING.md # Common errors and solutions
    └── RECOVERY.md        # Emergency recovery procedures
```

## ⚙️ Hardware Requirements

| Component | Specification |
|-----------|---------------|
| **Compute** | NVIDIA Jetson Orin Nano Super (8GB) |
| **Storage** | NVMe SSD (recommended) or 64GB+ SD Card |
| **Camera** | USB Camera (e.g., Logitech C920) |
| **Power** | DC barrel jack power supply |
| **OS** | JetPack 6.2+ |

## 🚀 Quick Start

### Prerequisites

1. Jetson Orin Nano Super with JetPack 6.2+ installed
2. Docker and NVIDIA Container Runtime installed
3. USB camera connected to `/dev/video0`

### Deploy in 3 Steps

```bash
# 1. Clone this repository
git clone <repository-url> rockUGV
cd rockUGV

# 2. Place your model weights
cp /path/to/best.pt models/

# 3. Build and run
sudo docker compose up -d
```

### Access the System

- **Video Feed**: `http://<jetson-ip>:8000/video_feed`
- **Health Check**: `http://<jetson-ip>:8000/health`
- **API Docs**: `http://<jetson-ip>:8000/docs`

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | Complete setup from fresh Jetson |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors and solutions |
| [RECOVERY.md](docs/RECOVERY.md) | SD card reflash and recovery |

## 🔧 Key Commands

```bash
# === DOCKER COMPOSE ===
# View logs
sudo docker compose logs -f

# Stop the system
sudo docker compose down

# Restart after changes
sudo docker compose restart

# Rebuild after Dockerfile changes
sudo docker compose build --no-cache
sudo docker compose up -d

# === DOCKER RUN (Alternative) ===
# Run interactively (for testing)
sudo docker run -it --rm \
  --runtime nvidia \
  --network host \
  --privileged \
  -v $(pwd)/models:/app/models \
  -v /dev:/dev \
  --device /dev/video0:/dev/video0 \
  detection-api

# Run in background
sudo docker run -d \
  --name rockugv \
  --restart unless-stopped \
  --runtime nvidia \
  --network host \
  --privileged \
  -v $(pwd)/models:/app/models \
  -v /dev:/dev \
  --device /dev/video0:/dev/video0 \
  detection-api

# === UTILITIES ===
# Check camera
ls -la /dev/video*

# Monitor GPU
tegrastats

# Check container status
sudo docker ps -a
```

## ⚠️ Important Notes

1. **Model File**: The `best.pt` model file is NOT included in this repository. You must provide your own trained model.

2. **Docker Runtime**: Ensure NVIDIA runtime is configured as default in `/etc/docker/daemon.json`

3. **Camera Permissions**: Container runs with `privileged: true` for camera access

4. **Network**: Default port is 8000. Modify `docker-compose.yml` if needed.

## 📞 Support

For issues:
1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review container logs: `sudo docker compose logs`
3. Contact the development team

---

**Last Updated**: January 2026  
**Version**: 1.0.0
