"""
EventBridge trigger: daily at 09:00 IST (03:30 UTC).
Sends nudge messages to donors whose predicted donation window is within 7 days.
Loads donor data from S3 (no direct DB access to CSV needed).
"""
import io
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION     = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET  = os.environ.get("S3_BUCKET", "commitmatch-team074")
CSV_KEY    = os.environ.get("CSV_KEY", "Dataset_demo.csv")


def _load_donors():
    import pandas as pd
    s3  = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=S3_BUCKET, Key=CSV_KEY)
    df  = pd.read_csv(io.BytesIO(obj["Body"].read()), low_memory=False)
    donors = df[df["bridge_id"].isna()].copy()
    donors["last_donation_date"]  = pd.to_datetime(donors["last_donation_date"],  errors="coerce")
    donors["frequency_in_days"]   = pd.to_numeric(donors["frequency_in_days"],   errors="coerce")
    donors["donations_till_date"] = pd.to_numeric(donors["donations_till_date"], errors="coerce")
    return donors


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
        logger.error("WhatsApp failed: %s", e)
        return False


def _log_interaction(donor_id: str, message: str):
    ddb = boto3.resource("dynamodb", region_name=REGION)
    now = datetime.now(timezone.utc).isoformat()
    try:
        ddb.Table("commitmatch_interactions").put_item(Item={
            "id":           str(uuid.uuid4()),
            "donor_id":     donor_id,
            "direction":    "outbound",
            "message_body": message,
            "sentiment":    "nudge",
            "created_at":   now,
        })
    except Exception as e:
        logger.error("Failed to log interaction: %s", e)


def handler(event, context):
    today      = datetime.now(timezone.utc).date()
    demo_phone = os.environ.get("DEMO_PHONE_1", "")
    nudged     = 0

    try:
        donors = _load_donors()
    except Exception as e:
        logger.error("Failed to load CSV from S3: %s", e)
        return {"nudged": 0}

    # Candidates: 3+ donations, known cycle, recent donation date
    candidates = donors[
        (donors["donations_till_date"] >= 3) &
        (donors["frequency_in_days"] > 0) &
        (donors["last_donation_date"].notna())
    ]
    logger.info("Evaluating %d donor candidates", len(candidates))

    for _, row in candidates.iterrows():
        try:
            freq = int(row["frequency_in_days"])
            last_dt = row["last_donation_date"]
            last = last_dt.date() if hasattr(last_dt, "date") else None
            if not last:
                continue

            predicted_next = last + timedelta(days=freq)
            days_until     = (predicted_next - today).days

            if not (0 <= days_until <= 7):
                continue

            donor_id = str(row.get("user_id", ""))
            lang     = str(row.get("preferred_language", "Hindi")).lower()
            name     = f"Donor #{donor_id[:6]}" if donor_id else "Donor"

            if lang == "hindi":
                message = (
                    f"Namaste {name} ji! Aapka donation window aane wala hai "
                    f"({days_until} din mein). Blood Warriors ko aapki zaroorat hai. "
                    "Kya aap ready hain? Reply HAAN karein."
                )
            else:
                message = (
                    f"Hello {name}! Your donation window is coming up "
                    f"in {days_until} day(s). Blood Warriors needs you. "
                    "Reply YES if you're ready."
                )

            # Send to demo phone (dataset has no real phone numbers)
            if demo_phone and _send_whatsapp(demo_phone, message):
                _log_interaction(donor_id, message)
                nudged += 1
                logger.info("Nudged %s (window in %d days)", donor_id[:8], days_until)

        except Exception as e:
            logger.error("Error processing donor %s: %s", row.get("user_id", "?"), e)

    logger.info("Rhythm nudger complete: %d nudges sent", nudged)
    return {"nudged": nudged}
