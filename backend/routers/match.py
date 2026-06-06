import json
import time
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

import db
import config
from ai.outreach import generate_outreach_message
from matching.prioritizer import rank_donors_for_patient
from memory.donor_profile import enrich_profile
from messaging.whatsapp import send_whatsapp
from models.schemas import LifecycleSummary, MatchRequest, MatchResponse, RankedDonor
from orchestration.request_lifecycle import transition, get_lifecycle_summary
from websocket.push import push_event

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/match", response_model=MatchResponse)
async def create_match(body: MatchRequest, request: Request, background_tasks: BackgroundTasks):
    print(f"\n{'='*60}")
    print(f"[MATCH] ▶ New request — patient_id={body.patient_id}")
    dl = request.app.state.data_loader

    print(f"[MATCH] Step 1: Looking up patient...")
    patient = dl.get_patient_by_id(body.patient_id)
    if not patient:
        print(f"[MATCH] ✗ Patient not found: {body.patient_id}")
        raise HTTPException(404, f"Patient {body.patient_id} not found")
    print(f"[MATCH] ✓ Patient found — blood group: {patient.get('bridge_blood_group')}")

    donors_df = dl.get_donors()
    if donors_df.empty:
        print(f"[MATCH] ✗ No donors loaded")
        raise HTTPException(503, "Donor data unavailable")
    print(f"[MATCH] ✓ {len(donors_df)} donors available in memory")

    print(f"[MATCH] Step 2: Running scoring engine on {len(donors_df)} donors...")
    t0 = time.monotonic()
    raw_ranked = rank_donors_for_patient(donors_df, patient, top_n=10)
    match_time_ms = int((time.monotonic() - t0) * 1000)
    print(f"[MATCH] ✓ Scoring done in {match_time_ms}ms — {len(raw_ranked)} donors ranked (top scores: {[r['score'] for r in raw_ranked[:3]]})")

    if not raw_ranked:
        print(f"[MATCH] ✗ No compatible donors found")
        raise HTTPException(404, "No compatible donors found")

    print(f"[MATCH] Step 3: Enriching donors with memory ({len(raw_ranked)} donors)...")
    t1 = time.monotonic()
    ranked = [enrich_profile(r) for r in raw_ranked]
    print(f"[MATCH] ✓ Memory enrichment done in {int((time.monotonic()-t1)*1000)}ms")
    print(f"[MATCH]   Top donor: {ranked[0].get('donor_name') or ranked[0]['donor_id'][:12]}... score={ranked[0]['score']}")

    print(f"[MATCH] Step 4: Persisting request to DB...")
    t2 = time.monotonic()
    request_id = db.put_item("requests", {
        "patient_bridge_id":  body.patient_id,
        "required_date":      str(body.required_date) if body.required_date else None,
        "status":             "open",
        "lifecycle_state":    "created",
        "notes":              body.notes,
        "match_time_seconds": match_time_ms // 1000,
        "created_at":         datetime.now(timezone.utc).isoformat(),
    })
    print(f"[MATCH] ✓ Request saved in {int((time.monotonic()-t2)*1000)}ms — id={request_id[:8]}...")
    transition(request_id, "ranked", {"donor_count": len(ranked)})

    print(f"[MATCH] Step 5: Persisting {len(ranked)} rankings to DB (batch)...")
    t3 = time.monotonic()
    import uuid as _uuid
    primary_ranking_id = str(_uuid.uuid4())   # pre-generate so we can update without a query
    ranking_items = []
    for r in ranked:
        item = {
            "request_id":       request_id,
            "donor_id":         r["donor_id"],
            "rank":             r["rank"],
            "commitment_score": r["score"],
            "signal_breakdown": json.dumps(r.get("signals", {})),
            "reasons":          r.get("reasons", []),
            "flags":            r.get("flags", []),
            "is_primary":       r["is_primary"],
            "is_standby":       r["is_standby"],
            "outreach_status":  "pending",
        }
        if r["is_primary"]:
            item["id"] = primary_ranking_id
        ranking_items.append(item)
    db.batch_write_items("rankings", ranking_items)
    print(f"[MATCH] ✓ Rankings saved in {int((time.monotonic()-t3)*1000)}ms")

    top      = ranked[0]
    language = top.get("preferred_language", "Hinglish")

    # Steps 6-7 (Bedrock + WhatsApp) run in background — don't block the HTTP response
    background_tasks.add_task(
        _outreach_background,
        top=top, patient=patient, language=language,
        request_id=request_id, primary_ranking_id=primary_ranking_id,
    )

    ranked_donors = [
        _to_ranked_donor(r, "pending")
        for r in ranked
    ]

    total_ms = int((time.monotonic() - t0) * 1000)
    print(f"[MATCH] ✓ DONE (rankings saved) — total={total_ms}ms, request_id={request_id[:8]}...")
    print(f"[MATCH]   Outreach + WhatsApp running in background")
    print(f"{'='*60}\n")

    return MatchResponse(
        request_id=request_id,
        patient_id=body.patient_id,
        ranked_donors=ranked_donors,
        message_preview="",
        match_time_ms=match_time_ms,
    )


