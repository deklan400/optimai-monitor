from datetime import datetime


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds):
    minutes = seconds // 60
    return f"{minutes} menit"
