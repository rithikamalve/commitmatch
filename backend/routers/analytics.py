import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request

import db
from engagement.churn_detection import assess_churn_risk
from matching.blood_compat import ALL_BLOOD_GROUPS, is_compatible
from matching.chain_health import get_chain_health_summary
from models.schemas import (
    AnalyticsSupplyDemand, ChainHealthSummary, ChurnRiskDonor,
    NetworkHealth, ShortageAlert,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analytics/supply-demand", response_model=list[AnalyticsSupplyDemand])
async def supply_demand(request: Request):
    dl = request.app.state.data_loader
    donors_df   = dl.get_donors()
    patients_df = dl.get_patients()

    results = []
    for bg in ALL_BLOOD_GROUPS:
        eligible = donors_df[donors_df["blood_group"] == bg] if "blood_group" in donors_df.columns else donors_df.iloc[0:0]
        if "eligibility_status" in eligible.columns:
            elig_lower = eligible["eligibility_status"].str.lower()
            eligible_count = int((
                elig_lower.str.contains("eligible", na=False) &
                ~elig_lower.str.contains("not eligible", na=False) &
                ~elig_lower.str.contains("ineligible", na=False)
            ).sum())
        else:
            eligible_count = len(eligible)

        patient_count = int(patients_df["bridge_blood_group"].apply(
            lambda p: is_compatible(bg, p)
        ).sum()) if "bridge_blood_group" in patients_df.columns else 0

        results.append(AnalyticsSupplyDemand(
            blood_group=bg,
            eligible_donors=eligible_count,
            active_patients=patient_count,
            gap=max(0, patient_count - eligible_count),
        ))
    return results


@router.get("/analytics/churn-risk", response_model=list[ChurnRiskDonor])
async def churn_risk(request: Request):
    dl = request.app.state.data_loader
    donors_df = dl.get_donors()
    results = []

    for _, row in donors_df.iterrows():
        d = dl._row_to_dict(row)
        risk = assess_churn_risk(d)
        if not risk["should_reactivate"]:
            continue
        results.append(ChurnRiskDonor(
            donor_id=str(d.get("user_id", "")),
            donor_name=str(d.get("user_id", "")),
            blood_group=d.get("blood_group"),
            days_since_contact=risk["days_since_contact"],
            total_donations=int(d.get("donations_till_date") or 0),
            risk_level=risk["risk_level"],
            churn_reason=risk["reason"],
        ))

    results.sort(key=lambda x: x.days_since_contact, reverse=True)
    return results[:100]


@router.get("/analytics/chain-health", response_model=ChainHealthSummary)
async def chain_health(request: Request):
    summary = get_chain_health_summary(request.app.state.data_loader)
    chains = [
        {
            "patient_id":           c["patient_id"],
            "blood_group":          c.get("blood_group"),
            "status":               c["status"],
            "eligible_count":       c["eligible_count"],
            "at_risk_count":        c["at_risk_count"],
            "ineligible_count":     c["ineligible_count"],
            "total_donors_checked": c["total_donors_checked"],
            "needs_attention":      c["needs_attention"],
        }
        for c in summary["chains"]
    ]
    return ChainHealthSummary(
        total_chains=summary["total_chains"],
        critical=summary["critical"],
        warning=summary["warning"],
        healthy=summary["healthy"],
        needs_attention=summary["needs_attention"],
        chains=chains,
    )


@router.get("/analytics/shortage-alerts", response_model=list[ShortageAlert])
async def shortage_alerts():
    rows = db.scan_table("shortage_alerts", filter_fn=lambda r: not r.get("resolved"))
    rows.sort(key=lambda r: {"critical": 0, "medium": 1, "low": 2}.get(r.get("severity", "low"), 3))
    return [ShortageAlert(**{**r, "id": str(r.get("id", ""))}) for r in rows]


@router.get("/analytics/network-health", response_model=NetworkHealth)
async def network_health(request: Request):
    dl = request.app.state.data_loader
    donors_df = dl.get_donors()
    total = len(donors_df)

    if total == 0:
        return NetworkHealth(
            total_donors=0, pct_eligible=0, pct_active=0,
            pct_with_donation_history=0, pct_complete_profile=0,
            avg_commitment_score=0,
        )

    pct_eligible = 0.0
    if "eligibility_status" in donors_df.columns:
        eligible = donors_df["eligibility_status"].str.lower()
        pct_eligible = round(100 * (
            eligible.str.contains("eligible", na=False) &
            ~eligible.str.contains("not eligible", na=False) &
            ~eligible.str.contains("ineligible", na=False)
        ).sum() / total, 1)

    pct_active = 0.0
    if "user_donation_active_status" in donors_df.columns:
        # exact match only — "inactive" contains "active" as substring
        pct_active = round(100 * (
            donors_df["user_donation_active_status"].str.lower().str.strip() == "active"
        ).sum() / total, 1)

    pct_history = round(100 * donors_df.get("has_donation_history", False).sum() / total, 1) \
        if "has_donation_history" in donors_df.columns else 0.0

    has_bg  = donors_df["blood_group"].notna() if "blood_group" in donors_df.columns else [False] * total
    has_lat = donors_df["latitude"].notna()    if "latitude"    in donors_df.columns else [False] * total
    has_lon = donors_df["longitude"].notna()   if "longitude"   in donors_df.columns else [False] * total
    pct_complete = round(100 * (has_bg & has_lat & has_lon).sum() / total, 1)

    return NetworkHealth(
        total_donors=total,
        pct_eligible=pct_eligible,
        pct_active=pct_active,
        pct_with_donation_history=pct_history,
        pct_complete_profile=pct_complete,
        avg_commitment_score=0.0,
    )
