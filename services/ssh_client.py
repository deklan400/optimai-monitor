import shlex
import subprocess

from utils.activity_parser import parse_assignment_activity


def _clip(text, limit=260):
    text = " ".join((text or "").split())
    if not text:
        return ""
    return text[:limit]


def run_ssh(host, command, timeout=10):
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=5",
                "-o", "ServerAliveInterval=5",
                "-o", "ServerAliveCountMax=2",
                host,
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    except Exception:
        return None


def test_ssh_connection(host):
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=5",
                "-o", "ServerAliveInterval=5",
                "-o", "ServerAliveCountMax=2",
                host,
                "echo SSH_OK",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown error").strip()
            return False, detail

        output = (result.stdout or "").strip()
        if "SSH_OK" not in output:
            return False, f"unexpected response: {output}"

        return True, "ok"

    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def get_status(host):
    output = run_ssh(host, "systemctl is-active optimai")
    if not output:
        return "down"
    return "running" if output.strip() == "active" else "down"


def diagnose_down_reason(host):
    """Coba jelaskan kenapa node terdeteksi DOWN untuk alert Telegram."""
    ssh_ok, ssh_detail = test_ssh_connection(host)
    if not ssh_ok:
        detail = _clip(ssh_detail, 220)
        lower = detail.lower()
        if "permission denied" in lower:
            return f"SSH gagal: permission denied/key salah. Detail: {detail}"
        if "connection refused" in lower:
            return f"SSH gagal: connection refused. Kemungkinan SSH service mati / port tertutup. Detail: {detail}"
        if "timed out" in lower or "timeout" in lower:
            return f"SSH gagal: timeout. Kemungkinan VPS offline/network lambat/firewall. Detail: {detail}"
        if "no route" in lower or "could not resolve" in lower:
            return f"SSH gagal: network/DNS. Detail: {detail}"
        return f"SSH gagal: {detail or 'unknown error'}"

    command = r'''
STATUS=$(systemctl is-active optimai 2>/dev/null || true)
SUBSTATE=$(systemctl show optimai -p SubState --value 2>/dev/null || true)
RESULT=$(systemctl show optimai -p Result --value 2>/dev/null || true)
EXIT_CODE=$(systemctl show optimai -p ExecMainCode --value 2>/dev/null || true)
EXIT_STATUS=$(systemctl show optimai -p ExecMainStatus --value 2>/dev/null || true)
ACTIVE_SINCE=$(systemctl show optimai -p ActiveEnterTimestamp --value 2>/dev/null || true)
DOCKER=$(systemctl is-active docker 2>/dev/null || true)
DISK=$(df -P / | awk 'NR==2 {print $5}' | tr -d '%')
MEM=$(free -m | awk '/^Mem:/ {print int($3*100/$2)}')
CLI=$(command -v optimai-cli 2>/dev/null || true)
RECENT=$(journalctl -u optimai -n 80 --no-pager -o cat 2>/dev/null | grep -Ei 'error|failed|failure|timeout|denied|unauthorized|newer|docker|cannot|refused|killed|oom' | tail -1 || true)
printf 'status=%s\nsubstate=%s\nresult=%s\nexit_code=%s\nexit_status=%s\nactive_since=%s\ndocker=%s\ndisk=%s\nmem=%s\ncli=%s\nrecent=%s\n' "$STATUS" "$SUBSTATE" "$RESULT" "$EXIT_CODE" "$EXIT_STATUS" "$ACTIVE_SINCE" "$DOCKER" "$DISK" "$MEM" "$CLI" "$RECENT"
'''
    output = run_ssh(host, command, timeout=20)
    if output is None:
        return "SSH OK, tapi gagal ambil diagnosa. Cek manual: systemctl status optimai"

    info = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            info[key.strip()] = value.strip()

    status = info.get("status") or "unknown"
    substate = info.get("substate") or "unknown"
    result = info.get("result") or "unknown"
    docker = info.get("docker") or "unknown"
    recent = _clip(info.get("recent"), 260)
    cli = info.get("cli") or ""

    try:
        disk = int(info.get("disk") or 0)
    except ValueError:
        disk = 0
    try:
        mem = int(info.get("mem") or 0)
    except ValueError:
        mem = 0

    reasons = []
    if status != "active":
        base = f"Service optimai {status}/{substate}"
        if result and result != "success":
            base += f", result={result}"
        exit_status = info.get("exit_status") or ""
        if exit_status and exit_status not in {"0", "-"}:
            base += f", exit={exit_status}"
        reasons.append(base)
    if docker != "active":
        reasons.append(f"Docker {docker}")
    if not cli:
        reasons.append("optimai-cli tidak ditemukan di PATH")
    if disk >= 90:
        reasons.append(f"Disk hampir penuh {disk}%")
    if mem >= 95:
        reasons.append(f"RAM sangat tinggi {mem}%")
    if recent:
        reasons.append(f"Log terakhir: {recent}")

    if reasons:
        return "; ".join(reasons)
    return f"Service optimai tidak active ({status}/{substate}), tapi tidak ada error jelas. Cek journalctl -u optimai -n 100"


