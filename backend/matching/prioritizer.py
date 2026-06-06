"""
Donor Prioritization Engine — Layer 1.

Pure Python. No API calls. No LLM. Deterministic.
Ranks donors for a patient using 7 weighted signals.
"""
import logging
from typing import Any

import pandas as pd

import math

from matching.blood_compat import normalize_blood_group
from matching.eligibility import is_eligible
from matching.explainability import build_reasons, score_to_confidence
from matching.signals import (
    score_active_status, score_cycle_health, score_donor_type,
    score_engagement, score_proximity, score_recency, score_reliability,
)

logger = logging.getLogger(__name__)

# blood_compatibility is a hard gate (is_eligible), not a scoring signal — excluded here.
# proximity is mostly a placeholder in this dataset (95%+ share the same coords) — minimal weight.
# reliability and active_status have the most discriminating power given data coverage.
WEIGHTS = {
    "reliability":   0.30,  # most predictive; 80% null but heavily penalises no-data donors
    "active_status": 0.22,  # 100% data coverage; Active+eligible vs inactive vs ineligible
    "engagement":    0.13,  # active flag (100%) + donation count (20%)
    "cycle_health":  0.13,  # 100% data; 90-day cycle vs no established cycle
    "donor_type":    0.10,  # Bridge Donor vs Guest — loyalty and commitment tier
    "recency":       0.07,  # 20% have dates; low weight to avoid penalising unknown donors
    "proximity":     0.05,  # mostly placeholder coords; kept for real-distance cases
}


