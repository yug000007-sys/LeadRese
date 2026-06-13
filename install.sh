#!/bin/bash
set -e

sudo apt update
sudo apt install python3-pip python3-venv git nginx unzip -y

cd /root/company-enrichment-tool

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

sudo cp deploy/company-enrichment.service /etc/systemd/system/company-enrichment.service
sudo systemctl daemon-reload
sudo systemctl enable company-enrichment
sudo systemctl restart company-enrichment

echo "App started."
echo "Open: http://YOUR_SERVER_IP:8501"
echo "Logs: sudo journalctl -u company-enrichment -f"
