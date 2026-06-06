import logging
from fastapi import APIRouter, HTTPException, Request

from engagement.scoring import evaluate_donor_priority
from matching.blood_compat import normalize_blood_group, is_compatible
from matching.prioritizer import score_donor
from memory.donor_profile import enrich_profile
from models.schemas import DonorScore, EngagementAssessment

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/donors/{donor_id}/score", response_model=DonorScore)
async def get_donor_score(donor_id: str, request: Request):
    dl = request.app.state.data_loader
    donor = dl.get_donor_by_id(donor_id)
    if not donor:
        raise HTTPException(404, f"Donor {donor_id} not found")

    # Find a compatible patient for scoring context
    patients_df = dl.get_patients()
    if patients_df.empty:
        patient = {
            "bridge_blood_group": donor.get("blood_group"),
            "latitude": donor.get("latitude"),
            "longitude": donor.get("longitude"),
        }
    else:
        bg = donor.get("blood_group")
        matching = [
            dl.get_patient_by_id(str(r["bridge_id"]))
            for _, r in patients_df.iterrows()
            if is_compatible(bg, r.get("bridge_blood_group"))
        ]
        patient = matching[0] if matching else dl._row_to_dict(patients_df.iloc[0])

    scored = score_donor(donor, patient)
    if scored is None:
        raise HTTPException(409, "Donor is ineligible or incompatible")

    enriched   = enrich_profile({**donor, **scored})
    engagement = evaluate_donor_priority(donor)

    return DonorScore(
        donor_id=donor_id,
        commitment_score=scored["score"],
        confidence=scored.get("confidence", "low"),
        signals=scored["signals"],
        reasons=scored["reasons"],
        flags=scored["flags"],
        engagement=EngagementAssessment(**engagement),
        eligibility_status=donor.get("eligibility_status"),
        blood_group=donor.get("blood_group"),
        total_donations=scored.get("total_donations", 0),
        lifetime_show_rate=enriched.get("lifetime_show_rate"),
        memory_summary=enriched.get("memory_summary", ""),
    )


@router.get("/donors")
async def list_donors(request: Request, limit: int = 50, blood_group: str | None = None):
    dl = request.app.state.data_loader
    df = dl.get_donors()

    if blood_group:
        bg = normalize_blood_group(blood_group)
        df = df[df["blood_group"] == bg]

    records = []
    for _, row in df.head(limit).iterrows():
        d = dl._row_to_dict(row)
        records.append({
            "user_id":            str(d.get("user_id", "")),
            "blood_group":        d.get("blood_group"),
            "eligibility_status": d.get("eligibility_status"),
            "user_donation_active_status": d.get("user_donation_active_status"),
            "donations_till_date": d.get("donations_till_date"),
            "last_donation_date":  str(d.get("last_donation_date") or ""),
            "latitude":            d.get("latitude"),
            "longitude":           d.get("longitude"),
        })
    return records
