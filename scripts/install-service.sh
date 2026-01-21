#!/bin/bash
#
# RockUGV Service Installation Script
# Sets up automatic startup on boot
#
# Author: Border Surveillance Team
# Date: January 2026
#
# Usage: sudo ./install-service.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo ./install-service.sh${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================="
echo "RockUGV Service Installation"
echo -e "==========================================${NC}"

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-nvidia}
PROJECT_DIR="/home/$ACTUAL_USER/rockUGV"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  User: $ACTUAL_USER"
echo "  Project Directory: $PROJECT_DIR"

# Verify project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}ERROR: Project directory not found: $PROJECT_DIR${NC}"
    echo "Please ensure the project is set up at $PROJECT_DIR"
    exit 1
fi

# Create logs directory
echo -e "\n${YELLOW}[1/6] Creating logs directory...${NC}"
mkdir -p "$PROJECT_DIR/logs"
chown "$ACTUAL_USER:$ACTUAL_USER" "$PROJECT_DIR/logs"
echo -e "${GREEN}Done${NC}"

# Make scripts executable
echo -e "\n${YELLOW}[2/6] Making scripts executable...${NC}"
chmod +x "$PROJECT_DIR/scripts/startup.sh"
chmod +x "$PROJECT_DIR/scripts/shutdown.sh"
echo -e "${GREEN}Done${NC}"

# Update service file with correct user
echo -e "\n${YELLOW}[3/6] Configuring service file...${NC}"
sed -i "s/User=nvidia/User=$ACTUAL_USER/g" "$PROJECT_DIR/rockugv.service"
sed -i "s/Group=nvidia/Group=$ACTUAL_USER/g" "$PROJECT_DIR/rockugv.service"
sed -i "s|/home/nvidia/rockUGV|$PROJECT_DIR|g" "$PROJECT_DIR/rockugv.service"
echo -e "${GREEN}Done${NC}"

# Copy service file to systemd
echo -e "\n${YELLOW}[4/6] Installing systemd service...${NC}"
cp "$PROJECT_DIR/rockugv.service" /etc/systemd/system/
echo -e "${GREEN}Done${NC}"

# Reload systemd
echo -e "\n${YELLOW}[5/6] Reloading systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}Done${NC}"

# Enable the service
echo -e "\n${YELLOW}[6/6] Enabling service for auto-start...${NC}"
systemctl enable rockugv.service
echo -e "${GREEN}Done${NC}"

echo -e "\n${GREEN}=========================================="
echo "Installation Complete!"
echo -e "==========================================${NC}"

echo -e "\n${YELLOW}Service Commands:${NC}"
echo "  Start:   sudo systemctl start rockugv"
echo "  Stop:    sudo systemctl stop rockugv"
echo "  Status:  sudo systemctl status rockugv"
echo "  Logs:    sudo journalctl -u rockugv -f"
echo "  Disable: sudo systemctl disable rockugv"

echo -e "\n${YELLOW}Log File:${NC}"
echo "  $PROJECT_DIR/logs/startup.log"

echo -e "\n${YELLOW}Test the service now?${NC}"
read -p "Start the service? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Starting service...${NC}"
    systemctl start rockugv
    sleep 5
    systemctl status rockugv --no-pager
fi

echo -e "\n${GREEN}The system will now start automatically on boot!${NC}"
