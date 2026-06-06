"""
Donor Profile Enrichment — merges static CSV data with dynamic memory
into a single unified profile dict used across the system.
"""
from memory.retrieval import get_donor_context


def enrich_profile(donor: dict) -> dict:
    """
    Merges static donor data with live memory context.
    Returns a new dict — does not mutate the input.
    """
    uid = str(donor.get("user_id") or donor.get("donor_id") or "")
    ctx = get_donor_context(uid)
    profile = dict(donor)

    profile["memory"] = ctx

    # Promote key memory fields to top level for easy access in templates
    profile["lifetime_show_rate"]   = ctx["show_rate"]
    profile["show_rate_label"]      = ctx["show_rate_label"]
    profile["is_first_contact"]     = ctx["is_first_contact"]
    profile["is_reliable"]          = ctx["is_reliable"]
    profile["coordinator_notes"]    = ctx["notes"]
    profile["memory_summary"]       = ctx["memory_summary"]

    # Override preferred_language from memory if set
    if ctx.get("preferred_language"):
        profile["preferred_language"] = ctx["preferred_language"]

    # Override stale CSV values with live memory data where available.
    # These fields feed directly into the scoring signals on the next match.
    if ctx.get("last_donation_date_actual"):
        profile["last_donation_date"] = ctx["last_donation_date_actual"]
    if ctx.get("actual_donations", 0) > int(profile.get("total_donations") or 0):
        profile["donations_till_date"] = ctx["actual_donations"]
        profile["total_donations"]     = ctx["actual_donations"]

    return profile
