"""
Memory Retrieval — loads donor memory and surfaces it as context for
the AI layer (personalized outreach) and the prioritizer (show-rate signal).
"""
import db
from memory.store import get_memory


def get_dynamic_reliability_penalty(donor_id: str) -> float:
    """
    Returns a score multiplier (0.5–1.0) based on recent failure history.
    Each confirmed failure (decline or no_response) reduces trust in the score.
    3+ failures → score cut by 35%.  5+ → cut by 50%.
    """
    if not donor_id or not donor_id.strip():
        return 1.0
    failures = db.query_by_field("failure_log", "donor_id", donor_id)
    recent = [
        f for f in failures
        if f.get("failure_reason") in ("no_response", "declined")
    ]
    n = len(recent)
    if n >= 5: return 0.50
    if n >= 3: return 0.65
    if n >= 1: return 0.85
    return 1.0


def get_donor_context(donor_id: str) -> dict:
    """
    Returns a rich context dict for a donor, combining static profile
    with dynamic memory signals.

    Used by:
      - ai/outreach.py  → personalise message tone
      - matching/prioritizer.py → adjust reliability estimate
    """
    mem = get_memory(donor_id)
    show_rate = mem.get("lifetime_show_rate")

    context = {
        "donor_id":                  donor_id,
        "show_rate":                 show_rate,
        "show_rate_label":           _label(show_rate),
        "last_outcome":              mem.get("last_outcome"),
        "total_confirmations":       mem.get("total_confirmations", 0),
        "total_declines":            mem.get("total_declines", 0),
        "total_no_responses":        mem.get("total_no_responses", 0),
        "preferred_language":        mem.get("preferred_language", "Hindi"),
        "best_contact_time":         mem.get("best_contact_time", "unknown"),
        "notes":                     mem.get("notes", []),
        "is_first_contact":          mem.get("total_requests_sent", 0) == 0,
        "is_reliable":               show_rate is not None and show_rate >= 0.7,
        "is_at_risk":                show_rate is not None and show_rate < 0.3,
        # Live donation overrides — used by scoring engine to replace stale CSV values
        "last_donation_date_actual": mem.get("last_donation_date_actual"),
        "actual_donations":          mem.get("actual_donations", 0),
    }

    # Build a natural-language summary for the AI layer
    context["memory_summary"] = _summarize(context)
    return context


def _label(show_rate: float | None) -> str:
    if show_rate is None:         return "new donor"
    if show_rate >= 0.8:          return "highly reliable"
    if show_rate >= 0.6:          return "reliable"
    if show_rate >= 0.4:          return "moderately reliable"
    return "needs follow-up"


def _summarize(ctx: dict) -> str:
    if ctx["is_first_contact"]:
        return "First contact — no donation history with Blood Warriors yet."

    parts = []
    rate = ctx["show_rate"]
    if rate is not None:
        parts.append(f"Show rate {rate:.0%} ({ctx['show_rate_label']})")
    if ctx["total_confirmations"]:
        parts.append(f"{ctx['total_confirmations']} past donation(s)")
    if ctx["total_declines"]:
        parts.append(f"declined {ctx['total_declines']} time(s)")
    if ctx["last_outcome"]:
        parts.append(f"last outcome: {ctx['last_outcome']}")
    return "; ".join(parts) if parts else "No interaction history."
