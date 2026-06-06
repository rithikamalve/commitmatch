"""
EventBridge trigger: every 30 minutes.
Promotes standby donor when primary has not responded in 4 hours.
"""
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "us-east-1")


def _ddb():
    return boto3.resource("dynamodb", region_name=REGION)


def _table(name):
    return _ddb().Table(f"commitmatch_{name}")


def _send_whatsapp(to_number: str, message: str) -> bool:
    try:
        from twilio.rest import Client
        client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        client.messages.create(
            from_=os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"),
            to=to_number,
            body=message,
        )
        return True
    except Exception as e:
        logger.error("WhatsApp send failed: %s", e)
        return False


def handler(event, context):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
    now    = datetime.now(timezone.utc).isoformat()
    promoted = 0

    rankings_table = _table("rankings")

    # Find primary donors who were sent outreach 4+ hours ago with no reply
    resp = rankings_table.scan(
        FilterExpression=(
            Attr("outreach_status").eq("sent") &
            Attr("is_primary").eq(True) &
            Attr("outreach_sent_at").lt(cutoff)
        )
    )
    stale = resp.get("Items", [])
    logger.info("Found %d stale primary rankings", len(stale))

    for ranking in stale:
        request_id = str(ranking.get("request_id", ""))
        donor_id   = str(ranking.get("donor_id", ""))
        ranking_id = str(ranking.get("id", ""))

        if not request_id:
            continue

        # Mark primary as no_response
        try:
            rankings_table.update_item(
                Key={"id": ranking_id},
                UpdateExpression="SET outreach_status = :s, updated_at = :u",
                ExpressionAttributeValues={":s": "no_response", ":u": now},
            )
        except Exception as e:
            logger.error("Failed to update ranking %s: %s", ranking_id[:8], e)
            continue

        # Log failure for the learning loop
        try:
            _table("failure_log").put_item(Item={
                "id":             str(uuid.uuid4()),
                "request_id":     request_id,
                "donor_id":       donor_id,
                "failure_reason": "no_response",
                "predicted_score": int(ranking.get("commitment_score") or 0),
                "created_at":     now,
            })
        except Exception as e:
            logger.error("Failed to log failure: %s", e)

        # Update request lifecycle to escalated
        try:
            _table("requests").update_item(
                Key={"id": request_id},
                UpdateExpression="SET lifecycle_state = :s, updated_at = :u",
                ExpressionAttributeValues={":s": "escalated", ":u": now},
            )
        except Exception as e:
            logger.error("Failed to update request lifecycle: %s", e)

        # Find the standby donor for this request
        resp2 = rankings_table.scan(
            FilterExpression=(
                Attr("request_id").eq(request_id) &
                Attr("is_standby").eq(True) &
                Attr("outreach_status").is_in(["pending", "ready_to_send"])
            )
        )
        standbys = resp2.get("Items", [])
        if not standbys:
            logger.warning("No standby for request %s", request_id[:8])
            continue

        standby = standbys[0]
        standby_id = str(standby.get("id", ""))

        # Promote standby to primary
        try:
            rankings_table.update_item(
                Key={"id": standby_id},
                UpdateExpression=(
                    "SET outreach_status = :s, is_primary = :p, "
                    "outreach_sent_at = :t, updated_at = :u"
                ),
                ExpressionAttributeValues={
                    ":s": "sent", ":p": True, ":t": now, ":u": now,
                },
            )
        except Exception as e:
            logger.error("Failed to promote standby: %s", e)
            continue

        # Send WhatsApp (demo phone — dataset has no real phone numbers)
        demo_phone = os.environ.get("DEMO_PHONE_1", "")
        if demo_phone:
            msg = (
                "Blood Warriors: Urgent blood donation needed! "
                "Kya aap donate kar sakte hain? Reply HAAN ya NAHI."
            )
            _send_whatsapp(demo_phone, msg)

        promoted += 1
        logger.info(
            "Promoted standby %s for request %s",
            str(standby.get("donor_id", ""))[:8],
            request_id[:8],
        )

    logger.info("Standby promoter complete: %d promotions", promoted)
    return {"promoted": promoted}
