import subprocess


def run_ssh(host, command):
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", host, command],
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

    if output == "active":
        return "running"

    return "down"


def get_reward_raw(host):
    return run_ssh(host, "optimai-cli rewards balance")
