import math
import logging
from datetime import datetime, date, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _to_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    try:
        import pandas as pd
        ts = pd.Timestamp(v)
        if pd.isnull(ts):
            return None
        return ts.date()
    except Exception:
        return None


def score_proximity(
    donor_lat: float | None,
    donor_lon: float | None,
    patient_lat: float | None,
    patient_lon: float | None,
) -> int:
    try:
        if any(v is None for v in (donor_lat, donor_lon, patient_lat, patient_lon)):
            return 50

        lat1, lon1 = math.radians(donor_lat), math.radians(donor_lon)
        lat2, lon2 = math.radians(patient_lat), math.radians(patient_lon)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        km = 6371 * 2 * math.asin(math.sqrt(a))

        if km <= 2:   return 100
        if km <= 5:   return 85
        if km <= 10:  return 70
        if km <= 20:  return 50
        if km <= 50:  return 30
        return 10
    except Exception:
        return 50


def score_reliability(
    calls_to_donations_ratio: float | None,
    total_calls: float | None,
    donations_till_date: float | None,
) -> int:
    try:
        if calls_to_donations_ratio is not None:
            r = float(calls_to_donations_ratio)
            if r <= 1.0: return 100
            if r <= 1.5: return 85
            if r <= 2.5: return 65
            if r <= 4.0: return 45
            if r <= 6.0: return 25
            return 10

        if donations_till_date is not None:
            d = float(donations_till_date)
            if d >= 3: return 60
            if d >= 1: return 40
            return 30

        return 30
    except Exception:
        return 30


def score_engagement(
    cycle_of_donations: float | None,
    user_donation_active_status: str | None,
) -> int:
    try:
        status = (user_donation_active_status or "").lower()
        base = 50 if "active" in status else 0

        if cycle_of_donations is None:
            return base

        c = float(cycle_of_donations)
        if c < 0:
            return max(0, base - 20)
        if c > 10:
            return min(100, base + 50)
        if c > 3:
            return min(100, base + 30)
        if c > 0:
            return min(100, base + 15)
        return base
    except Exception:
        return 30


def score_recency(
    last_donation_date: Any,
    last_contacted_date: Any,
) -> int:
    try:
        d1 = _to_date(last_donation_date)
        d2 = _to_date(last_contacted_date)

        candidates = [x for x in (d1, d2) if x is not None]
        if not candidates:
            return 20

        most_recent = max(candidates)
        days_ago = ((_today()) - most_recent).days

        if days_ago <= 30:  return 100
        if days_ago <= 90:  return 75
        if days_ago <= 180: return 50
        if days_ago <= 365: return 30
        return 15
    except Exception:
        return 20


def score_cycle_health(
    cycle_of_donations: float | None,
    frequency_in_days: float | None,
) -> int:
    try:
        if cycle_of_donations is not None and float(cycle_of_donations) < 0:
            return 10

        c = float(cycle_of_donations) if cycle_of_donations is not None else 0
        f = float(frequency_in_days) if frequency_in_days is not None else 0

        if c == 0 and f == 0:
            return 40

        base = 40
        if c > 0:
            base += 30
        if 0 < f <= 90:
            base += 30
        return min(100, base)
    except Exception:
        return 40


def score_active_status(
    user_donation_active_status: str | None,
    eligibility_status: str | None,
) -> int:
    try:
        s = (user_donation_active_status or "").lower()
        e = (eligibility_status or "").lower()

        is_active = "active" in s
        is_eligible = "eligible" in e and "ineligible" not in e

        if is_active and is_eligible: return 100
        if is_active:                 return 60
        if is_eligible:               return 40
        return 0
    except Exception:
        return 0


SIGNAL_EXPLANATIONS: dict[str, str] = {
    "blood_compatibility": "Donor blood type is compatible with patient",
    "proximity":           "Geographic distance between donor and patient",
    "reliability":         "Calls-to-donations ratio — how reliably donor shows up",
    "engagement":          "Donation cycle activity and active-status signal",
    "recency":             "Days since last donation or contact",
    "cycle_health":        "Donation cycle regularity and frequency",
    "active_status":       "Current eligibility and active-donation status",
}
