import re


def parse_reward(text):
    if not text:
        return None

    match = re.search(r"Total rewards\s*:\s*([0-9.]+)", text, re.IGNORECASE)

    if match:
        try:
            return float(match.group(1))
        except:
            return None

    return None
