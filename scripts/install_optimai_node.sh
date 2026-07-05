#!/usr/bin/env bash
set -e

apt update -y && apt upgrade -y
apt install -y curl docker.io
systemctl start docker
systemctl enable docker
rm -f /usr/local/bin/optimai-cli
rm -rf ~/.optimai
curl -L https://optimai.network/download/cli-node/linux -o optimai-cli
chmod +x optimai-cli
mv optimai-cli /usr/local/bin/optimai-cli

echo "========================================="
echo "MASUKKAN EMAIL OPTIMAI LU:"
echo "========================================="
read -r EMAIL
optimai-cli auth login --email "$EMAIL"

echo "========================================="
echo "MEMBUAT SERVICE AUTO RUN..."
echo "========================================="
cat <<'EOF' > /etc/systemd/system/optimai.service
[Unit]
Description=OptimAI Node
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/optimai-cli node start
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable optimai
systemctl start optimai

echo "========================================="
echo "SETUP SELESAI - NODE RUNNING"
echo "========================================="
sleep 3
journalctl -u optimai -f
