#!/bin/bash

# GreetBot Systemd Service Installer
# Run this script on your Raspberry Pi to start GreetBot on boot.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo ./install_service.sh)"
  exit
fi

SERVICE_FILE="/etc/systemd/system/greetbot.service"
USER_NAME=$(logname)
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/.venv"
MAIN_SCRIPT="$PROJECT_DIR/main.py"

echo "Creating systemd service file..."

cat <<EOF > $SERVICE_FILE
[Unit]
Description=GreetBot AI Assistant
After=network.target sound.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment="DISPLAY=:0"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$VENV_DIR/bin/python $MAIN_SCRIPT
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=graphical.target
EOF

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling GreetBot service to start on boot..."
systemctl enable greetbot.service

echo "Starting GreetBot service..."
systemctl start greetbot.service

echo ""
echo "✅ GreetBot has been configured to start automatically on boot!"
echo "To check its status, run: sudo systemctl status greetbot"
echo "To view logs, run: journalctl -u greetbot -f"
