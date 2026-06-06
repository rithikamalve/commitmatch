from datetime import datetime, timedelta, timezone
from typing import Any


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        f = float(v)
        import math
        return None if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return None


def _to_date(v: Any):
    if v is None:
        return None
    try:
        import pandas as pd
        ts = pd.Timestamp(v)
        return None if pd.isnull(ts) else ts.date()
    except Exception:
        return None


class DonationRhythmPredictor:
    def predict(self, donor: dict) -> dict:
        donations = _safe_int(donor.get("donations_till_date"))
        frequency = _safe_int(donor.get("frequency_in_days"))
        last_date = _to_date(donor.get("last_donation_date"))

        if not donations or donations < 3 or not frequency or frequency == 0:
            return {
                "rhythm_available": False,
                "reason": "insufficient_history",
            }

        if not last_date:
            return {
                "rhythm_available": False,
                "reason": "no_last_donation_date",
            }

        predicted_next = last_date + timedelta(days=frequency)
        today = datetime.now(timezone.utc).date()
        days_until = (predicted_next - today).days

        if donations >= 5:
            confidence = "high"
        elif donations >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "rhythm_available":     True,
            "predicted_next_date":  str(predicted_next),
            "days_until_window":    days_until,
            "confidence":           confidence,
            "donations_till_date":  donations,
            "frequency_in_days":    frequency,
        }
