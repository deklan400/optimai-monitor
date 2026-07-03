import shlex
import subprocess


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

    if "active" in output:
        return "running"

    return "down"


def get_reward_raw(host):
    output = run_ssh(host, "optimai-cli rewards balance", timeout=20)

    if not output:
        return None

    if "error" in output.lower():
        return None

    return output


def get_node_metrics(host, since_utc, until_utc=None):
    """Hitung task, submit, dan gagal dari journal OptimAI pada rentang UTC."""
    journal = (
        "journalctl -u optimai "
        f"--since {shlex.quote(since_utc)} "
    )
    if until_utc:
        journal += f"--until {shlex.quote(until_utc)} "

    journal += "--no-pager -o cat 2>/dev/null"

    awk_program = r'''awk '
    {
        original = $0
        line = $0

        if (line ~ /fetched [0-9]+ actionable assignments/) {
            sub(/^.*fetched /, "", line)
            sub(/ actionable assignments.*$/, "", line)
            tasks += line + 0
        }

        lower = tolower(original)

        if (lower ~ /assignment .* submitted successfully/ ||
            lower ~ /successfully submitted.*assignment/) {
            submitted++
        }

        if ((lower ~ /assignment/ && lower ~ /(failed|rejected)/) ||
            (lower ~ /submit/ && lower ~ /(failed|error)/) ||
            (lower ~ /crawl/ && lower ~ /(failed|error)/)) {
            failed++
        }
    }
    END {
        printf "%d|%d|%d\n", tasks + 0, submitted + 0, failed + 0
    }' '''

    output = run_ssh(host, f"{journal} | {awk_program}", timeout=45)
    if not output:
        return {
            "available": False,
            "assignments": 0,
            "submitted": 0,
            "failed": 0,
        }

    try:
        tasks, submitted, failed = output.split("|")[-3:]
        return {
            "available": True,
            "assignments": int(tasks),
            "submitted": int(submitted),
            "failed": int(failed),
        }
    except (TypeError, ValueError):
        return {
            "available": False,
            "assignments": 0,
            "submitted": 0,
            "failed": 0,
        }
