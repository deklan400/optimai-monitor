import os
import subprocess


def _ensure_public_key():
    home = os.path.expanduser("~")
    key_path = os.path.join(home, ".ssh", "id_ed25519")
    pub_path = key_path + ".pub"

    if os.path.exists(pub_path):
        return pub_path

    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    result = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", key_path],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return None
    return pub_path


def setup_ssh_key_with_password(host, password):
    pub_path = _ensure_public_key()
    if not pub_path:
        return False, "Gagal membuat SSH key di VPS monitor."

    # Install public key ke node target menggunakan password sementara.
    command = [
        "sshpass",
        "-p",
        password,
        "ssh-copy-id",
        "-i",
        pub_path,
        "-o",
        "StrictHostKeyChecking=no",
        host,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=25,
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout saat setup SSH key."
    except Exception as e:
        return False, f"Gagal eksekusi ssh-copy-id: {e}"

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if not err:
            err = "Setup SSH key gagal."
        return False, err

    return True, "SSH key berhasil dipasang."
