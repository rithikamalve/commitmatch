import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import Response

import config
import db
from ai.outreach import detect_hesitation, generate_outreach_message
from learning.feedback import (
    record_confirmation, record_decline,
    record_hesitation, record_no_response,
)
from messaging.whatsapp import send_whatsapp
from orchestration.request_lifecycle import transition
from websocket.push import push_event

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    data = dict(form)

    # Twilio sends status callbacks (sent/delivered/read) to the same URL — ignore them
    if data.get("MessageStatus") or not data.get("Body", "").strip():
        return Response(content="<Response></Response>", media_type="text/xml")

    from_number = data.get("From", "")
    body        = data.get("Body", "").strip()
    phone_plain = from_number.replace("whatsapp:", "").strip()

    logger.info("WA inbound from %s: %s", phone_plain, body)

    result      = detect_hesitation(body)
    sentiment   = result.get("sentiment", "unclear")
    now         = datetime.now(timezone.utc).isoformat()

    # Find open ranking — try by phone first, fall back to most recent open request
    all_donors = request.app.state.data_loader.get_donors()
    ranking = None
    donor_id = ""
    request_id = ""

    if "phone_number" in all_donors.columns:
        matching = all_donors[all_donors["phone_number"] == phone_plain]
        if not matching.empty:
            uid = str(matching.iloc[0].get("user_id", ""))
            open_rankings = sorted(
                [r for r in db.query_by_field("rankings", "donor_id", uid)
                 if r.get("outreach_status") in ("sent", "pending", "ready_to_send")],
                key=lambda r: r.get("created_at", ""), reverse=True,
            )
            if open_rankings:
                ranking    = open_rankings[0]
                donor_id   = uid
                request_id = str(ranking.get("request_id", ""))

    # Fallback: match to most recent awaiting_response request (covers demo — no phone data in CSV)
    if not ranking:
        open_reqs = sorted(
            [r for r in db.scan_table("requests")
             if r.get("lifecycle_state") == "awaiting_response"],
            key=lambda r: r.get("created_at", ""), reverse=True,
        )
        if open_reqs:
            request_id = open_reqs[0]["id"]
            primary = next(
                (r for r in db.query_by_field("rankings", "request_id", request_id)
                 if r.get("is_primary")
                 and r.get("outreach_status") in ("sent", "pending", "ready_to_send")),
                None,
            )
            if primary:
                ranking  = primary
                donor_id = str(primary.get("donor_id", ""))
                logger.info("Matched reply to most recent open request %s (demo fallback)", request_id[:8])

    # Log inbound interaction — omit request_id if unknown (GSI key can't be NULL)
    interaction = {
        "donor_id":     donor_id or "unknown",
        "direction":    "inbound",
        "message_body": body,
        "sentiment":    sentiment,
        "created_at":   now,
    }
    if request_id:
        interaction["request_id"] = request_id
    db.put_item("interactions", interaction)

    if not ranking:
        logger.warning("No open ranking for phone %s", phone_plain)
        return Response(content="<Response></Response>", media_type="text/xml")

    auto_reply = ""

    if sentiment == "confirmed":
        db.update_item("rankings", ranking["id"], {
            "outreach_status": "confirmed", "response_received_at": now,
        })
        db.update_item("requests", request_id, {
            "matched_donor_id": donor_id, "status": "confirmed", "updated_at": now,
        })
        record_confirmation(donor_id, request_id)
        transition(request_id, "confirmed", {"donor_id": donor_id})
        push_event({"type": "confirmed", "request_id": request_id,
                    "donor_name": donor_id})
        auto_reply = (
            "Bahut shukriya! 🙏 Blood Warriors aapka intezaar karega. "
            "Hospital ka address aur details aapko jald bheje jaenge."
        )

    elif sentiment == "declined":
        print(f"\n[WEBHOOK] Donor {donor_id[:12]}... replied DECLINED for request {request_id[:8]}")
        db.update_item("rankings", ranking["id"], {
            "outreach_status": "declined",
            "donor_reply_raw": body,
            "response_received_at": now,
        })
        record_decline(donor_id, request_id,
                       predicted_score=ranking.get("commitment_score"))
        transition(request_id, "declined_promoting_standby", {"donor_id": donor_id})
        push_event({"type": "declined", "request_id": request_id,
                    "donor_name": donor_id})
        auto_reply = (
            "Koi baat nahi. Aapke samay ke liye dhanyavad. "
            "Jab bhi aap ready hon, Blood Warriors aapka swagat karega. 🙏"
        )
        _promote_standby(request_id, request.app.state.data_loader)

    elif sentiment == "hesitation":
        print(f"\n[WEBHOOK] Donor {donor_id[:12]}... HESITATION detected for request {request_id[:8]}")
        db.update_item("rankings", ranking["id"], {
            "outreach_status":     "amber",
            "hesitation_detected": True,
            "donor_reply_raw":     body,
            "response_received_at": now,
        })
        record_hesitation(donor_id, request_id)
        push_event({"type": "amber_alert", "request_id": request_id,
                    "donor_name": donor_id, "reply_text": body})
        auto_reply = (
            "Hum samajhte hain! Kya aap confirm kar sakte hain? "
            "Reply HAAN (yes) ya NAHI (no). Ek zyindagi aap par depend karti hai. 🙏"
        )
        _alert_standby_amber(request_id, request.app.state.data_loader)

    else:
        push_event({"type": "unclear", "request_id": request_id,
                    "donor_name": donor_id})
        auto_reply = (
            "Blood Warriors: Kya aap blood donate kar sakte hain? "
            "Reply HAAN ya NAHI."
        )

    if auto_reply:
        twiml = f"<Response><Message>{auto_reply}</Message></Response>"
    else:
        twiml = "<Response></Response>"

    return Response(content=twiml, media_type="text/xml")


