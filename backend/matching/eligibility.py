"""
Hard-gate checks run before any scoring.
A donor that fails eligibility is excluded entirely — not just penalised.
"""
from datetime import datetime, date, timezone
from typing import Any

from matching.blood_compat import is_compatible, normalize_blood_group


def _today():
    return datetime.now(timezone.utc).date()


def _to_date(v: Any):
    try:
        import pandas as pd
        if pd.isnull(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        import pandas as pd
        ts = pd.Timestamp(v)
        return None if pd.isnull(ts) else ts.date()
    except Exception:
        return None


def is_eligible(donor: dict, patient: dict) -> tuple[bool, str]:
    """
    Returns (eligible: bool, reason: str).
    reason is populated only when eligible=False.
    """
    donor_bg   = normalize_blood_group(donor.get("blood_group"))
    patient_bg = normalize_blood_group(
        patient.get("bridge_blood_group") or patient.get("blood_group")
    )

    # Gate 1: unknown blood type
    if not donor_bg:
        return False, "Blood type unknown — excluded from matching"

    # Gate 2: blood incompatibility
    if not is_compatible(donor_bg, patient_bg):
        return False, f"{donor_bg} cannot donate to {patient_bg}"

    # Gate 3: explicit ineligibility flag ("not eligible" or "ineligible")
    e_status = (donor.get("eligibility_status") or "").lower()
    if "not eligible" in e_status or "ineligible" in e_status:
        return False, f"Marked ineligible: {donor.get('eligibility_status')}"

    # Gate 4: next_eligible_date in the future
    ned = _to_date(donor.get("next_eligible_date"))
    if ned and ned > _today():
        days = (ned - _today()).days
        return False, f"Not eligible until {ned} ({days} days away)"

    return True, ""
