import os
import re
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.check_cycle import current_local_date, day_window_utc
from core.history import get_recent_days, get_week_summary, save_daily_snapshot
from core.monitor import check_all_vps
from core.reporter import get_account_reward
from core.vps_store import add_vps, delete_vps, load_vps, save_vps
from services.ssh_bootstrap import setup_ssh_key_with_password
from services.ssh_client import run_ssh
from services.telegram_bot import send_message

load_dotenv()

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "").strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
VPS_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")

app = FastAPI(title="OptimAI Control Dashboard")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class VpsPayload(BaseModel):
    name: str
    host: str
    password: str | None = None


def _require_token(x_dashboard_token: str | None = Header(default=None)):
    if DASHBOARD_TOKEN and x_dashboard_token != DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid dashboard token")


def _validate_vps_name(name):
    clean = (name or "").strip()
    if not VPS_NAME_RE.fullmatch(clean):
        raise HTTPException(status_code=400, detail="Nama VPS hanya boleh huruf, angka, underscore, dan strip. Maksimal 32 karakter.")
    return clean


def _validate_vps_host(host):
    clean = (host or "").strip()
    if "@" not in clean:
        raise HTTPException(status_code=400, detail="Host harus format user@ip, contoh root@1.2.3.4")
    user, target = clean.split("@", 1)
    if not user or not target:
        raise HTTPException(status_code=400, detail="Host harus format user@ip, contoh root@1.2.3.4")
    return clean


def _setup_key_if_password(host, password):
    password = (password or "").strip()
    if not password:
        return {"ssh_key_setup": "skipped", "message": "Password kosong, setup SSH key dilewati."}

    ok, detail = setup_ssh_key_with_password(host, password)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Setup SSH key gagal: {detail}")
    return {"ssh_key_setup": "ok", "message": detail}


def _notify_telegram(text):
    try:
        send_message(text)
    except Exception as exc:
        print(f"[DASHBOARD TELEGRAM NOTIFY ERROR] {exc}")


def _success_rate(metrics):
    if not metrics:
        return 0.0
    task = int(metrics.get("assignments", 0) or 0)
    submit = int(metrics.get("submitted", 0) or 0)
    return round((submit / task) * 100, 1) if task else 0.0


def _metrics_total(nodes):
    totals = {"assignments": 0, "submitted": 0, "failed": 0, "pending": 0, "retried": 0}
    for node in nodes:
        metrics = node.get("metrics") or {}
        if not metrics.get("available"):
            continue
        for key in totals:
            totals[key] += int(metrics.get(key, 0) or 0)
    return totals


def _node_payload(item):
    metrics = item.get("metrics") or {}
    system = item.get("system") or {}
    return {
        "name": item.get("name"),
        "host": item.get("host"),
        "status": item.get("status"),
        "reward": item.get("reward"),
        "metrics": metrics,
        "system": system,
        "success_rate": _success_rate(metrics),
    }


def _load_current(include_details=False):
    vps_dict = load_vps()
    since_utc, _ = day_window_utc()
    current = check_all_vps(vps_dict, include_reward=True, metrics_since=since_utc, include_details=include_details)
    account_total, source_node = get_account_reward(current)
    save_daily_snapshot(str(current_local_date()), current, account_total, source_node)
    nodes = [_node_payload(item) for item in current]
    totals = _metrics_total(nodes)
    return vps_dict, current, nodes, totals, account_total, source_node


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


@app.get("/api/overview")
def overview():
    _, _, nodes, totals, account_total, source_node = _load_current(include_details=True)
    running = sum(1 for node in nodes if node.get("status") == "running")
    down = len(nodes) - running
    ranking = sorted(nodes, key=lambda node: (-int((node.get("metrics") or {}).get("submitted", 0) or 0), node.get("name") or ""))[:5]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "date": str(current_local_date()),
        "total_vps": len(nodes),
        "running": running,
        "down": down,
        "totals": totals,
        "account_total": account_total,
        "source_node": source_node,
        "nodes": nodes,
        "top_nodes": ranking,
    }