def _promote_standby(request_id: str, data_loader) -> None:
    print(f"\n[STANDBY] ▶ Promoting standby for request {request_id[:8]}...")

    all_rankings = db.query_by_field("rankings", "request_id", request_id)
    print(f"[STANDBY]   Found {len(all_rankings)} rankings for this request")

    standby = next(
        (r for r in all_rankings
         if r.get("is_standby")
         and r.get("outreach_status") in ("pending", "ready_to_send", "amber_notified")),
        None,
    )
    if not standby:
        print(f"[STANDBY] ✗ No eligible standby found — all statuses: "
              f"{[r.get('outreach_status') for r in all_rankings]}")
        logger.warning("No standby for request %s", request_id)
        return

    standby_donor_id = str(standby.get("donor_id", ""))
    print(f"[STANDBY]   Standby donor: {standby_donor_id[:12]}... rank={standby.get('rank')}")

    # Load patient blood group for outreach message
    req        = db.get_item("requests", request_id)
    patient_bg = ""
    if req and req.get("patient_bridge_id"):
        p = data_loader.get_patient_by_id(req["patient_bridge_id"])
        if p:
            patient_bg = p.get("bridge_blood_group", "")
    print(f"[STANDBY]   Patient blood group: {patient_bg or '(unknown)'}")

    donor    = data_loader.get_donor_by_id(standby_donor_id)
    language = (donor or {}).get("preferred_language", "Hinglish") if donor else "Hinglish"
    message  = generate_outreach_message(
        donor or {"donor_id": standby_donor_id, "donor_name": f"Donor #{standby_donor_id[:6]}"},
        {"bridge_blood_group": patient_bg},
        language,
    )
    print(f"[STANDBY]   Outreach message ready ({len(message)} chars)")

    now = datetime.now(timezone.utc).isoformat()

    # Promote standby: mark as primary, update status
    db.update_item("rankings", standby["id"], {
        "outreach_status": "sent",
        "is_primary":      True,
        "outreach_sent_at": now,
    })
    db.update_item("requests", request_id, {
        "standby_donor_id": standby_donor_id,
        "updated_at":       now,
    })
    print(f"[STANDBY] ✓ DB updated — standby is now primary")

    # Send WhatsApp — use real phone if available, else demo phone
    phone = (donor or {}).get("phone_number") or config.DEMO_PHONE_1
    if phone:
        dest = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
        sent = send_whatsapp(dest, message, donor_id=standby_donor_id, request_id=request_id)
        print(f"[STANDBY] {'✓ WhatsApp sent' if sent else '✗ WhatsApp failed'} → {dest}")
    else:
        print(f"[STANDBY] ✗ No phone number — WhatsApp skipped")

    # Notify coordinator dashboard via WebSocket
    push_event({
        "type":           "standby_promoted",
        "request_id":     request_id,
        "new_donor_id":   standby_donor_id,
        "new_donor_name": f"Donor #{standby_donor_id[:6]}",
        "blood_group":    patient_bg,
        "message_preview": message[:60],
    })
    print(f"[STANDBY] ✓ Coordinator notified via WebSocket")


def _alert_standby_amber(request_id: str, data_loader) -> None:
    """
    When primary donor hesitates (amber), send a heads-up to the standby donor
    so they can be mentally prepared — without fully replacing the primary yet.
    """
    print(f"\n[AMBER]  ▶ Alerting standby donor for request {request_id[:8]}...")

    all_rankings = db.query_by_field("rankings", "request_id", request_id)
    standby = next(
        (r for r in all_rankings
         if r.get("is_standby") and r.get("outreach_status") in ("pending", "ready_to_send")),
        None,
    )
    if not standby:
        print(f"[AMBER]  ✗ No standby found")
        return

    standby_donor_id = str(standby.get("donor_id", ""))
    print(f"[AMBER]    Standby donor: {standby_donor_id[:12]}... rank={standby.get('rank')}")

    # Get patient blood group for context
    req        = db.get_item("requests", request_id)
    patient_bg = ""
    if req and req.get("patient_bridge_id"):
        p = data_loader.get_patient_by_id(req["patient_bridge_id"])
        if p:
            patient_bg = p.get("bridge_blood_group", "")

    donor    = data_loader.get_donor_by_id(standby_donor_id)
    language = (donor or {}).get("preferred_language", "Hinglish") if donor else "Hinglish"
    name     = f"Donor #{standby_donor_id[:6]}"

    if language.lower() == "hindi":
        message = (
            f"Namaste {name} ji, Blood Warriors yahan se hain. "
            f"Hume {patient_bg} blood ki zaroorat pad sakti hai. "
            "Abhi koi confirm nahi hua hai — kya aap ready rehenge? "
            "Agar haan, toh READY reply karein."
        )
    elif language.lower() == "hinglish":
        message = (
            f"Bhai {name}, Blood Warriors ki taraf se — "
            f"hume {patient_bg} blood donor ki zaroorat pad sakti hai thodi der mein. "
            "Abhi commitment nahi chahiye, bas ready raho. "
            "Reply karo READY agar available ho. 🙏"
        )
    else:
        message = (
            f"Hello {name}, this is Blood Warriors. "
            f"We may need a {patient_bg} blood donor soon. "
            "No commitment yet — but could you be on standby? "
            "Reply READY if yes."
        )

    # Mark standby as amber-notified so we don't double-message
    db.update_item("rankings", standby["id"], {
        "outreach_status": "amber_notified",
    })

    # Send WhatsApp
    phone = (donor or {}).get("phone_number") or config.DEMO_PHONE_1
    if phone:
        dest = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
        sent = send_whatsapp(dest, message, donor_id=standby_donor_id, request_id=request_id)
        print(f"[AMBER]  {'✓ Standby WhatsApp sent' if sent else '✗ WhatsApp failed'} → {dest}")
    else:
        print(f"[AMBER]  ✗ No phone — standby WhatsApp skipped")

    # Notify coordinator dashboard
    push_event({
        "type":            "standby_alerted",
        "request_id":      request_id,
        "standby_donor_id": standby_donor_id,
        "standby_name":    name,
        "blood_group":     patient_bg,
        "message_preview": message[:60],
    })
    print(f"[AMBER]  ✓ Coordinator notified — standby is on alert")
