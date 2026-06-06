"""
7 deterministic signal functions.  Each returns int 0–100.
Every function catches all exceptions and returns a neutral fallback — never raises.
"""
import math
import logging
from datetime import datetime, date, timezone
from typing import Any



logger = logging.getLogger(__name__)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _to_date(v: Any) -> date | None:
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


def score_proximity(donor_lat, donor_lon, patient_lat, patient_lon) -> int:
    try:
        if any(v is None for v in (donor_lat, donor_lon, patient_lat, patient_lon)):
            return 50
        # Identical coords = placeholder/default value in dataset — no real proximity signal
        if float(donor_lat) == float(patient_lat) and float(donor_lon) == float(patient_lon):
            return 50
        r = math.radians
        lat1, lon1 = r(float(donor_lat)),  r(float(donor_lon))
        lat2, lon2 = r(float(patient_lat)), r(float(patient_lon))
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a  = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        km = 6371 * 2 * math.asin(math.sqrt(a))
        if km <=  2: return 100
        if km <=  5: return 85
        if km <= 10: return 70
        if km <= 20: return 50
        if km <= 50: return 30
        return 10
    except Exception:
        return 50


def score_reliability(calls_to_donations_ratio, total_calls, donations_till_date) -> int:
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


def score_engagement(donations_till_date, user_donation_active_status) -> int:
    # cycle_of_donations is a duration (90=quarterly), not a count — use donations_till_date
    try:
        status = (user_donation_active_status or "").lower().strip()
        base   = 50 if status == "active" or (status.startswith("active") and "inactive" not in status) else 0
        if donations_till_date is None:
            return base
        d = float(donations_till_date)
        if d >= 10: return min(100, base + 50)
        if d >= 5:  return min(100, base + 30)
        if d >= 1:  return min(100, base + 15)
        return base
    except Exception:
        return 30


def score_recency(last_donation_date, last_contacted_date) -> int:
    try:
        candidates = [x for x in (_to_date(last_donation_date), _to_date(last_contacted_date)) if x]
        if not candidates:
            return 20
        days = (_today() - max(candidates)).days
        if days <=  30: return 100
        if days <=  90: return 75
        if days <= 180: return 50
        if days <= 365: return 30
        return 15
    except Exception:
        return 20


def score_cycle_health(cycle_of_donations, frequency_in_days) -> int:
    try:
        if cycle_of_donations is not None and float(cycle_of_donations) < 0:
            return 10
        c = float(cycle_of_donations)  if cycle_of_donations  is not None else 0
        f = float(frequency_in_days)   if frequency_in_days   is not None else 0
        if c == 0 and f == 0:
            return 40
        base = 40
        if c > 0:         base += 30
        if 0 < f <= 90:   base += 30
        return min(100, base)
    except Exception:
        return 40


def score_donor_type(donor_type: str | None, role: str | None) -> int:
    """
    Bridge Donors are dedicated repeat donors — preferred for thalassemia patients.
    Guest/Emergency donors are one-time — still usable but lower baseline trust.
    Returns 100 for Bridge, 60 for unknown/other, 40 for Guest/Emergency.
    """
    try:
        dtype = (donor_type or "").lower().strip()
        role_ = (role or "").lower().strip()
        if "bridge" in dtype or "bridge" in role_:
            return 100
        if dtype in ("guest", "emergency") or role_ in ("guest", "emergency"):
            return 40
        return 60  # unknown — neutral
    except Exception:
        return 60


def score_active_status(user_donation_active_status, eligibility_status) -> int:
    try:
        s = (user_donation_active_status or "").lower().strip()
        e = (eligibility_status or "").lower()
        # "inactive" contains "active" as substring — must exclude it
        active   = s == "active" or (s.startswith("active") and "inactive" not in s)
        # "not eligible" contains "eligible" as substring — must exclude it
        eligible = "eligible" in e and "not eligible" not in e and "ineligible" not in e
        if active and eligible: return 100
        if active:              return 60
        if eligible:            return 40
        return 0
    except Exception:
        return 0
