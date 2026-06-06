"""
Explainability engine — converts raw signal values into human-readable reasons.

Output format used by the API:
{
  "rank": 1,
  "score": 87,
  "reasons": [
    "Lives within 3 km of patient",
    "Donates reliably — 1 call per donation",
    "Eligible to donate today",
    "Active donor with 14 donation cycles"
  ],
  "flags": ["No recent contact in 200 days"]
}
"""
from typing import Any
from datetime import datetime, date, timezone


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


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        import math
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def build_reasons(donor: dict, signals: dict) -> dict:
    """
    Returns {reasons: list[str], flags: list[str]}.
    reasons = positive factors that support this donor.
    flags   = concerns a coordinator should be aware of.
    """
    reasons: list[str] = []
    flags:   list[str] = []

    # ── Blood (hard gate — always compatible if ranked) ────────────────────
    reasons.append(
        f"Blood type {donor.get('blood_group', '?')} is compatible with patient"
    )

    # ── Proximity ──────────────────────────────────────────────────────────
    prox = signals.get("proximity", 50)
    if prox >= 85:
        reasons.append("Lives within 5 km of patient — same neighbourhood")
    elif prox >= 70:
        reasons.append("Lives within 10 km — reachable within 30 minutes")
    elif prox == 50:
        pass  # neutral / placeholder coords — no proximity signal either way
    else:
        flags.append(f"Significant distance from patient — proximity score {prox}")

    # ── Reliability ────────────────────────────────────────────────────────
    ratio = _safe_float(donor.get("calls_to_donations_ratio"))
    dtd   = _safe_float(donor.get("donations_till_date"))
    rel   = signals.get("reliability", 30)

    if ratio is not None:
        if ratio <= 1.0:
            reasons.append(f"Perfect reliability — donates every time they are called (ratio {ratio:.1f})")
        elif ratio <= 1.5:
            reasons.append(f"High reliability — calls-to-donation ratio {ratio:.1f}")
        elif ratio <= 2.5:
            reasons.append(f"Moderate reliability — ratio {ratio:.1f} (donates most times)")
        else:
            flags.append(f"Low reliability — ratio {ratio:.1f} (needs multiple calls)")
    elif dtd is not None:
        if dtd >= 3:
            reasons.append(f"{int(dtd)} total donations — proven track record")
        elif dtd >= 1:
            reasons.append(f"{int(dtd)} donation(s) on record")
        else:
            flags.append("No previous donations — first-time probability unknown")
    else:
        flags.append("No donation history — score estimated from engagement signals")

    # ── Active status ──────────────────────────────────────────────────────
    act = signals.get("active_status", 0)
    elig = (donor.get("eligibility_status") or "").lower()
    status = (donor.get("user_donation_active_status") or "").lower()

    if act == 100:
        reasons.append("Active donor and currently eligible to donate")
    elif act == 60:
        reasons.append("Donor is active")
        if "ineligible" in elig:
            flags.append(f"Marked ineligible: {donor.get('eligibility_status')}")
    elif act == 40:
        reasons.append("Eligible to donate")
        flags.append("Donor status not marked active — may need confirmation")
    else:
        flags.append("Not marked active or eligible — may require outreach to confirm availability")

    # ── Engagement ─────────────────────────────────────────────────────────
    dtd_eng = _safe_float(donor.get("donations_till_date"))
    eng     = signals.get("engagement", 30)

    if dtd_eng is not None and dtd_eng >= 1:
        if dtd_eng >= 10:
            reasons.append(f"Highly engaged donor — {int(dtd_eng)} recorded donations")
        elif dtd_eng >= 5:
            reasons.append(f"Regular donor — {int(dtd_eng)} recorded donations")
        else:
            reasons.append(f"{int(dtd_eng)} donation(s) on record")

    # ── Recency ────────────────────────────────────────────────────────────
    rec = signals.get("recency", 20)
    last_d = _to_date(donor.get("last_donation_date"))
    last_c = _to_date(donor.get("last_contacted_date"))
    most_recent = max((d for d in (last_d, last_c) if d), default=None)

    if most_recent:
        days = (_today() - most_recent).days
        if days <= 30:
            reasons.append(f"Recently active — last interaction {days} day(s) ago")
        elif days <= 90:
            reasons.append(f"Contacted within 3 months ({days} days ago)")
        elif days > 180:
            flags.append(f"Last contact was {days} days ago — may have become inactive")
    else:
        flags.append("No interaction history on record")

    # ── Cycle health ───────────────────────────────────────────────────────
    # cycle_of_donations = donation cycle duration in days (90 = quarterly, 0 = no cycle set)
    cycle_days = _safe_float(donor.get("cycle_of_donations"))
    cyc = signals.get("cycle_health", 40)
    if cycle_days and cycle_days > 0:
        reasons.append(f"Has an established {int(cycle_days)}-day donation cycle")

    return {"reasons": reasons, "flags": flags}


def score_to_confidence(score: int) -> str:
    if score >= 92: return "high"
    if score >= 80: return "medium"
    return "low"
