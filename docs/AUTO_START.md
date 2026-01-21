# 🚀 RockUGV Auto-Start Configuration

> Configure the system to automatically start when Jetson powers on

## 📋 Overview

This guide explains how to set up automatic startup of the RockUGV border surveillance system using systemd. Once configured, the system will:

- Start automatically when Jetson boots
- Set maximum performance mode (nvpmodel)
- Start the Docker container with camera and AI model
- Restart automatically if it crashes
- Log all startup/shutdown events

## 📁 Files Included

| File | Purpose |
|------|---------|
| `rockugv.service` | Systemd service unit file |
| `scripts/startup.sh` | Main startup script |
| `scripts/shutdown.sh` | Graceful shutdown script |
| `scripts/install-service.sh` | One-click installation |

---

## 🔧 Quick Installation

### One-Command Setup

```bash
cd ~/rockUGV
sudo ./scripts/install-service.sh
```

This will:
1. Create logs directory
2. Make scripts executable
3. Install the systemd service
4. Enable auto-start on boot

---

## 📝 Manual Installation

If you prefer to install manually:

### Step 1: Make Scripts Executable

```bash
chmod +x ~/rockUGV/scripts/startup.sh
chmod +x ~/rockUGV/scripts/shutdown.sh
chmod +x ~/rockUGV/scripts/install-service.sh
```

### Step 2: Copy Service File

```bash
sudo cp ~/rockUGV/rockugv.service /etc/systemd/system/
```

### Step 3: Reload Systemd

```bash
sudo systemctl daemon-reload
```

### Step 4: Enable the Service

```bash
sudo systemctl enable rockugv.service
```

### Step 5: Start the Service

```bash
sudo systemctl start rockugv
```

---

## 🎮 Service Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl start rockugv` | Start the service |
| `sudo systemctl stop rockugv` | Stop the service |
| `sudo systemctl restart rockugv` | Restart the service |
| `sudo systemctl status rockugv` | Check service status |
| `sudo systemctl enable rockugv` | Enable auto-start |
| `sudo systemctl disable rockugv` | Disable auto-start |

### View Logs

```bash
# Systemd journal logs
sudo journalctl -u rockugv -f

# Application startup log
tail -f ~/rockUGV/logs/startup.log

# Docker container logs
sudo docker logs -f rockugv
```

---

## ⚙️ How It Works

### Boot Sequence

```
1. Jetson Powers On
        ↓
2. System boots, Docker service starts
        ↓
3. rockugv.service triggered (after docker.service)
        ↓
4. startup.sh executes:
   - Waits for Docker to be ready
   - Sets nvpmodel to MAXN SUPER
   - Sets jetson_clocks for max performance
   - Checks camera availability
   - Stops any existing container
   - Starts new container
   - Waits for API health check
        ↓
5. System Ready! (accessible at http://<ip>:8000)
```

### Startup Script Flow

```bash
startup.sh
├── Wait for Docker (up to 60 seconds)
├── Set performance mode (nvpmodel -m 2)
├── Lock GPU clocks (jetson_clocks)
├── Check camera (/dev/video0)
├── Check model file (models/best.pt)
├── Stop existing container (if any)
├── Start new container
└── Wait for API health check
```

---

## 🔍 Troubleshooting

### Service Won't Start

```bash
# Check status and errors
sudo systemctl status rockugv

# Check detailed logs
sudo journalctl -u rockugv -n 50 --no-pager

# Check startup log
cat ~/rockUGV/logs/startup.log
```

### Common Issues

**1. Docker not ready**
```
Solution: The script waits up to 60 seconds for Docker.
If still failing, increase sleep time in startup.sh
```

**2. Camera not detected**
```bash
# Check camera
ls -la /dev/video*

# The system will still start, but with warning
```

**3. Permission denied**
```bash
# Ensure user is in docker group
sudo usermod -aG docker nvidia
newgrp docker
```

**4. Container already exists**
```bash
# Remove manually
sudo docker rm -f rockugv
sudo systemctl restart rockugv
```

### Reset Service

```bash
# Stop and disable
sudo systemctl stop rockugv
sudo systemctl disable rockugv

# Remove service file
sudo rm /etc/systemd/system/rockugv.service
sudo systemctl daemon-reload

# Reinstall
sudo ./scripts/install-service.sh
```

---

## 📊 Monitoring

### Check if Running

```bash
# Quick check
sudo systemctl is-active rockugv

# Detailed status
sudo systemctl status rockugv

# Container status
sudo docker ps | grep rockugv
```

### Health Check

```bash
# API health
curl http://localhost:8000/health

# From another device
curl http://<jetson-ip>:8000/health
```

### Performance Monitoring

```bash
# GPU usage
tegrastats

# Or use jtop
jtop
```

---

## 🔄 Updating the System

After making changes to the code:

```bash
# Rebuild Docker image
cd ~/rockUGV
sudo docker compose build

# Restart service
sudo systemctl restart rockugv

# Check logs
sudo journalctl -u rockugv -f
```

---

## ⏱️ Boot Time

Expected boot sequence timing:

| Phase | Time |
|-------|------|
| Jetson boot | ~30 sec |
| Docker ready | ~10 sec |
| Container start | ~5 sec |
| Model loading | ~10 sec |
| API ready | ~5 sec |
| **Total** | **~60 sec** |

---

## 📝 Service File Reference

```ini
[Unit]
Description=RockUGV Border Surveillance System
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=nvidia
WorkingDirectory=/home/nvidia/rockUGV
ExecStartPre=/bin/sleep 10
ExecStart=/home/nvidia/rockUGV/scripts/startup.sh
ExecStop=/home/nvidia/rockUGV/scripts/shutdown.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

**Document Version**: 1.0  
**Last Updated**: January 2026
