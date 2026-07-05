#!/usr/bin/env bash
set -e
SIZE_GB="${1:-32}"
case "$SIZE_GB" in ''|*[!0-9]*) echo "Size must be a number"; exit 1;; esac
CURRENT_MB=$(free -m | awk '/Swap:/ {print $2}')
TARGET_MB=$((SIZE_GB * 1024))
echo "current_swap_mb=$CURRENT_MB"
echo "target_swap_gb=$SIZE_GB"
if [ "${CURRENT_MB:-0}" -ge "$TARGET_MB" ]; then
  echo "Swap already enough"
  free -h
  exit 0
fi
fallocate -l "${SIZE_GB}G" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count="$TARGET_MB"
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h
