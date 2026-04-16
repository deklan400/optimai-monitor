from datetime import datetime

LOG_FILE = "data/logs.txt"


def log(message):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{time}] {message}"

    # print ke terminal
    print(line)

    # simpan ke file
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass
