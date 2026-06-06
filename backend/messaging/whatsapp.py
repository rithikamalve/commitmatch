import logging
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

_twilio_client = None


def _get_twilio():
    global _twilio_client
    if _twilio_client is None:
        from twilio.rest import Client
        _twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    return _twilio_client


def send_whatsapp(
    to_number: str, message: str,
    donor_id: str = "", request_id: str = "",
) -> bool:
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        logger.info("WhatsApp (demo) → %s | %s", to_number, message[:60])
        _log(donor_id, request_id, "outbound", message, None)
        return True

    try:
        client = _get_twilio()
        msg = client.messages.create(
            from_=config.TWILIO_WHATSAPP_FROM, to=to_number, body=message
        )
        logger.info("WhatsApp sent SID=%s → %s", msg.sid, to_number)
        _log(donor_id, request_id, "outbound", message, None)
        return True
    except Exception as e:
        logger.error("Twilio send failed: %s", e)
        return False


def _log(donor_id, request_id, direction, body, sentiment):
    try:
        import db
        db.put_item("interactions", {
            "donor_id":    donor_id or None,
            "request_id":  request_id or None,
            "direction":   direction,
            "message_body": body,
            "sentiment":   sentiment,
            "created_at":  datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning("Failed to log interaction: %s", e)
