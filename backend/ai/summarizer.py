"""
Case Summarizer — generates a concise natural-language summary of a blood request
for handoff between coordinators or for audit logs.
"""
import logging

logger = logging.getLogger(__name__)


def summarize_request(request: dict, ranked_donors: list[dict], timeline: list[dict]) -> str:
    """Returns a concise rule-based summary of a blood request. No Bedrock."""
    return _rule_based_summary(request, ranked_donors, timeline)


def _rule_based_summary(request: dict, ranked_donors: list, timeline: list) -> str:
    bg     = request.get("patient_blood_group", "unknown")
    status = request.get("status", "open")
    date   = request.get("required_date", "TBD")
    n      = len(ranked_donors)
    top    = ranked_donors[0] if ranked_donors else {}
    score  = top.get("commitment_score", "?")
    out    = top.get("outreach_status", "pending")
    events = len(timeline)

    return (
        f"Blood request for {bg} blood — required by {date}, currently {status}. "
        f"{n} compatible donors identified; top donor scored {score}. "
        f"Primary outreach status: {out}. "
        f"{events} interaction event(s) logged."
    )
