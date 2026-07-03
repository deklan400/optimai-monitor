import re

ASSIGNMENT_ID_RE = re.compile(
    r"assignment(?:id\s*[=:]\s*|\s+)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def parse_assignment_activity(text):
    """Parse journal OptimAI berdasarkan assignment ID unik."""
    states = {}

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = ASSIGNMENT_ID_RE.search(line)
        if not match:
            continue

        assignment_id = match.group(1).lower()
        lower = line.lower()
        state = states.setdefault(
            assignment_id,
            {
                "submitted": False,
                "failure_events": 0,
                "seen_events": 0,
            },
        )
        state["seen_events"] += 1

        if "submitted successfully" in lower or "successfully submitted" in lower:
            state["submitted"] = True

        assignment_failed = "assignment" in lower and (
            " failed" in lower or "rejected" in lower
        )
        submit_failed = "submit" in lower and (
            " failed" in lower or " error" in lower
        )
        crawl_failed = any(
            marker in lower
            for marker in (
                "crawl failed",
                "failed to crawl",
                "error crawling",
                "crawler error",
            )
        )

        if assignment_failed or submit_failed or crawl_failed:
            state["failure_events"] += 1

    submitted = sum(1 for state in states.values() if state["submitted"])
    failed = sum(
        1
        for state in states.values()
        if state["failure_events"] > 0 and not state["submitted"]
    )
    pending = sum(
        1
        for state in states.values()
        if not state["submitted"] and state["failure_events"] == 0
    )
    retried = sum(
        1
        for state in states.values()
        if state["failure_events"] > 0 and state["submitted"]
    )

    return {
        "available": True,
        "assignments": len(states),
        "submitted": submitted,
        "failed": failed,
        "pending": pending,
        "retried": retried,
    }
