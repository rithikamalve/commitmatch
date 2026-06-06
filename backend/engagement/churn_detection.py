"""
Churn Detection — identifies donors at risk of becoming inactive.

A donor is at churn risk if:
  - Last contact was >90 days ago, OR
  - Donation cycle is negative (missed commitments)

Risk levels:
  high   — >180 days silent OR cycle < -2
  medium — 90-180 days silent OR cycle < 0
  low    — <90 days silent, cycle ≥ 0 (not technically at risk, included for completeness)
"""
from datetime import datetime, timezone
from typing import Any


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        import math
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _today():
    return datetime.now(timezone.utc).date()


def _to_date(v: Any):
    try:
        import pandas as pd
        if pd.isnull(v):
            return None
    except (TypeError, ValueError):
        pass
    from datetime import datetime, date
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


def assess_churn_risk(donor: dict) -> dict:
    """
    Returns {risk_level, days_since_contact, reason, should_reactivate}.
    """
    today = _today()

    last_c = _to_date(donor.get("last_contacted_date"))
    last_d = _to_date(donor.get("last_donation_date"))
    most_recent = max((d for d in (last_c, last_d) if d), default=None)

    days_since = (today - most_recent).days if most_recent else -1
    cycle = _safe_float(donor.get("cycle_of_donations"))

    reasons = []
    if days_since > 365:
        reasons.append(f"No contact in {days_since} days")
    elif days_since > 180:
        reasons.append(f"Silent for {days_since} days")

    if cycle is not None and cycle < 0:
        reasons.append(f"Donation cycle dropped to {int(cycle)}")

    if days_since > 365 or (cycle is not None and cycle < -2):
        risk = "High"
    elif days_since > 180 or (cycle is not None and cycle < 0):
        risk = "Medium"
    elif days_since == -1:
        risk = "Unknown"
    else:
        risk = "Low"

    return {
        "risk_level":         risk,
        "days_since_contact": days_since,
        "reason":             "; ".join(reasons) if reasons else "Within normal contact window",
        "should_reactivate":  risk in ("High", "Medium"),
    }