def get_reward_raw(host):
    output = run_ssh(host, "optimai-cli rewards balance", timeout=20)
    if not output or "error" in output.lower():
        return None
    return output


def get_node_metrics(host, since_utc, until_utc=None):
    """Hitung assignment unik dari journal OptimAI pada rentang UTC."""
    journal = f"journalctl -u optimai --since {shlex.quote(since_utc)} "
    if until_utc:
        journal += f"--until {shlex.quote(until_utc)} "
    journal += "--no-pager -o cat 2>/dev/null"

    command = f"{journal} | grep -Ei 'assignment|crawl|submit' || true"
    output = run_ssh(host, command, timeout=45)

    if output is None:
        return {
            "available": False,
            "assignments": 0,
            "submitted": 0,
            "failed": 0,
            "pending": 0,
            "retried": 0,
        }

    return parse_assignment_activity(output)


def get_node_system_detail(host):
    """Ambil ringkasan sistem untuk menu Detail VPS dan stale detector."""
    command = r'''
STATUS=$(systemctl is-active optimai 2>/dev/null || true)
ACTIVE=$(systemctl show optimai -p ActiveEnterTimestamp --value 2>/dev/null || true)
MEM=$(free -m | awk '/^Mem:/ {printf "%s/%s MB", $3, $2}')
DISK=$(df -P / | awk 'NR==2 {print $5}')
DOCKER=$(systemctl is-active docker 2>/dev/null || true)
HOSTNAME_VALUE=$(hostname)
LAST_TASK_LINE=$(journalctl -u optimai --since "24 hours ago" --no-pager -o cat 2>/dev/null | grep -Ei 'assignment .* submitted successfully|fetched [1-9][0-9]* actionable assignments' | tail -1)
LAST_TASK_TS=$(journalctl -u optimai --since "24 hours ago" --no-pager -o short-unix 2>/dev/null | grep -Ei 'assignment .* submitted successfully|fetched [1-9][0-9]* actionable assignments' | tail -1 | awk '{print $1}' | cut -d. -f1)
NOW_TS=$(date +%s)
if [ -n "$LAST_TASK_TS" ]; then
  LAST_TASK_AGE=$((NOW_TS - LAST_TASK_TS))
else
  LAST_TASK_AGE=-1
fi
printf 'hostname=%s\nstatus=%s\nactive_since=%s\nmemory=%s\ndisk=%s\ndocker=%s\nlast_task_age_seconds=%s\nlast_task=%s\n' "$HOSTNAME_VALUE" "$STATUS" "$ACTIVE" "$MEM" "$DISK" "$DOCKER" "$LAST_TASK_AGE" "$LAST_TASK_LINE"
'''
    output = run_ssh(host, command, timeout=25)
    if output is None:
        return {"available": False}

    detail = {"available": True}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        detail[key.strip()] = value.strip()
    return detail
