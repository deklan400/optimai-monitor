import subprocess

def run_ssh_command(host, command, timeout=10):
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", host, command],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            return None, result.stderr.strip()

        return result.stdout.strip(), None

    except Exception as e:
        return None, str(e)


def get_node_status(host):
    output, error = run_ssh_command(host, "systemctl is-active optimai")

    if error or output is None:
        return "down"

    if "active" in output:
        return "running"

    return "down"


def get_node_reward(host):
    output, error = run_ssh_command(host, "optimai-cli rewards balance")

    if error or output is None:
        return None

    return output
