import shlex
import subprocess

from utils.activity_parser import parse_assignment_activity


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
    """Ambil ringkasan sistem untuk menu Detail VPS."""
    command = r'''
STATUS=$(systemctl is-active optimai 2>/dev/null || true)
ACTIVE=$(systemctl show optimai -p ActiveEnterTimestamp --value 2>/dev/null || true)
MEM=$(free -m | awk '/^Mem:/ {printf "%s/%s MB", $3, $2}')
DISK=$(df -P / | awk 'NR==2 {print $5}')
DOCKER=$(systemctl is-active docker 2>/dev/null || true)
HOSTNAME_VALUE=$(hostname)
LAST_TASK=$(journalctl -u optimai --since "24 hours ago" --no-pager -o cat 2>/dev/null | grep -Ei 'assignment .* submitted successfully|fetched [1-9][0-9]* actionable assignments' | tail -1)
printf 'hostname=%s\nstatus=%s\nactive_since=%s\nmemory=%s\ndisk=%s\ndocker=%s\nlast_task=%s\n' "$HOSTNAME_VALUE" "$STATUS" "$ACTIVE" "$MEM" "$DISK" "$DOCKER" "$LAST_TASK"
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
