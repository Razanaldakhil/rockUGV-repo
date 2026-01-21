# 🔄 RockUGV Recovery Guide

> Emergency procedures for SD card corruption and system recovery

## 📋 Table of Contents

1. [When to Use This Guide](#when-to-use-this-guide)
2. [Backup Strategy](#backup-strategy)
3. [SD Card Reflash Procedure](#sd-card-reflash-procedure)
4. [Post-Flash Setup](#post-flash-setup)
5. [Quick Recovery Checklist](#quick-recovery-checklist)

---

## When to Use This Guide

Use this recovery procedure when:

- ❌ Jetson fails to boot
- ❌ SD card corruption detected
- ❌ System becomes unresponsive
- ❌ Docker/CUDA not working after failed update
- ❌ Need to set up a new Jetson device
- ❌ Restoring from backup

---

## Backup Strategy

### What to Backup Regularly

| Item | Location | Priority |
|------|----------|----------|
| Model weights | `~/rockUGV/models/best.pt` | 🔴 Critical |
| Docker compose | `~/rockUGV/docker-compose.yml` | 🔴 Critical |
| Application code | `~/rockUGV/app/` | 🔴 Critical |
| Docker daemon config | `/etc/docker/daemon.json` | 🟡 Important |
| Custom scripts | `~/scripts/` | 🟡 Important |
| Network config | `/etc/netplan/` | 🟢 Optional |

### Backup Commands

```bash
# Create backup directory
mkdir -p ~/backup-$(date +%Y%m%d)

# Backup project files
cp -r ~/rockUGV ~/backup-$(date +%Y%m%d)/

# Backup Docker config
sudo cp /etc/docker/daemon.json ~/backup-$(date +%Y%m%d)/

# Compress backup
tar -czvf rockugv-backup-$(date +%Y%m%d).tar.gz ~/backup-$(date +%Y%m%d)

# Transfer to external storage
# USB drive example:
sudo mount /dev/sda1 /mnt/usb
cp rockugv-backup-*.tar.gz /mnt/usb/
sudo umount /mnt/usb
```

### Automated Backup Script

```bash
#!/bin/bash
# save as ~/scripts/backup.sh

BACKUP_DIR="/home/nvidia/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/nvidia/rockUGV"

mkdir -p $BACKUP_DIR

# Backup project
tar -czvf $BACKUP_DIR/rockugv-$DATE.tar.gz \
    $PROJECT_DIR/app \
    $PROJECT_DIR/models \
    $PROJECT_DIR/docker-compose.yml \
    $PROJECT_DIR/Dockerfile

# Keep only last 5 backups
ls -t $BACKUP_DIR/rockugv-*.tar.gz | tail -n +6 | xargs -r rm

echo "Backup complete: $BACKUP_DIR/rockugv-$DATE.tar.gz"
```

---

## SD Card Reflash Procedure

### Step 1: Download JetPack Image

On your host computer (not Jetson):

1. Go to [NVIDIA JetPack Downloads](https://developer.nvidia.com/embedded/jetpack)
2. Download **JetPack 6.2** for Orin Nano Super
3. Note the file location

### Step 2: Prepare SD Card

Requirements:
- MicroSD card: 64GB+ (128GB recommended)
- Card speed: U3 or A2 rated
- SD card reader

### Step 3: Flash Using Balena Etcher

1. Download [Balena Etcher](https://www.balena.io/etcher/)

2. Run Etcher:
   - Select the JetPack image file
   - Select your SD card
   - Click "Flash!"

3. Wait for completion (10-15 minutes)

### Step 4: Alternative - Flash Using Command Line (Linux)

```bash
# Identify SD card device (CAREFUL!)
lsblk

# Unmount any mounted partitions
sudo umount /dev/sdX*

# Flash the image (replace sdX with your device)
sudo dd if=jetpack-image.img of=/dev/sdX bs=4M status=progress
sync
```

### Step 5: First Boot

1. Insert SD card into Jetson
2. Connect:
   - DisplayPort/HDMI monitor
   - USB keyboard
   - Ethernet cable (recommended)
   - Power supply
3. Power on
4. Follow on-screen setup:
   - Accept license
   - Select language/timezone
   - Create user: `nvidia` (recommended)
   - Set password
   - Configure network

---

## Post-Flash Setup

### Phase 1: System Update (5 minutes)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Reboot
sudo reboot
```

### Phase 2: Performance Configuration (2 minutes)

```bash
# Set maximum performance mode
sudo nvpmodel -m 2
sudo jetson_clocks

# Verify
sudo nvpmodel -q
```

### Phase 3: Docker Configuration (5 minutes)

```bash
# Configure Docker with NVIDIA runtime and iptables fix
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

### Phase 4: Project Setup (5 minutes)

```bash
# Create project directory
mkdir -p ~/rockUGV/app ~/rockUGV/models ~/rockUGV/videos

# Restore from backup if available
tar -xzvf /path/to/backup/rockugv-backup.tar.gz -C ~/

# Or create fresh files (see SETUP_GUIDE.md)
```

### Phase 5: Copy Files from This Repository

```bash
# If you have this repo cloned elsewhere
# Copy the essential files:

# Dockerfile
cat > ~/rockUGV/Dockerfile << 'EOF'
FROM dustynv/l4t-pytorch:r36.4.0

WORKDIR /app

RUN pip3 install --no-cache-dir \
    --index-url https://pypi.org/simple \
    --default-timeout=100 \
    --retries 5 \
    "numpy<2" \
    fastapi uvicorn python-multipart pillow ultralytics opencv-python-headless

COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# docker-compose.yml
cat > ~/rockUGV/docker-compose.yml << 'EOF'
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

### Phase 6: Restore Model and Build (10 minutes)

```bash
# Copy your model file
cp /path/to/backup/best.pt ~/rockUGV/models/

# Build Docker image
cd ~/rockUGV
sudo docker compose build

# Start system
sudo docker compose up -d

# Verify
sudo docker compose ps
curl http://localhost:8000/health
```

---

## Quick Recovery Checklist

### ⏱️ 30-Minute Recovery Procedure

- [ ] **Flash SD card** (15 min)
  - Download JetPack 6.2
  - Flash with Balena Etcher
  
- [ ] **First boot setup** (5 min)
  - Create user `nvidia`
  - Configure network
  
- [ ] **System configuration** (5 min)
  ```bash
  sudo apt update && sudo apt upgrade -y
  sudo nvpmodel -m 2
  sudo jetson_clocks
  ```

- [ ] **Docker setup** (2 min)
  ```bash
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
  ```

- [ ] **Project restore** (5 min)
  - Copy project files from backup/repo
  - Copy model file
  - Build and start Docker

- [ ] **Verify** (2 min)
  ```bash
  sudo docker compose up -d
  curl http://localhost:8000/health
  ```

---

## Critical Files Reference

### /etc/docker/daemon.json
```json
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
```

### ~/rockUGV/Dockerfile
```dockerfile
FROM dustynv/l4t-pytorch:r36.4.0

WORKDIR /app

RUN pip3 install --no-cache-dir \
    --index-url https://pypi.org/simple \
    --default-timeout=100 \
    --retries 5 \
    "numpy<2" \
    fastapi uvicorn python-multipart pillow ultralytics opencv-python-headless

COPY app/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### ~/rockUGV/docker-compose.yml
```yaml
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
```

---

## Prevention Tips

1. **Regular backups**: Run backup script weekly
2. **Use quality SD cards**: Samsung EVO Plus, SanDisk Extreme Pro
3. **Proper shutdown**: Always `sudo shutdown now` before power off
4. **Monitor health**: Check `df -h` for disk space regularly
5. **Keep this guide accessible**: Store on cloud/USB drive

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Time to recover**: ~30 minutes with backup
