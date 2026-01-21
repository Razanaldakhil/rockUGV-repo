# 🔧 RockUGV Troubleshooting Guide

> Common errors and their solutions for the RockUGV border surveillance system

## 📋 Table of Contents

1. [Docker Build Errors](#1-docker-build-errors)
2. [Docker Runtime Errors](#2-docker-runtime-errors)
3. [Camera Issues](#3-camera-issues)
4. [Model Loading Issues](#4-model-loading-issues)
5. [Network Issues](#5-network-issues)
6. [Performance Issues](#6-performance-issues)
7. [Python/Package Errors](#7-pythonpackage-errors)

---

## 1. Docker Build Errors

### Error 1.1: iptables Table Does Not Exist

**Symptom:**
```
failed to set up container networking: failed to create endpoint on network bridge: 
Unable to enable DIRECT ACCESS FILTERING - DROP rule: 
(iptables failed: iptables --wait -t raw -A PREROUTING -d 172.17.0.2 ! -i docker0 -j DROP: 
iptables v1.8.7 (legacy): can't initialize iptables table `raw': Table does not exist
```

**Cause:** Jetson kernel missing `iptable_raw` module

**Solution:**

```bash
# Option 1: Configure Docker to disable iptables (Recommended)
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
sudo systemctl restart docker

# Then rebuild
sudo docker compose build
```

```bash
# Option 2: Use legacy iptables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
sudo systemctl restart docker
```

```bash
# Option 3: Build with host network
sudo docker build --network=host -t rockugv:latest .
```

---

### Error 1.2: Manifest Not Found

**Symptom:**
```
manifest for nvcr.io/nvidia/l4t-pytorch:r36.3.0-pth2.1-py3 not found
```

**Cause:** Incorrect base image tag

**Solution:**
Use the correct base image. Check available images:

```bash
# Recommended base images for JetPack 6.2:
# dustynv/l4t-pytorch:r36.4.0
# nvcr.io/nvidia/l4t-jetpack:r36.4.0
```

Update Dockerfile:
```dockerfile
FROM dustynv/l4t-pytorch:r36.4.0
```

---

### Error 1.3: Permission Denied on Docker Socket

**Symptom:**
```
dial unix /var/run/docker.sock: connect: permission denied
```

**Solution:**
```bash
# Run with sudo
sudo docker compose build

# Or add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

### Error 1.4: Build Context Too Large

**Symptom:**
```
Sending build context to Docker daemon  566.4MB
```

**Cause:** Large files in build directory

**Solution:**
Create `.dockerignore`:

```bash
cat > .dockerignore << 'EOF'
*.mp4
*.avi
*.mov
videos/*
*.pt
*.onnx
*.engine
__pycache__
.git
EOF
```

---

## 2. Docker Runtime Errors

### Error 2.1: NVIDIA Runtime Not Found

**Symptom:**
```
docker: Error response from daemon: Unknown runtime specified nvidia
```

**Solution:**
```bash
# Install nvidia-container-toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker info | grep -i runtime
```

---

### Error 2.2: ONNX Runtime Not Found

**Symptom:**
```
Error: No module named 'onnxruntime'
ERROR: Could not find a version that satisfies the requirement onnxruntime-gpu
```

**Cause:** ONNX runtime not available for Jetson architecture

**Solution:**
Use PyTorch/TensorRT instead of ONNX. In your code, load `.pt` file directly:

```python
# Use .pt file, not .onnx
model = YOLO("/app/models/best.pt")
```

Or convert to TensorRT engine inside container:
```bash
# Inside container
python3 << 'PYEOF'
from ultralytics import YOLO
model = YOLO('/app/models/best.pt')
model.export(format='engine', imgsz=640, half=True, device=0)
PYEOF
```

---

### Error 2.3: NumPy Version Conflict

**Symptom:**
```
AttributeError: module 'numpy' has no attribute 'object'
# or
numpy.core.multiarray failed to import
```

**Cause:** NumPy 2.0 incompatibility with older packages

**Solution:**
Pin NumPy version < 2 in Dockerfile:

```dockerfile
RUN pip3 install --no-cache-dir "numpy<2" ...
```

Or in requirements.txt:
```
numpy>=1.24.0,<2.0
```

---

### Error 2.4: Container Exits Immediately

**Symptom:**
Container starts and immediately stops.

**Diagnosis:**
```bash
# Check logs
sudo docker compose logs

# Check exit code
sudo docker ps -a
```

**Common Causes & Solutions:**

1. **Model file not found:**
   ```bash
   # Verify model exists
   ls -la models/best.pt
   ```

2. **Port already in use:**
   ```bash
   # Find process using port 8000
   sudo lsof -i :8000
   # Kill it or use different port
   ```

3. **Camera not available:**
   ```bash
   # Check camera
   ls -la /dev/video*
   ```

---

## 3. Camera Issues

### Error 3.1: Camera Not Detected

**Symptom:**
```
Failed to open camera 0
```

**Diagnosis:**
```bash
# Check video devices
ls -la /dev/video*

# Get device info
v4l2-ctl --list-devices
```

**Solutions:**

1. **USB Camera not connected:**
   ```bash
   # Reconnect camera and check
   dmesg | tail -20
   ```

2. **Wrong camera ID:**
   Update camera_id in code:
   ```python
   camera = USBCamera(camera_id=1)  # Try different IDs: 0, 1, 2
   ```

3. **Permissions issue:**
   ```bash
   # Add user to video group
   sudo usermod -aG video $USER
   ```

4. **Device not passed to container:**
   Update docker-compose.yml:
   ```yaml
   devices:
     - /dev/video0:/dev/video0
     - /dev/video1:/dev/video1
   privileged: true
   volumes:
     - /dev:/dev
   ```

---

### Error 3.2: Camera Works Outside Container but Not Inside

**Solution:**
Ensure privileged mode and device mapping:

```yaml
# docker-compose.yml
services:
  detection-api:
    privileged: true
    devices:
      - /dev/video0:/dev/video0
    volumes:
      - /dev:/dev
```

---

### Error 3.3: Low FPS or Laggy Video

**Causes & Solutions:**

1. **Resolution too high:**
   ```python
   camera = USBCamera(width=640, height=480, fps=30)
   ```

2. **USB 2.0 vs 3.0:**
   ```bash
   # Check USB port speed
   lsusb -t
   # Use USB 3.0 port if available
   ```

3. **CPU bottleneck:**
   ```bash
   # Enable max performance
   sudo nvpmodel -m 2
   sudo jetson_clocks
   ```

---

## 4. Model Loading Issues

### Error 4.1: Model File Not Found

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/app/models/best.pt'
```

**Solution:**
```bash
# Verify model exists on host
ls -la models/best.pt

# Verify volume mount in docker-compose.yml
volumes:
  - ./models:/app/models

# Check inside container
sudo docker compose exec detection-api ls -la /app/models/
```

---

### Error 4.2: Invalid Model Format

**Symptom:**
```
RuntimeError: Invalid model file
```

**Solution:**
```bash
# Verify file is valid PyTorch model
python3 << 'EOF'
from ultralytics import YOLO
model = YOLO("models/best.pt")
print("Model loaded successfully!")
print(f"Classes: {model.names}")
EOF
```

---

### Error 4.3: CUDA Out of Memory

**Symptom:**
```
CUDA out of memory
```

**Solutions:**

1. **Reduce batch size:**
   ```python
   results = model(frame, batch=1)
   ```

2. **Use smaller input size:**
   ```python
   results = model(frame, imgsz=320)
   ```

3. **Close other GPU processes:**
   ```bash
   # Check GPU usage
   tegrastats
   # Or
   nvidia-smi
   ```

---

## 5. Network Issues

### Error 5.1: Cannot Access from Other Devices

**Symptom:**
Can access `localhost:8000` but not `<jetson-ip>:8000`

**Solutions:**

1. **Firewall blocking:**
   ```bash
   # Allow port 8000
   sudo ufw allow 8000
   ```

2. **Wrong bind address:**
   Ensure app binds to `0.0.0.0`:
   ```bash
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **Check IP address:**
   ```bash
   ip addr show
   hostname -I
   ```

---

### Error 5.2: Port Already in Use

**Symptom:**
```
Address already in use: bind: 0.0.0.0:8000
```

**Solution:**
```bash
# Find process using port
sudo lsof -i :8000

# Kill it
sudo kill -9 <PID>

# Or use different port in docker-compose.yml
ports:
  - "8001:8000"
```

---

## 6. Performance Issues

### Issue 6.1: Low FPS (< 10 FPS)

**Diagnosis:**
```bash
# Check power mode
sudo nvpmodel -q

# Check clocks
sudo jetson_clocks --show
```

**Solutions:**

1. **Enable maximum performance:**
   ```bash
   sudo nvpmodel -m 2  # MAXN SUPER
   sudo jetson_clocks
   ```

2. **Use TensorRT:**
   ```python
   # Export to TensorRT engine
   model.export(format='engine', half=True)
   # Then load .engine file
   model = YOLO("best.engine")
   ```

3. **Reduce input resolution:**
   ```python
   results = model(frame, imgsz=320)
   ```

---

### Issue 6.2: High Memory Usage

**Diagnosis:**
```bash
# Check memory
free -h
tegrastats
```

**Solutions:**

1. **Use FP16:**
   ```python
   model = YOLO("best.pt")
   model.export(format='engine', half=True)
   ```

2. **Reduce image size:**
   ```python
   camera = USBCamera(width=416, height=416)
   ```

---

## 7. Python/Package Errors

### Error 7.1: scipy Version Not Found

**Symptom:**
```
ERROR: Could not find a version that satisfies the requirement scipy>=1.11.0
```

**Cause:** Python 3.8 doesn't support scipy >= 1.11

**Solution:**
Use compatible version:
```
scipy>=1.10.0,<1.11.0
```

---

### Error 7.2: OpenCV Import Error

**Symptom:**
```
ImportError: libGL.so.1: cannot open shared object file
```

**Solution:**
```bash
# Install dependencies
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0

# Or use headless version
pip install opencv-python-headless
```

---

### Error 7.3: pip externally-managed-environment

**Symptom:**
```
error: externally-managed-environment
```

**Solution:**
```bash
# Use --break-system-packages flag
pip3 install package_name --break-system-packages

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install package_name
```

---

## 🆘 Emergency Commands

```bash
# Stop all containers
sudo docker compose down

# Remove all containers
sudo docker rm -f $(sudo docker ps -aq)

# Remove all images
sudo docker rmi -f $(sudo docker images -q)

# Full Docker cleanup
sudo docker system prune -a --volumes

# Restart Docker service
sudo systemctl restart docker

# Check system resources
tegrastats
htop
df -h

# Check logs
sudo docker compose logs -f --tail=100
journalctl -u docker -f
dmesg | tail -50
```

---

## 📞 Still Stuck?

1. **Collect diagnostic info:**
   ```bash
   # Create diagnostic report
   cat /etc/nv_tegra_release
   docker --version
   docker compose version
   nvidia-smi
   df -h
   free -h
   ls -la /dev/video*
   sudo docker compose logs > logs.txt
   ```

2. **Check the container:**
   ```bash
   # Get shell inside container
   sudo docker compose exec detection-api bash
   
   # Check files
   ls -la /app/
   ls -la /app/models/
   python3 -c "from ultralytics import YOLO; print('OK')"
   ```

3. **Review this guide** for similar errors

4. **Contact support** with diagnostic info

---

**Document Version**: 1.0  
**Last Updated**: January 2026
