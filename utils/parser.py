import re


def parse_reward(output):
    """
    Extract reward value from CLI output
    """

    if not output:
        return None

    try:
        match = re.search(r"Total rewards:\s*([0-9.]+)", output)

        if match:
            return float(match.group(1))

    except Exception as e:
        print(f"[PARSER ERROR] {e}")

    return None


def is_valid_output(output):
    if not output:
        return False

    if "Total rewards" in output:
        return True

    return False
