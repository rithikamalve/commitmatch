"""
Donor Prioritization Engine — Layer 2.

Predicts when a donor's next donation window opens and evaluates
their current engagement level. This is the renamed "Donation Rhythm Predictor"
reframed as a prioritization tool.

The output surfaces as a confidence badge on the dashboard and informs
whether a donor should be in the priority contact list this week.
"""
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


def evaluate_donor_priority(donor: dict) -> dict:
    """
    Returns a priority assessment for a donor:
    {
      ready_now: bool,
      window_open: bool,
      days_until_window: int | None,
      predicted_next_date: str | None,
      confidence: "high" | "medium" | "low" | "unknown",
      priority_label: "donate_now" | "window_soon" | "not_ready" | "unknown",
      reasoning: str,
    }
    """
    donations  = _safe_int(donor.get("donations_till_date"))
    frequency  = _safe_int(donor.get("frequency_in_days"))
    last_date  = _to_date(donor.get("last_donation_date"))
    today      = datetime.now(timezone.utc).date()

    e_status = (donor.get("eligibility_status") or "").lower()
    is_eligible = "eligible" in e_status and "ineligible" not in e_status

    # Without history we can only check eligibility flag
    if not donations or donations < 3 or not frequency or frequency == 0:
        if is_eligible:
            return {
                "ready_now":          True,
                "window_open":        True,
                "days_until_window":  0,
                "predicted_next_date": None,
                "confidence":         "low",
                "priority_label":     "donate_now",
                "reasoning":          "Eligible — no donation history to predict rhythm",
            }
        return {
            "ready_now":          False,
            "window_open":        False,
            "days_until_window":  None,
            "predicted_next_date": None,
            "confidence":         "unknown",
            "priority_label":     "unknown",
            "reasoning":          "Insufficient history and no eligibility flag",
        }

    if not last_date:
        return {
            "ready_now":          is_eligible,
            "window_open":        is_eligible,
            "days_until_window":  0 if is_eligible else None,
            "predicted_next_date": None,
            "confidence":         "low",
            "priority_label":     "donate_now" if is_eligible else "unknown",
            "reasoning":          "No last donation date — relying on eligibility flag",
        }

    predicted_next = last_date + timedelta(days=frequency)
    days_until     = (predicted_next - today).days
    window_open    = days_until <= 0 and is_eligible

    if donations >= 5:
        confidence = "high"
    elif donations >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    if window_open:
        label     = "donate_now"
        reasoning = f"Predicted window opened {abs(days_until)} day(s) ago — {confidence} confidence"
    elif days_until <= 7:
        label     = "window_soon"
        reasoning = f"Predicted window in {days_until} day(s) — {confidence} confidence"
    else:
        label     = "not_ready"
        reasoning = f"Next predicted window in {days_until} days"

    return {
        "ready_now":           window_open,
        "window_open":         days_until <= 0,
        "days_until_window":   days_until,
        "predicted_next_date": str(predicted_next),
        "confidence":          confidence,
        "priority_label":      label,
        "reasoning":           reasoning,
    }