@app.get("/api/vps")
def vps_list():
    data = load_vps()
    return {"vps": [{"name": name, "host": host} for name, host in sorted(data.items(), key=lambda item: item[0].lower())]}


@app.post("/api/vps")
def create_vps(payload: VpsPayload, x_dashboard_token: str | None = Header(default=None)):
    _require_token(x_dashboard_token)
    name = _validate_vps_name(payload.name)
    host = _validate_vps_host(payload.host)

    data = load_vps()
    if name in data:
        raise HTTPException(status_code=409, detail="Nama VPS sudah ada.")

    setup_result = _setup_key_if_password(host, payload.password)
    add_vps(name, host)
    _notify_telegram(f"➕ VPS ditambahkan dari dashboard:\n- {name}: {host}")
    return {"ok": True, "action": "created", "name": name, "host": host, **setup_result}


@app.put("/api/vps/{old_name}")
def edit_vps(old_name: str, payload: VpsPayload, x_dashboard_token: str | None = Header(default=None)):
    _require_token(x_dashboard_token)
    old_name = _validate_vps_name(old_name)
    new_name = _validate_vps_name(payload.name)
    host = _validate_vps_host(payload.host)

    data = load_vps()
    if old_name not in data:
        raise HTTPException(status_code=404, detail="VPS tidak ditemukan.")
    if new_name != old_name and new_name in data:
        raise HTTPException(status_code=409, detail="Nama VPS baru sudah dipakai.")

    setup_result = _setup_key_if_password(host, payload.password)
    old_host = data.get(old_name)
    data.pop(old_name, None)
    data[new_name] = host
    save_vps(data)
    _notify_telegram("✏️ VPS diedit dari dashboard:\n" f"- Lama: {old_name}: {old_host}\n" f"- Baru: {new_name}: {host}")
    return {"ok": True, "action": "updated", "old_name": old_name, "name": new_name, "host": host, **setup_result}


@app.delete("/api/vps/{name}")
def remove_vps(name: str, x_dashboard_token: str | None = Header(default=None)):
    _require_token(x_dashboard_token)
    name = _validate_vps_name(name)
    data = load_vps()
    host = data.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS tidak ditemukan.")

    deleted = delete_vps(name)
    if not deleted:
        raise HTTPException(status_code=404, detail="VPS tidak ditemukan.")

    _notify_telegram(f"❌ VPS dihapus dari dashboard:\n- {name}: {host}")
    return {"ok": True, "action": "deleted", "name": name, "host": host}


@app.get("/api/vps/{name}")
def node_detail(name: str):
    vps_dict = load_vps()
    host = vps_dict.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS not found")

    since_utc, _ = day_window_utc()
    current = check_all_vps({name: host}, include_reward=True, metrics_since=since_utc, include_details=True)
    if not current:
        raise HTTPException(status_code=404, detail="VPS not found")
    return _node_payload(current[0])


@app.get("/api/vps/{name}/logs")
def node_logs(name: str):
    vps_dict = load_vps()
    host = vps_dict.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS not found")

    command = "journalctl -u optimai -n 120 --no-pager -o short-iso 2>/dev/null || true"
    output = run_ssh(host, command, timeout=25)
    return {"name": name, "logs": output or ""}


@app.post("/api/vps/{name}/restart")
def restart_node(name: str, x_dashboard_token: str | None = Header(default=None)):
    _require_token(x_dashboard_token)
    vps_dict = load_vps()
    host = vps_dict.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS not found")

    command = "systemctl restart optimai && sleep 2 && systemctl is-active optimai"
    output = run_ssh(host, command, timeout=35)
    if not output:
        raise HTTPException(status_code=500, detail="Restart command failed")
    clean = output.strip()
    return {"name": name, "status": "running" if clean == "active" else clean, "raw": output}


@app.get("/api/history/daily")
def history_daily():
    return {"days": get_recent_days(limit=14)}


@app.get("/api/history/weekly")
def history_weekly():
    return get_week_summary(end_date=current_local_date(), days=7)
