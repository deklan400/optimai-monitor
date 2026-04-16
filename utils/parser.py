import re

def parse_reward(output):
    """
    Extract number from:
    Total rewards: 28945.55
    """

    if not output:
        return None

    match = re.search(r"Total rewards:\s*([0-9.]+)", output)

    if match:
        return float(match.group(1))

    return None
