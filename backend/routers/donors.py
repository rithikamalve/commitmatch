import logging
from fastapi import APIRouter, HTTPException, Request

from engagement.scoring import evaluate_donor_priority
from matching.blood_compat import normalize_blood_group, is_compatible
from matching.prioritizer import score_donor
from memory.donor_profile import enrich_profile
from models.schemas import DonorScore, EngagementAssessment

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/donors/{donor_id}")
async def get_donor_profile(donor_id: str, request: Request):
    """Pure data — CSV fields + memory counters. No scoring, no Bedrock."""
    dl = request.app.state.data_loader
    donor = dl.get_donor_by_id(donor_id)
    if not donor:
        raise HTTPException(404, f"Donor {donor_id} not found")

    from memory.store import get_memory
    mem = get_memory(donor_id)

    csv_donations    = int(donor.get("donations_till_date") or 0)
    actual_donations = int(mem.get("actual_donations") or 0)

    def _date(v):
        if v is None: return None
        s = str(v)
        return s[:10] if len(s) >= 10 and s != "NaT" else None

    return {
        "donor_id":                   donor_id,
        "blood_group":                donor.get("blood_group"),
        "eligibility_status":         donor.get("eligibility_status"),
        "user_donation_active_status":donor.get("user_donation_active_status"),
        "total_donations":            csv_donations + actual_donations,
        "last_donation_date":         _date(donor.get("last_donation_date")),
        "next_eligible_date":         _date(donor.get("next_eligible_date")),
        "frequency_in_days":          donor.get("frequency_in_days"),
        "donor_type":                 donor.get("donor_type"),
        "role":                       donor.get("role"),
        "preferred_language":         mem.get("preferred_language") or donor.get("preferred_language") or "Hinglish",
        # Memory stats
        "lifetime_show_rate":         mem.get("lifetime_show_rate"),
        "total_confirmations":        int(mem.get("total_confirmations") or 0),
        "total_declines":             int(mem.get("total_declines") or 0),
        "total_no_responses":         int(mem.get("total_no_responses") or 0),
        "last_outcome":               mem.get("last_outcome"),
        "last_updated":               mem.get("last_updated"),
    }


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
        # Always use a compatible context — fall back to same blood group so score_donor never returns None
        patient = matching[0] if matching else {
            "bridge_blood_group": bg,
            "latitude": donor.get("latitude"),
            "longitude": donor.get("longitude"),
        }

    scored = score_donor(donor, patient)
    if scored is None:
        raise HTTPException(409, "Donor is ineligible or incompatible")

    enriched   = enrich_profile({**donor, **scored})
    engagement = evaluate_donor_priority(donor)

    # Combine CSV donation count with confirmed donations recorded through this system
    from memory.store import get_memory
    mem = get_memory(donor_id)
    csv_donations    = int(scored.get("total_donations") or 0)
    actual_donations = int(mem.get("actual_donations") or 0)

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
        total_donations=csv_donations + actual_donations,
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
