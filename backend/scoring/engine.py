import logging
from typing import Any

import pandas as pd

from scoring.blood_compat import is_compatible, normalize_blood_group
from scoring.signals import (
    SIGNAL_EXPLANATIONS,
    score_active_status,
    score_cycle_health,
    score_engagement,
    score_proximity,
    score_recency,
    score_reliability,
)

logger = logging.getLogger(__name__)

WEIGHTS = {
    "blood_compatibility": 0.25,
    "reliability":         0.25,
    "proximity":           0.20,
    "engagement":          0.10,
    "recency":             0.10,
    "cycle_health":        0.05,
    "active_status":       0.05,
}


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        import math
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def calculate_commitment_score(donor: dict, patient: dict) -> dict | None:
    donor_bg = normalize_blood_group(donor.get("blood_group"))
    patient_bg = normalize_blood_group(
        patient.get("bridge_blood_group") or patient.get("blood_group")
    )

    if not is_compatible(donor_bg, patient_bg):
        return None

    e_status = (donor.get("eligibility_status") or "").lower()
    if "ineligible" in e_status:
        return None

    proximity   = score_proximity(
        _safe_float(donor.get("latitude")),  _safe_float(donor.get("longitude")),
        _safe_float(patient.get("latitude")), _safe_float(patient.get("longitude")),
    )
    reliability = score_reliability(
        _safe_float(donor.get("calls_to_donations_ratio")),
        _safe_float(donor.get("total_calls")),
        _safe_float(donor.get("donations_till_date")),
    )
    engagement  = score_engagement(
        _safe_float(donor.get("cycle_of_donations")),
        donor.get("user_donation_active_status"),
    )
    recency     = score_recency(
        donor.get("last_donation_date"),
        donor.get("last_contacted_date"),
    )
    cycle_health = score_cycle_health(
        _safe_float(donor.get("cycle_of_donations")),
        _safe_float(donor.get("frequency_in_days")),
    )
    active_status = score_active_status(
        donor.get("user_donation_active_status"),
        donor.get("eligibility_status"),
    )

    signal_values = {
        "blood_compatibility": 100,
        "proximity":           proximity,
        "reliability":         reliability,
        "engagement":          engagement,
        "recency":             recency,
        "cycle_health":        cycle_health,
        "active_status":       active_status,
    }

    total_weight = sum(WEIGHTS[k] for k in signal_values)
    weighted_sum = sum(signal_values[k] * WEIGHTS[k] for k in signal_values)
    final_score  = round(weighted_sum / total_weight)

    human_explanations = _build_explanations(donor, signal_values)

    return {
        "score":                  final_score,
        "signals":                signal_values,
        "signal_explanations":    human_explanations,
        "donor_id":               str(donor.get("user_id", "")),
        "blood_group":            donor_bg,
        "eligibility_status":     donor.get("eligibility_status"),
        "next_eligible_date":     str(donor.get("next_eligible_date") or ""),
        "total_donations":        int(donor.get("donations_till_date") or 0),
        "calls_to_donations_ratio": _safe_float(donor.get("calls_to_donations_ratio")),
        "latitude":               _safe_float(donor.get("latitude")),
        "longitude":              _safe_float(donor.get("longitude")),
    }


def _build_explanations(donor: dict, signals: dict) -> dict[str, str]:
    ratio = _safe_float(donor.get("calls_to_donations_ratio"))
    dtd   = _safe_float(donor.get("donations_till_date"))
    cycle = _safe_float(donor.get("cycle_of_donations"))

    exps: dict[str, str] = {}

    exps["blood_compatibility"] = (
        f"Blood type {normalize_blood_group(donor.get('blood_group'))} is compatible"
    )

    if ratio is not None:
        exps["reliability"] = f"Calls-to-donation ratio: {ratio:.1f}"
    elif dtd is not None:
        exps["reliability"] = f"{int(dtd)} total donations — no ratio data"
    else:
        exps["reliability"] = "No donation history — estimated from engagement"

    exps["proximity"] = f"Score {signals['proximity']} — based on haversine distance"

    status = donor.get("user_donation_active_status", "")
    exps["engagement"] = f"Donation active status: {status}, cycle: {int(cycle or 0)}"

    exps["recency"]      = "Recent contact/donation activity score"
    exps["cycle_health"] = f"Cycle: {int(cycle or 0)}, frequency: {int(_safe_float(donor.get('frequency_in_days')) or 0)} days"
    exps["active_status"] = (
        f"Status: {donor.get('user_donation_active_status')} / {donor.get('eligibility_status')}"
    )

    return exps


def rank_donors_for_patient(
    donors_df: pd.DataFrame,
    patient: dict,
    top_n: int = 10,
) -> list[dict]:
    results = []
    for _, row in donors_df.iterrows():
        donor = row.to_dict()
        scored = calculate_commitment_score(donor, patient)
        if scored is not None:
            scored["donor_name"] = donor.get("name") or donor.get("user_id", "Unknown")
            scored["phone_number"] = donor.get("phone_number")
            scored["preferred_language"] = donor.get("preferred_language", "Hindi")
            scored["last_donation_date"] = str(donor.get("last_donation_date") or "")
            scored["last_contacted_date"] = str(donor.get("last_contacted_date") or "")
            scored["frequency_in_days"] = int(_safe_float(donor.get("frequency_in_days")) or 0)
            scored["cycle_of_donations"] = int(_safe_float(donor.get("cycle_of_donations")) or 0)
            scored["user_donation_active_status"] = donor.get("user_donation_active_status", "")
            results.append(scored)

    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:top_n]

    for i, item in enumerate(top):
        item["rank"]       = i + 1
        item["is_primary"] = i == 0
        item["is_standby"] = i == 1

    return top
