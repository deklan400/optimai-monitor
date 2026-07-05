import hashlib
import hmac
import os
import re
import time

from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

from core.vps_store import load_vps
from services.ssh_client import run_ssh

load_dotenv()

CHAT_ID = os.getenv("CHAT_ID", "").strip()
ALLOWED_TELEGRAM_IDS = {
    item.strip()
    for item in os.getenv("DASHBOARD_ALLOWED_TELEGRAM_IDS", CHAT_ID).split(",")
    if item.strip()
}
SESSION_SECRET = (
    os.getenv("DASHBOARD_SESSION_SECRET", "").strip()
    or os.getenv("DASHBOARD_TOKEN", "").strip()
    or os.getenv("BOT_TOKEN", "")
    or "optimai-dashboard-session"
)
SESSION_TTL = 60 * 60 * 24 * 7
VPS_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")

router = APIRouter(prefix="/api/install-node", tags=["install-node"])


class SwapPayload(BaseModel):
    names: list[str]
    size_gb: int


def _sign_session(telegram_id: str, timestamp: int) -> str:
    message = f"{telegram_id}:{timestamp}".encode()
    return hmac.new(SESSION_SECRET.encode(), message, hashlib.sha256).hexdigest()


def _parse_session(session_value: str | None):
    if not session_value:
        return None
    try:
        telegram_id, raw_timestamp, signature = session_value.split(":", 2)
        timestamp = int(raw_timestamp)
    except (ValueError, TypeError):
        return None
    if int(time.time()) - timestamp > SESSION_TTL:
        return None
    if not hmac.compare_digest(signature, _sign_session(telegram_id, timestamp)):
        return None
    return telegram_id if telegram_id in ALLOWED_TELEGRAM_IDS else None


def _require_login(optimai_session: str | None, opt_session: str | None):
    telegram_id = _parse_session(optimai_session or opt_session)
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Login required")
    return telegram_id


def _natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value or "")]


def _selected_vps(names: list[str]):
    vps = load_vps()
    if not names:
        raise HTTPException(status_code=400, detail="Pilih minimal 1 VPS.")
    selected = {}
    for raw_name in names:
        name = (raw_name or "").strip()
        if not VPS_NAME_RE.fullmatch(name):
            raise HTTPException(status_code=400, detail=f"Nama VPS tidak valid: {raw_name}")
        host = vps.get(name)
        if not host:
            raise HTTPException(status_code=404, detail=f"VPS tidak ditemukan: {name}")
        selected[name] = host
    return dict(sorted(selected.items(), key=lambda item: _natural_key(item[0])))


def _parse_key_values(output: str):
    data = {}
    for line in (output or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def _status_for(host: str):
    command = r'''
printf 'ssh=ok\n'
printf 'hostname=%s\n' "$(hostname 2>/dev/null || true)"
printf 'cli=%s\n' "$(command -v optimai-cli 2>/dev/null || true)"
printf 'optimai=%s\n' "$(systemctl is-active optimai 2>/dev/null || true)"
printf 'docker=%s\n' "$(systemctl is-active docker 2>/dev/null || true)"
printf 'swap_mb=%s\n' "$(free -m | awk '/Swap:/ {print $2}')"
printf 'swap_used_mb=%s\n' "$(free -m | awk '/Swap:/ {print $3}')"
if [ -d /root/.optimai ] || [ -d "$HOME/.optimai" ]; then echo 'auth_dir=yes'; else echo 'auth_dir=no'; fi
printf 'version=%s\n' "$(optimai-cli --version 2>/dev/null | head -1 || true)"
'''
    output = run_ssh(host, command, timeout=30)
    if output is None:
        return {
            "ssh": False,
            "installed": False,
            "running": False,
            "docker": "unknown",
            "swap_mb": 0,
            "swap_gb": 0,
            "auth_dir": "unknown",
            "reason": "SSH gagal / timeout",
        }

    data = _parse_key_values(output)
    swap_mb = int(data.get("swap_mb") or 0)
    installed = bool(data.get("cli"))
    running = data.get("optimai") == "active"
    docker = data.get("docker") or "unknown"
    if running:
        reason = "Node running"
    elif not installed:
        reason = "optimai-cli belum terinstall"
    elif docker != "active":
        reason = f"Docker {docker}"
    else:
        reason = f"Service optimai {data.get('optimai') or 'unknown'}"

    return {
        "ssh": True,
        "hostname": data.get("hostname", ""),
        "installed": installed,
        "running": running,
        "docker": docker,
        "swap_mb": swap_mb,
        "swap_gb": round(swap_mb / 1024, 1) if swap_mb else 0,
        "auth_dir": data.get("auth_dir", "unknown"),
        "version": data.get("version", ""),
        "reason": reason,
    }


def _swap_script(size_gb: int):
    return f'''#!/usr/bin/env bash
set -e
SIZE_GB={int(size_gb)}
CURRENT_MB=$(free -m | awk '/Swap:/ {{print $2}}')
TARGET_MB=$((SIZE_GB * 1024))
echo "target_swap=${{SIZE_GB}}G"
echo "current_swap_mb=${{CURRENT_MB}}"
if [ "${{CURRENT_MB:-0}}" -ge "$TARGET_MB" ]; then
  echo "swap_status=already_enough"
  free -h
  exit 0
fi
swapoff /swapfile 2>/dev/null || true
rm -f /swapfile
if command -v fallocate >/dev/null 2>&1; then
  fallocate -l "${{SIZE_GB}}G" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count="$TARGET_MB"
else
  dd if=/dev/zero of=/swapfile bs=1M count="$TARGET_MB"
fi
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo "swap_status=created"
free -h
'''


@router.get("/status")
def install_node_status(
    optimai_session: str | None = Cookie(default=None),
    opt_session: str | None = Cookie(default=None),
):
    _require_login(optimai_session, opt_session)
    vps = load_vps()
    nodes = []
    for name, host in sorted(vps.items(), key=lambda item: _natural_key(item[0])):
        nodes.append({"name": name, "host": host, **_status_for(host)})
    return {"count": len(nodes), "nodes": nodes}


@router.post("/swap")
def create_swap(
    payload: SwapPayload,
    optimai_session: str | None = Cookie(default=None),
    opt_session: str | None = Cookie(default=None),
):
    _require_login(optimai_session, opt_session)
    size_gb = int(payload.size_gb or 0)
    if size_gb < 1 or size_gb > 256:
        raise HTTPException(status_code=400, detail="Ukuran swap harus 1 sampai 256 GB.")

    results = []
    for name, host in _selected_vps(payload.names).items():
        output = run_ssh(host, _swap_script(size_gb), timeout=900)
        results.append({
            "name": name,
            "host": host,
            "ok": output is not None,
            "output": output or "SSH gagal / timeout",
            "status": _status_for(host),
        })
    return {"ok": all(item["ok"] for item in results), "results": results}
