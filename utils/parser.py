import re


def parse_reward(text):
    if not text:
        return None

    match = re.search(r"Total rewards:\s*([0-9.]+)", text)

    if match:
        try:
            return float(match.group(1))
        except:
            return None

    return None