def _km_distance(lat1, lon1, lat2, lon2) -> float | None:
    try:
        if any(v is None for v in (lat1, lon1, lat2, lon2)):
            return None
        if float(lat1) == float(lat2) and float(lon1) == float(lon2):
            return None  # identical coords = placeholder, not real distance
        r = math.radians
        la1, lo1 = r(float(lat1)), r(float(lon1))
        la2, lo2 = r(float(lat2)), r(float(lon2))
        dlat, dlon = la2 - la1, lo2 - lo1
        a = math.sin(dlat/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
        return round(6371 * 2 * math.asin(math.sqrt(a)), 1)
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


def score_donor(donor: dict, patient: dict) -> dict | None:
    """
    Scores a single donor against a patient.
    Returns a rich dict or None if the donor is ineligible.
    """
    eligible, ineligible_reason = is_eligible(donor, patient)
    if not eligible:
        return None

    proximity     = score_proximity(
        _safe_float(donor.get("latitude")),  _safe_float(donor.get("longitude")),
        _safe_float(patient.get("latitude")), _safe_float(patient.get("longitude")),
    )
    reliability   = score_reliability(
        _safe_float(donor.get("calls_to_donations_ratio")),
        _safe_float(donor.get("total_calls")),
        _safe_float(donor.get("donations_till_date")),
    )
    engagement    = score_engagement(
        _safe_float(donor.get("donations_till_date")),
        donor.get("user_donation_active_status"),
    )
    recency       = score_recency(
        donor.get("last_donation_date"), donor.get("last_contacted_date"),
    )
    cycle_health  = score_cycle_health(
        _safe_float(donor.get("cycle_of_donations")),
        _safe_float(donor.get("frequency_in_days")),
    )
    active_status = score_active_status(
        donor.get("user_donation_active_status"),
        donor.get("eligibility_status"),
    )

    donor_type_score = score_donor_type(
        donor.get("donor_type"), donor.get("role")
    )

    signals = {
        "reliability":   reliability,
        "active_status": active_status,
        "engagement":    engagement,
        "cycle_health":  cycle_health,
        "donor_type":    donor_type_score,
        "recency":       recency,
        "proximity":     proximity,
    }

    total_weight = sum(WEIGHTS.values())
    final_score  = round(sum(signals[k] * WEIGHTS[k] for k in signals) / total_weight)

    explainability = build_reasons(donor, signals)

    return {
        "score":      final_score,
        "confidence": score_to_confidence(final_score),
        "signals":    signals,
        "reasons":    explainability["reasons"],
        "flags":      explainability["flags"],
        # Donor metadata
        "donor_id":                 str(donor.get("user_id", "")),
        "blood_group":              normalize_blood_group(donor.get("blood_group")),
        "eligibility_status":       donor.get("eligibility_status"),
        "next_eligible_date":       str(donor.get("next_eligible_date") or ""),
        "total_donations":          int(_safe_float(donor.get("donations_till_date")) or 0),
        "calls_to_donations_ratio": _safe_float(donor.get("calls_to_donations_ratio")),
        "latitude":                 _safe_float(donor.get("latitude")),
        "longitude":                _safe_float(donor.get("longitude")),
        "phone_number":             donor.get("phone_number"),
        "preferred_language":       donor.get("preferred_language", "Hindi"),
        "last_donation_date":       str(donor.get("last_donation_date") or ""),
        "last_contacted_date":      str(donor.get("last_contacted_date") or ""),
        "frequency_in_days":        int(_safe_float(donor.get("frequency_in_days")) or 0),
        "cycle_of_donations":       int(_safe_float(donor.get("cycle_of_donations")) or 0),
        "user_donation_active_status": donor.get("user_donation_active_status", ""),
        "donor_type":               donor.get("donor_type"),
        "role":                     donor.get("role"),
        "distance_km":              _km_distance(
            _safe_float(donor.get("latitude")),  _safe_float(donor.get("longitude")),
            _safe_float(patient.get("latitude")), _safe_float(patient.get("longitude")),
        ),
    }


def rank_donors_for_patient(
    donors_df: pd.DataFrame,
    patient: dict,
    top_n: int = 10,
) -> list[dict]:
    """
    Score all eligible donors, sort, then apply memory-based adjustments
    only to the top_n results — keeping the hot path free of DB calls.
    """
    from memory.retrieval import get_dynamic_reliability_penalty

    # Convert once — avoids repeated row.to_dict() inside the loop
    records = donors_df.to_dict("records")

    results = []
    for row in records:
        scored = score_donor(row, patient)
        if scored is None:
            continue
        uid = str(row.get("user_id", ""))
        scored["donor_name"] = row.get("name") or (f"Donor #{uid[:6]}" if uid else "Unknown")
        results.append(scored)

    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:top_n]

    # Batch fetch all memories in ONE DDB call instead of top_n sequential calls
    from memory.store import batch_get_memory
    from learning.feedback import get_memory_reliability_boost_from_mem

    donor_ids = [item["donor_id"] for item in top]
    memories  = batch_get_memory(donor_ids)

    for i, item in enumerate(top):
        item["rank"]       = i + 1
        item["is_primary"] = i == 0
        item["is_standby"] = i == 1

        donor_id = item["donor_id"]
        mem      = memories.get(donor_id, {})

        # Failure penalty (sequential scan — small table, acceptable)
        penalty = get_dynamic_reliability_penalty(donor_id)
        if penalty < 1.0:
            item["score"] = round(item["score"] * penalty)
            item["failure_penalty"] = penalty

        # Memory boost from pre-fetched memory — no extra DDB call
        boost = get_memory_reliability_boost_from_mem(mem)
        if boost != 1.0:
            item["score"] = min(100, round(item["score"] * boost))
            item["memory_boost"] = boost

        dist = item.get("distance_km")
        item["est_travel_min"] = round(dist / 30 * 60) if dist else None

        # Attach memory for enrich_profile to reuse — eliminates Step 3 DDB calls
        item["_memory"] = mem

    # Re-sort after memory adjustments in case boost/penalty changed order
    top.sort(key=lambda x: x["score"], reverse=True)
    for i, item in enumerate(top):
        item["rank"]       = i + 1
        item["is_primary"] = i == 0
        item["is_standby"] = i == 1

    return top
