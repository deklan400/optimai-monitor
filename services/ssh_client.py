import subprocess


def run_ssh(host, command):
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
                command
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    except Exception:
        return None


def get_status(host):
    output = run_ssh(host, "systemctl is-active optimai")

    if not output:
        return "down"

    if "active" in output:
        return "running"

    return "down"


def get_reward_raw(host):
    output = run_ssh(host, "optimai-cli rewards balance")

    if not output:
        return None

    # filter error
    if "error" in output.lower():
        return None

    return output
