import os
from dotenv import load_dotenv

load_dotenv()

# ========================
# VPS LIST
# ========================
VPS_LIST = {
    "vps1": "root@IP_VPS_1",
    "vps2": "root@IP_VPS_2",
    "vps3": "root@IP_VPS_3",
    "vps4": "root@IP_VPS_4",
    "vps5": "root@IP_VPS_5"
}

# ========================
# INTERVAL
# ========================
CHECK_INTERVAL = 1800      # 30 menit
REPORT_INTERVAL = 10800    # 3 jam

# ========================
# TELEGRAM
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
