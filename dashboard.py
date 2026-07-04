import hashlib
import hmac
import os
import re
import time
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.check_cycle import current_local_date, day_window_utc
from core.history import get_recent_days, get_week_summary, save_daily_snapshot
from core.monitor import check_all_vps
from core.reporter import get_account_reward
from core.vps_store import add_vps, delete_vps, load_vps, save_vps
from services.ssh_bootstrap import setup_ssh_key_with_password
from services.ssh_client import run_ssh

load_dotenv()

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "").strip()
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()
ALLOWED_TELEGRAM_IDS = {
    item.strip()
    for item in os.getenv("DASHBOARD_ALLOWED_TELEGRAM_IDS", CHAT_ID).split(",")
    if item.strip()
}
SESSION_SECRET = (
    os.getenv("DASHBOARD_SESSION_SECRET", "").strip()
    or DASHBOARD_TOKEN
    or os.getenv("BOT_TOKEN", "")
    or "optimai-dashboard-session"
)
SESSION_COOKIE = "optimai_session"
LEGACY_SESSION_COOKIE = "opt_session"
SESSION_TTL = 60 * 60 * 24 * 7
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
VPS_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")

NODE_COMMANDS = {
    "restart": "systemctl restart optimai && sleep 2 && systemctl is-active optimai",
    "start": "systemctl start optimai && sleep 2 && systemctl is-active optimai",
    "stop": "systemctl stop optimai && sleep 1 && systemctl is-active optimai || true",
    "status": "systemctl status optimai --no-pager -l | tail -n 80",
    "reward": "optimai-cli rewards balance",
}

MINI_COMMANDS = {
    "status": "systemctl status optimai --no-pager -l | tail -n 80",
    "reward": "optimai-cli rewards balance",
    "ram": "free -h",
    "disk": "df -h /",
    "docker": "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -n 60",
    "logs": "journalctl -u optimai -n 100 --no-pager -o short-iso 2>/dev/null || true",
    "errors": "journalctl -u optimai --since '6 hours ago' --no-pager -o short-iso 2>/dev/null | grep -Ei 'error|failed|rejected|timeout' | tail -n 120 || true",
    "version": "optimai-cli --version 2>/dev/null || which optimai-cli || true",
}

app = FastAPI(title="OptimAI Control Dashboard")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class LoginPayload(BaseModel):
    telegram_id: str


class VpsPayload(BaseModel):
    name: str
    host: str
    password: str | None = None


class ActionPayload(BaseModel):
    action: str


class MiniCommandPayload(BaseModel):
    command: str


class GlobalActionPayload(BaseModel):
    action: str


def _natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value or "")]


def _sign_session(telegram_id: str, timestamp: int) -> str:
    message = f"{telegram_id}:{timestamp}".encode()
    return hmac.new(SESSION_SECRET.encode(), message, hashlib.sha256).hexdigest()


def _make_session(telegram_id: str) -> str:
    timestamp = int(time.time())
    return f"{telegram_id}:{timestamp}:{_sign_session(telegram_id, timestamp)}"


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


def _set_session_cookies(response: Response, session_value: str):
    for cookie_name in (SESSION_COOKIE, LEGACY_SESSION_COOKIE):
        response.set_cookie(cookie_name, session_value, httponly=True, samesite="lax", max_age=SESSION_TTL)


