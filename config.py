import os

from dotenv import load_dotenv

load_dotenv()

# ========================
# VPS LIST (fallback lama)
# ========================
VPS_LIST = {
    "vps1": "root@IP_VPS_1",
    "vps2": "root@IP_VPS_2",
    "vps3": "root@IP_VPS_3",
}

# ========================
# INTERVAL & TIMEZONE
# ========================
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
REPORT_INTERVAL = int(os.getenv("REPORT_INTERVAL", "10800"))
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Asia/Jakarta")
