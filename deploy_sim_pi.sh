#!/bin/bash
#
# Deploy UniRoam Simulator to Raspberry Pi
# Usage: ./deploy_sim_pi.sh <hostname> <model> <serial>
#

set -e

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <hostname> <model> <serial> [c2_url]"
    echo ""
    echo "Example:"
    echo "  $0 pi@192.168.1.101 Go2 SIM_001 http://192.168.1.100:8443"
    exit 1
fi

HOST=$1
MODEL=$2
SERIAL=$3
C2_URL=${4:-"http://localhost:8443"}

echo "========================================="
echo "UniRoam Simulator Deployment"
echo "========================================="
echo "Target:  $HOST"
echo "Model:   $MODEL"
echo "Serial:  $SERIAL"
echo "C2 URL:  $C2_URL"
echo "========================================="

# Create remote directory
echo "[*] Creating remote directory..."
ssh "$HOST" "mkdir -p ~/uniroam"

# Copy necessary files
echo "[*] Copying files..."
scp -r \
    robot_simulator.py \
    virtual_ble.py \
    command_sandbox.py \
    requirements.txt \
    uniroam/ \
    "$HOST:~/uniroam/"

# Install dependencies
echo "[*] Installing dependencies on remote..."
ssh "$HOST" "cd ~/uniroam && pip3 install --user -r requirements.txt"

# Create systemd service
echo "[*] Creating systemd service..."
ssh "$HOST" "cat > ~/uniroam/robot_simulator.service << EOF
[Unit]
Description=UniRoam Robot Simulator
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/uniroam
Environment=VIRTUAL_BLE=true
Environment=C2_HOST=${C2_URL#*://}
ExecStart=/usr/bin/python3 robot_simulator.py --model $MODEL --serial $SERIAL --mode distributed
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
"

# Install service
echo "[*] Installing and starting service..."
ssh "$HOST" "sudo cp ~/uniroam/robot_simulator.service /etc/systemd/system/ && \
             sudo systemctl daemon-reload && \
             sudo systemctl enable robot_simulator && \
             sudo systemctl start robot_simulator"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Service status:"
ssh "$HOST" "sudo systemctl status robot_simulator --no-pager"

echo ""
echo "To view logs:"
echo "  ssh $HOST journalctl -u robot_simulator -f"
echo ""
echo "To stop simulator:"
echo "  ssh $HOST sudo systemctl stop robot_simulator"

