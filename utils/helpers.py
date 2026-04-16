def safe_int(value):
    try:
        return int(value)
    except:
        return 0


def get_status_icon(status):
    return "✅" if status == "running" else "❌"
