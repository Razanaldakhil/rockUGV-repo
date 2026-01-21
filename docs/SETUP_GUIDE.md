# 📖 RockUGV Complete Setup Guide

> Step-by-step instructions for deploying RockUGV on Jetson Orin Nano Super

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [JetPack Installation](#2-jetpack-installation)
3. [System Configuration](#3-system-configuration)
4. [Docker Setup](#4-docker-setup)
5. [Project Deployment](#5-project-deployment)
6. [Camera Setup](#6-camera-setup)
7. [Running the System](#7-running-the-system)
8. [Verification](#8-verification)

---

## 1. Prerequisites

### Hardware Checklist

- [ ] NVIDIA Jetson Orin Nano Super Developer Kit (8GB)
- [ ] NVMe SSD (recommended) or MicroSD Card (64GB+, U3/A2 rated)
- [ ] USB Camera (tested with Logitech C920, Tapo cameras)
- [ ] Power supply (DC barrel jack, 5V/4A minimum)
- [ ] Ethernet cable or WiFi connection
- [ ] DisplayPort cable (for initial setup)
- [ ] Keyboard and mouse (for initial setup)

### Software Requirements

- JetPack 6.2 (includes CUDA 12.6, TensorRT 10.3)
- Docker with NVIDIA Container Runtime
- Trained YOLO model (`best.pt`)

---

## 2. JetPack Installation

### Option A: Fresh Installation (SD Card/NVMe)

1. Download JetPack 6.2 from [NVIDIA Developer](https://developer.nvidia.com/embedded/jetpack-sdk-62)

2. Flash using Balena Etcher:
   ```bash
   # On your host computer
   # Download Balena Etcher from https://www.balena.io/etcher/
   # Select the JetPack image and your SD card/NVMe
   # Click Flash
   ```

3. First boot setup:
   - Accept license agreement
   - Set username: `nvidia` (recommended)
   - Set a secure password
   - Configure network

### Option B: Upgrade Existing JetPack 6.x

```bash
# Edit apt source
sudo nano /etc/apt/sources.list.d/nvidia-l4t-apt-source.list
# Change version to r36.4 in both lines

# Upgrade
sudo apt update
sudo apt dist-upgrade
sudo apt install --fix-broken -o Dpkg::Options::="--force-overwrite"

# Reboot
sudo reboot
```

### Verify JetPack Version

```bash
cat /etc/nv_tegra_release
# Should show: R36 (release), REVISION: 4.0
```

---

## 3. System Configuration

### 3.1 Enable Maximum Performance Mode

```bash
# Check current power mode
sudo nvpmodel -q

# Set to MAXN SUPER mode (maximum performance)
sudo nvpmodel -m 2

# Lock clocks for consistent performance
sudo jetson_clocks

# Verify settings
sudo nvpmodel -q
```

### 3.2 Install System Utilities

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    curl \
    git \
    htop \
    nano \
    v4l-utils \
    python3-pip

# Install jetson-stats (for monitoring)
sudo pip3 install jetson-stats --break-system-packages
```

### 3.3 Verify GPU and CUDA

```bash
# Check GPU
nvidia-smi

# Check CUDA version
nvcc --version

# Test with Python
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}')"
```

Expected output:
```
PyTorch: 2.5.0a0+872d972e41.nv24.08
CUDA: True
```

---

## 4. Docker Setup

### 4.1 Verify Docker Installation

```bash
# Check Docker
docker --version
# Expected: Docker version 24.x or higher

# Check NVIDIA runtime
docker info | grep -i runtime
# Should show: nvidia
```

### 4.2 Configure Docker Daemon (CRITICAL)

This fixes the common iptables error on Jetson.

```bash
# Create/edit Docker daemon config
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'EOF'
{
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "default-runtime": "nvidia",
    "iptables": false
}
EOF

# Restart Docker
sudo systemctl restart docker

# Verify
docker info | grep -i "default runtime"
```

### 4.3 Add User to Docker Group (Optional)

```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Test without sudo
docker ps
```

### 4.4 Fix iptables Issues (If Needed)

If you encounter iptables errors during docker build:

```bash
# Try legacy iptables mode
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# Restart Docker
sudo systemctl restart docker
```

---

## 5. Project Deployment

### 5.1 Clone/Create Project Directory

```bash
# Create project directory
mkdir -p ~/rockUGV
cd ~/rockUGV

# Create subdirectories
mkdir -p app models videos
```

### 5.2 Create Dockerfile

```bash
cat > Dockerfile << 'EOF'
FROM dustynv/l4t-pytorch:r36.4.0

WORKDIR /app

# Install packages with NumPy version pinned to avoid conflicts
RUN pip3 install --no-cache-dir \
    --index-url https://pypi.org/simple \
    --default-timeout=100 \
    --retries 5 \
    "numpy<2" \
    fastapi uvicorn python-multipart pillow ultralytics opencv-python-headless

# Copy application
COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

### 5.3 Create docker-compose.yml

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  detection-api:
    build: .
    ports:
      - "8000:8000"
    runtime: nvidia
    privileged: true   
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ./models:/app/models
      - ./videos:/app/videos
      - /dev:/dev   
    devices:
      - /dev/video0:/dev/video0  
EOF
```

### 5.4 Create camera.py

```bash
cat > app/camera.py << 'EOF'
import cv2
import threading
import time

class USBCamera:
    def __init__(self, camera_id=0, width=640, height=480, fps=30):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        
    def start(self):
        """Start the camera stream"""
        if self.running:
            return True
            
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print(f"Failed to open camera {self.camera_id}")
            return False
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        self.running = True
        
        # Start capture thread
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        
        print(f"Camera {self.camera_id} started: {self.width}x{self.height} @ {self.fps}fps")
        return True
    
    def _update_frame(self):
        """Continuously read frames from camera"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.01)
    
    def read(self):
        """Get the latest frame"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def stop(self):
        """Stop the camera stream"""
        self.running = False
        if self.thread:
            self.thread.join()
        if self.cap:
            self.cap.release()
        print(f"Camera {self.camera_id} stopped")
    
    def is_running(self):
        return self.running
EOF
```

### 5.5 Create main.py (FastAPI Application)

```bash
cat > app/main.py << 'EOF'
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse, HTMLResponse
import cv2
import numpy as np
from ultralytics import YOLO
from camera import USBCamera
import time
import threading

app = FastAPI(title="RockUGV Detection API")

# Global variables
model = None
camera = None

@app.on_event("startup")
async def startup():
    global model, camera
    
    # Load YOLO model
    print("Loading YOLO model...")
    try:
        model = YOLO("/app/models/best.pt")
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = YOLO("yolov8n.pt")  # Fallback to pretrained
        print("Using fallback model: yolov8n.pt")
    
    # Initialize camera
    camera = USBCamera(camera_id=0, width=640, height=480, fps=30)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RockUGV Detection</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: white; }
            h1 { color: #4CAF50; }
            .stream { border: 2px solid #4CAF50; border-radius: 8px; }
            a { color: #4CAF50; }
        </style>
    </head>
    <body>
        <h1>🪨 RockUGV Border Surveillance</h1>
        <p>System Status: <span style="color: #4CAF50;">Online</span></p>
        <h2>Video Feed</h2>
        <img class="stream" src="/video_feed" width="640" height="480">
        <h2>API Endpoints</h2>
        <ul>
            <li><a href="/health">/health</a> - System health check</li>
            <li><a href="/video_feed">/video_feed</a> - Live detection stream</li>
            <li><a href="/docs">/docs</a> - API documentation</li>
        </ul>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "camera_active": camera.is_running() if camera else False
    }

def generate_frames():
    global model, camera
    
    if not camera.is_running():
        camera.start()
    
    while True:
        frame = camera.read()
        if frame is None:
            time.sleep(0.1)
            continue
        
        # Run detection
        if model:
            results = model(frame, verbose=False)
            frame = results[0].plot()
        
        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.on_event("shutdown")
async def shutdown():
    global camera
    if camera:
        camera.stop()
EOF
```

### 5.6 Copy Your Model

```bash
# Copy your trained model to the models directory
cp /path/to/your/best.pt models/
```

---

## 6. Camera Setup

### 6.1 Check Camera Connection

```bash
# List video devices
ls -la /dev/video*

# Get camera info
v4l2-ctl --list-devices

# Test camera capture
v4l2-ctl -d /dev/video0 --list-formats-ext
```

### 6.2 Test Camera Outside Docker

```bash
# Quick test with Python
python3 << 'EOF'
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print(f"Camera working: {ret}")
print(f"Frame shape: {frame.shape if ret else 'N/A'}")
cap.release()
EOF
```

---

## 7. Running the System

### 7.1 Build Docker Image

```bash
cd ~/rockUGV

# Build (first time takes 5-10 minutes)
sudo docker compose build

# If build fails, try with network host
sudo docker build --network=host -t rockugv:latest .
```

### 7.2 Start the System

```bash
# Start in detached mode
sudo docker compose up -d

# View logs
sudo docker compose logs -f
```

### 7.3 Stop the System

```bash
sudo docker compose down
```

---

## 8. Verification

### 8.1 Check Container Status

```bash
sudo docker compose ps
# Should show: detection-api running
```

### 8.2 Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# From another computer on same network
curl http://<jetson-ip>:8000/health
```

### 8.3 View Video Feed

Open in browser:
```
http://<jetson-ip>:8000/
```

### 8.4 Monitor Performance

```bash
# GPU usage
tegrastats

# Or use jtop (more detailed)
jtop
```

---

## ✅ Setup Complete Checklist

- [ ] JetPack 6.2 installed
- [ ] Power mode set to MAXN SUPER
- [ ] Docker configured with NVIDIA runtime
- [ ] iptables issue fixed (if applicable)
- [ ] Project files created
- [ ] Model file in place (`models/best.pt`)
- [ ] Camera detected at `/dev/video0`
- [ ] Docker image built successfully
- [ ] Container running
- [ ] Video feed accessible
- [ ] Detections visible in stream

---

## 🔗 Next Steps

1. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
2. Create backup of working SD card
3. Document any environment-specific configurations

---

**Document Version**: 1.0  
**Last Updated**: January 2026
