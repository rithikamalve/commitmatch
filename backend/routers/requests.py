import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

import db
from ai.summarizer import summarize_request
from models.schemas import (
    BloodRequest, BloodRequestDetail, InteractionEntry, RankedDonor,
)
from websocket.push import push_event

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/requests", response_model=list[BloodRequest])
async def list_requests(request: Request):
    dl = request.app.state.data_loader
    all_requests = db.scan_table("requests", filter_fn=lambda r: r.get("status") != "cancelled")
    all_requests.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    result = []
    for r in all_requests:
        r_id = r["id"]

        # Get top-ranked donor
        rankings = db.query_by_field("rankings", "request_id", r_id)
        rankings.sort(key=lambda x: int(x.get("rank", 99)))

        top_row = rankings[0] if rankings else None
        has_amber = any(x.get("outreach_status") == "amber" for x in rankings)

        top_donor = None
        if top_row:
            signals = top_row.get("signal_breakdown")
            if isinstance(signals, str):
                try:
                    signals = json.loads(signals)
                except Exception:
                    signals = {}
            top_donor = RankedDonor(
                donor_id=top_row.get("donor_id", ""),
                rank=int(top_row.get("rank", 1)),
                commitment_score=int(top_row.get("commitment_score") or 0),
                confidence=top_row.get("confidence", "low"),
                is_primary=bool(top_row.get("is_primary")),
                is_standby=bool(top_row.get("is_standby")),
                outreach_status=top_row.get("outreach_status", "pending"),
                hesitation_detected=bool(top_row.get("hesitation_detected")),
                donor_reply_raw=top_row.get("donor_reply_raw"),
                signals=signals or {},
                reasons=top_row.get("reasons", []),
                flags=top_row.get("flags", []),
            )

        # Get patient blood group from data_loader
        patient_bg = None
        patient_id = r.get("patient_bridge_id")
        if patient_id:
            p = dl.get_patient_by_id(patient_id)
            if p:
                patient_bg = p.get("bridge_blood_group")

        result.append(BloodRequest(
            id=r_id,
            patient_bridge_id=patient_id,
            required_date=r.get("required_date"),
            status=r.get("status", "open"),
            notes=r.get("notes"),
            matched_donor_id=r.get("matched_donor_id"),
            standby_donor_id=r.get("standby_donor_id"),
            match_time_seconds=r.get("match_time_seconds"),
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at"),
            patient_blood_group=patient_bg,
            top_donor=top_donor,
            has_amber_alert=has_amber,
        ))
    return result


@router.get("/requests/{request_id}", response_model=BloodRequestDetail)
async def get_request_detail(request_id: str, request: Request):
    dl  = request.app.state.data_loader
    req = db.get_item("requests", request_id)
    if not req:
        raise HTTPException(404, "Request not found")

    rankings = db.query_by_field("rankings", "request_id", request_id)
    rankings.sort(key=lambda x: int(x.get("rank", 99)))

    interactions = db.query_by_field("interactions", "request_id", request_id)
    interactions.sort(key=lambda x: x.get("created_at", ""))

    patient_bg = None
    if req.get("patient_bridge_id"):
        p = dl.get_patient_by_id(req["patient_bridge_id"])
        if p:
            patient_bg = p.get("bridge_blood_group")

    ranked_donors = []
    for row in rankings[:10]:
        signals = row.get("signal_breakdown")
        if isinstance(signals, str):
            try:
                signals = json.loads(signals)
            except Exception:
                signals = {}
        ranked_donors.append(RankedDonor(
            donor_id=row.get("donor_id", ""),
            rank=int(row.get("rank", 1)),
            commitment_score=int(row.get("commitment_score") or 0),
            confidence=row.get("confidence", "low"),
            is_primary=bool(row.get("is_primary")),
            is_standby=bool(row.get("is_standby")),
            outreach_status=row.get("outreach_status", "pending"),
            hesitation_detected=bool(row.get("hesitation_detected")),
            donor_reply_raw=row.get("donor_reply_raw"),
            signals=signals or {},
            reasons=row.get("reasons", []),
            flags=row.get("flags", []),
        ))

    timeline = [
        InteractionEntry(
            id=str(i.get("id", "")),
            direction=i.get("direction", ""),
            message_body=i.get("message_body"),
            sentiment=i.get("sentiment"),
            created_at=i.get("created_at"),
        )
        for i in interactions
    ]

    blood_req = BloodRequest(
        id=request_id,
        patient_bridge_id=req.get("patient_bridge_id"),
        required_date=req.get("required_date"),
        status=req.get("status", "open"),
        notes=req.get("notes"),
        matched_donor_id=req.get("matched_donor_id"),
        standby_donor_id=req.get("standby_donor_id"),
        match_time_seconds=req.get("match_time_seconds"),
        created_at=req.get("created_at"),
        updated_at=req.get("updated_at"),
        patient_blood_group=patient_bg,
    )

    # Build AI case summary
    summary = summarize_request(
        {"status": req.get("status"), "patient_blood_group": patient_bg,
         "required_date": req.get("required_date")},
        [r.dict() for r in ranked_donors],
        [t.dict() for t in timeline],
    )

    return BloodRequestDetail(
        request=blood_req,
        ranked_donors=ranked_donors,
        timeline=timeline,
        ai_summary=summary,
    )


@router.post("/requests/{request_id}/confirm")
async def confirm_request(request_id: str, body: dict, request: Request):
    donor_id = body.get("donor_id")
    if not donor_id:
        raise HTTPException(400, "donor_id required")

    now = datetime.now(timezone.utc).isoformat()
    db.update_item("requests", request_id, {
        "status": "confirmed", "matched_donor_id": donor_id, "updated_at": now,
    })

    # Update the ranking
    rankings = db.query_by_field("rankings", "request_id", request_id)
    for row in rankings:
        if row.get("donor_id") == donor_id:
            db.update_item("rankings", row["id"], {"outreach_status": "confirmed"})
            break

    # Feedback loop
    from learning.feedback import record_confirmation
    record_confirmation(donor_id, request_id)

    push_event({"type": "confirmed", "request_id": request_id, "donor_name": donor_id})
    return {"status": "confirmed", "request_id": request_id, "donor_id": donor_id}