def _delete_session_cookies(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(LEGACY_SESSION_COOKIE)


def _session_from_request(request: Request):
    return request.cookies.get(SESSION_COOKIE) or request.cookies.get(LEGACY_SESSION_COOKIE)


def _require_login(opt_session: str | None = Cookie(default=None)):
    telegram_id = _parse_session(opt_session)
    if not telegram_id:
        raise HTTPException(status_code=401, detail="Login required")
    return telegram_id


def _page_is_logged_in(request: Request) -> bool:
    return bool(_parse_session(_session_from_request(request)))


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
    """Dashboard action notifications are disabled; Telegram keeps only normal bot reports/alerts."""
    return None


def _success_rate(metrics):
    task = int((metrics or {}).get("assignments", 0) or 0)
    submit = int((metrics or {}).get("submitted", 0) or 0)
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


def _stale_payload(status, system):
    try:
        age = int((system or {}).get("last_task_age_seconds", -1))
    except (TypeError, ValueError):
        age = -1

    if status != "running":
        return {"level": "down", "label": "Down", "age_seconds": age}
    if age < 0:
        return {"level": "unknown", "label": "No task 24h", "age_seconds": age}
    if age >= 21600:
        return {"level": "danger", "label": "Stale 6h+", "age_seconds": age}
    if age >= 10800:
        return {"level": "warning", "label": "No task 3h+", "age_seconds": age}
    return {"level": "healthy", "label": "Live", "age_seconds": age}


def _node_payload(item):
    metrics = item.get("metrics") or {}
    system = item.get("system") or {}
    status = item.get("status")
    return {
        "name": item.get("name"),
        "host": item.get("host"),
        "status": status,
        "reward": item.get("reward"),
        "metrics": metrics,
        "system": system,
        "success_rate": _success_rate(metrics),
        "stale": _stale_payload(status, system),
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


def _run_node_command(name, command, timeout=35):
    vps_dict = load_vps()
    host = vps_dict.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS not found")
    output = run_ssh(host, command, timeout=timeout)
    return {"name": name, "host": host, "output": output or "", "ok": output is not None}


@app.get("/")
def index(request: Request):
    session_value = _session_from_request(request)
    if not _parse_session(session_value):
        return RedirectResponse("/login", status_code=302)
    response = FileResponse(os.path.join(WEB_DIR, "index.html"))
    _set_session_cookies(response, session_value)
    return response


@app.get("/login")
def login_page(request: Request):
    if _page_is_logged_in(request):
        return RedirectResponse("/", status_code=302)
    return FileResponse(os.path.join(WEB_DIR, "login.html"))


@app.post("/api/login")
def login(payload: LoginPayload, response: Response):
    telegram_id = str(payload.telegram_id).strip()
    if telegram_id not in ALLOWED_TELEGRAM_IDS:
        raise HTTPException(status_code=401, detail="Telegram ID tidak diizinkan.")
    _set_session_cookies(response, _make_session(telegram_id))
    return {"ok": True, "telegram_id": telegram_id}


@app.post("/api/logout")
def logout(response: Response):
    _delete_session_cookies(response)
    return {"ok": True}


@app.get("/api/me")
def me(opt_session: str | None = Cookie(default=None)):
    telegram_id = _require_login(opt_session)
    return {"telegram_id": telegram_id, "dashboard_url": DASHBOARD_URL}


@app.get("/api/overview")
def overview(opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    _, _, nodes, totals, account_total, source_node = _load_current(include_details=True)
    running = sum(1 for node in nodes if node.get("status") == "running")
    down = len(nodes) - running
    stale = sum(1 for node in nodes if node.get("stale", {}).get("level") in {"warning", "danger", "unknown"})
    ranking = sorted(nodes, key=lambda node: (-int((node.get("metrics") or {}).get("submitted", 0) or 0), _natural_key(node.get("name") or "")))[:5]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "date": str(current_local_date()),
        "total_vps": len(nodes),
        "running": running,
        "down": down,
        "stale": stale,
        "totals": totals,
        "account_total": account_total,
        "source_node": source_node,
        "nodes": nodes,
        "top_nodes": ranking,
    }


@app.get("/api/vps")
def vps_list(opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    data = load_vps()
    return {"vps": [{"name": name, "host": host} for name, host in sorted(data.items(), key=lambda item: _natural_key(item[0]))]}


@app.post("/api/vps")
def create_vps(payload: VpsPayload, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    name = _validate_vps_name(payload.name)
    host = _validate_vps_host(payload.host)
    data = load_vps()
    if name in data:
        raise HTTPException(status_code=409, detail="Nama VPS sudah ada.")
    setup_result = _setup_key_if_password(host, payload.password)
    add_vps(name, host)
    _notify_telegram("dashboard vps created")
    return {"ok": True, "action": "created", "name": name, "host": host, **setup_result}


@app.put("/api/vps/{old_name}")
def edit_vps(old_name: str, payload: VpsPayload, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    old_name = _validate_vps_name(old_name)
    new_name = _validate_vps_name(payload.name)
    host = _validate_vps_host(payload.host)
    data = load_vps()
    if old_name not in data:
        raise HTTPException(status_code=404, detail="VPS tidak ditemukan.")
    if new_name != old_name and new_name in data:
        raise HTTPException(status_code=409, detail="Nama VPS baru sudah dipakai.")
    setup_result = _setup_key_if_password(host, payload.password)
    data.pop(old_name, None)
    data[new_name] = host
    save_vps(data)
    _notify_telegram("dashboard vps updated")
    return {"ok": True, "action": "updated", "old_name": old_name, "name": new_name, "host": host, **setup_result}


@app.delete("/api/vps/{name}")
def remove_vps(name: str, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    name = _validate_vps_name(name)
    data = load_vps()
    host = data.get(name)
    if not host:
        raise HTTPException(status_code=404, detail="VPS tidak ditemukan.")
    if not delete_vps(name):
        raise HTTPException(status_code=404, detail="VPS tidak ditemukan.")
    _notify_telegram("dashboard vps deleted")
    return {"ok": True, "action": "deleted", "name": name, "host": host}


@app.get("/api/vps/{name}")
def node_detail(name: str, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
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
def node_logs(name: str, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    return _run_node_command(name, "journalctl -u optimai -n 120 --no-pager -o short-iso 2>/dev/null || true", timeout=25)


@app.post("/api/vps/{name}/restart")
def restart_node(name: str, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    result = _run_node_command(name, NODE_COMMANDS["restart"], timeout=35)
    _notify_telegram("dashboard restart")
    clean = result["output"].strip()
    result["status"] = "running" if clean == "active" else clean
    return result


@app.post("/api/vps/{name}/action")
def node_action(name: str, payload: ActionPayload, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    action = payload.action.strip()
    command = NODE_COMMANDS.get(action)
    if not command:
        raise HTTPException(status_code=400, detail="Action tidak dikenali.")
    result = _run_node_command(name, command, timeout=45)
    _notify_telegram("dashboard node action")
    result["action"] = action
    return result


@app.post("/api/vps/{name}/mini-command")
def mini_command(name: str, payload: MiniCommandPayload, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    command_key = payload.command.strip()
    command = MINI_COMMANDS.get(command_key)
    if not command:
        raise HTTPException(status_code=400, detail="Command tidak diizinkan.")
    result = _run_node_command(name, command, timeout=40)
    result["command"] = command_key
    return result


@app.post("/api/global-action")
def global_action(payload: GlobalActionPayload, opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    action = payload.action.strip()
    command_map = {
        "status_all": NODE_COMMANDS["status"],
        "reward_all": NODE_COMMANDS["reward"],
        "restart_all": NODE_COMMANDS["restart"],
        "start_all": NODE_COMMANDS["start"],
    }
    command = command_map.get(action)
    if not command:
        raise HTTPException(status_code=400, detail="Global command tidak dikenali.")
    results = []
    for name, host in sorted(load_vps().items(), key=lambda item: _natural_key(item[0])):
        output = run_ssh(host, command, timeout=45)
        results.append({"name": name, "host": host, "ok": output is not None, "output": output or ""})
    _notify_telegram("dashboard global action")
    return {"action": action, "results": results}


@app.get("/api/history/daily")
def history_daily(opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    return {"days": get_recent_days(limit=14)}


@app.get("/api/history/weekly")
def history_weekly(opt_session: str | None = Cookie(default=None)):
    _require_login(opt_session)
    return get_week_summary(end_date=current_local_date(), days=7)