def _outreach_background(top: dict, patient: dict, language: str,
                          request_id: str, primary_ranking_id: str) -> None:
    """Runs after HTTP response is sent — Bedrock call + WhatsApp don't block the UI."""
    print(f"[BG] ▶ Outreach background starting for request {request_id[:8]}...")
    t0 = time.monotonic()
    message = generate_outreach_message(top, patient, language)
    print(f"[BG] ✓ Outreach message ready in {int((time.monotonic()-t0)*1000)}ms — {message[:60]}...")

    outreach_status = "ready_to_send"
    phone = top.get("phone_number") or config.DEMO_PHONE_1
    if phone and config.DEMO_WHATSAPP:
        dest = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
        sent = send_whatsapp(dest, message, donor_id=top["donor_id"], request_id=request_id)
        print(f"[BG] {'✓ WhatsApp sent' if sent else '✗ WhatsApp failed'} → {dest}")
        if sent:
            outreach_status = "sent"
            db.update_item("rankings", primary_ranking_id, {
                "outreach_status":  "sent",
                "outreach_sent_at": datetime.now(timezone.utc).isoformat(),
            })
    else:
        print(f"[BG] WhatsApp skipped (DEMO_WHATSAPP={config.DEMO_WHATSAPP})")

    transition(request_id, "outreach_sent", {"donor_id": top["donor_id"]})
    transition(request_id, "awaiting_response")

    push_event({
        "type":       "outreach_sent",
        "request_id": request_id,
        "donor_id":   top["donor_id"],
        "status":     outreach_status,
    })
    print(f"[BG] ✓ Done — total background time={int((time.monotonic()-t0)*1000)}ms")


def _to_ranked_donor(r: dict, outreach_status: str) -> RankedDonor:
    return RankedDonor(
        donor_id=r["donor_id"],
        donor_name=r.get("donor_name", ""),
        blood_group=r.get("blood_group"),
        rank=r["rank"],
        commitment_score=r["score"],
        confidence=r.get("confidence", "low"),
        is_primary=r["is_primary"],
        is_standby=r["is_standby"],
        latitude=r.get("latitude"),
        longitude=r.get("longitude"),
        eligibility_status=r.get("eligibility_status"),
        next_eligible_date=r.get("next_eligible_date"),
        total_donations=r.get("total_donations", 0),
        calls_to_donations_ratio=r.get("calls_to_donations_ratio"),
        outreach_status=outreach_status,
        signals=r.get("signals", {}),
        reasons=r.get("reasons", []),
        flags=r.get("flags", []),
        phone_number=r.get("phone_number"),
        last_donation_date=r.get("last_donation_date"),
        frequency_in_days=r.get("frequency_in_days", 0),
        cycle_of_donations=r.get("cycle_of_donations", 0),
        user_donation_active_status=r.get("user_donation_active_status", ""),
        preferred_language=r.get("preferred_language", "Hinglish"),
        lifetime_show_rate=r.get("lifetime_show_rate"),
        memory_summary=r.get("memory_summary", ""),
        donor_type=r.get("donor_type"),
        role=r.get("role"),
        distance_km=r.get("distance_km"),
        est_travel_min=r.get("est_travel_min"),
    )


@router.get("/match/{request_id}/lifecycle", response_model=LifecycleSummary)
async def lifecycle_status(request_id: str):
    summary = get_lifecycle_summary(request_id)
    if not summary:
        from fastapi import HTTPException
        raise HTTPException(404, f"Request {request_id} not found")
    return LifecycleSummary(**summary)
