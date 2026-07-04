import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.check_cycle import current_local_date, day_window_utc
from core.history import get_recent_days, get_week_summary, save_daily_snapshot
from core.monitor import check_all_vps
from core.reporter import get_account_reward
from core.vps_store import load_vps
from services.ssh_client import run_ssh

load_dotenv()

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "").strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

app = FastAPI(title="OptimAI Control Dashboard")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def _require_token(x_dashboard_token: str | None = Header(default=None)):
    if DASHBOARD_TOKEN and x_dashboard_token != DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid dashboard token")


def _success_rate(metrics):
    if not metrics:
        return 0.0
    task = int(metrics.get("assignments", 0) or 0)
    submit = int(metrics.get("submitted", 0) or 0)
    return round((submit / task) * 100, 1) if task else 0.0


def _metrics_total(nodes):
    totals = {
        "assignments": 0,
        "submitted": 0,
        "failed": 0,
        "pending": 0,
        "retried": 0,
    }
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
    current = check_all_vps(
        vps_dict,
        include_reward=True,
        metrics_since=since_utc,
        include_details=include_details,
    )
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
    ranking = sorted(
        nodes,
        key=lambda node: (
            -int((node.get("metrics") or {}).get("submitted", 0) or 0),
            node.get("name") or "",
        ),
    )[:5]
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


@app.get("/api/vps/{name}")
def node_detail(name: str):
    vps_dict = load_vps()
    host = vps_dict.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS not found")

    since_utc, _ = day_window_utc()
    current = check_all_vps(
        {name: host},
        include_reward=True,
        metrics_since=since_utc,
        include_details=True,
    )
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
    return {"name": name, "status": "running" if "active" in output else output.strip(), "raw": output}


@app.get("/api/history/daily")
def history_daily():
    return {"days": get_recent_days(limit=14)}


@app.get("/api/history/weekly")
def history_weekly():
    return get_week_summary(end_date=current_local_date(), days=7)
