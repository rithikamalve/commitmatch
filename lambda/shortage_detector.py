"""
EventBridge trigger: every 6 hours.
Detects blood group shortages from donor CSV and writes alerts to DynamoDB.
"""
import io
import json
import logging
import math
import os
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION    = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET = os.environ.get("S3_BUCKET", "commitmatch-team074")
CSV_KEY   = os.environ.get("CSV_KEY", "Dataset_demo.csv")

ALL_BLOOD_GROUPS = [
    "O Negative", "O Positive", "A Negative", "A Positive",
    "B Negative", "B Positive", "AB Negative", "AB Positive",
]
COMPATIBILITY_MAP = {
    "O Negative":  ["O Negative", "O Positive", "A Negative", "A Positive",
                    "B Negative", "B Positive", "AB Negative", "AB Positive"],
    "O Positive":  ["O Positive", "A Positive", "B Positive", "AB Positive"],
    "A Negative":  ["A Negative", "A Positive", "AB Negative", "AB Positive"],
    "A Positive":  ["A Positive", "AB Positive"],
    "B Negative":  ["B Negative", "B Positive", "AB Negative", "AB Positive"],
    "B Positive":  ["B Positive", "AB Positive"],
    "AB Negative": ["AB Negative", "AB Positive"],
    "AB Positive": ["AB Positive"],
}

SHORTAGE_THRESHOLD = 6    # fewer than 6 eligible donors → alert
RADIUS_KM          = 20
CITY_LAT           = 17.39   # Hyderabad
CITY_LON           = 78.47


def _haversine(lat1, lon1, lat2, lon2) -> float:
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, map(float, [lat1, lon1, lat2, lon2]))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371 * 2 * math.asin(math.sqrt(a))
    except Exception:
        return 9999.0


def _load_csv():
    import pandas as pd
    s3  = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=S3_BUCKET, Key=CSV_KEY)
    return pd.read_csv(io.BytesIO(obj["Body"].read()), low_memory=False)


def _push_ws(event_data: dict):
    endpoint = os.environ.get("WEBSOCKET_ENDPOINT", "")
    if not endpoint:
        return
    mgmt_url = endpoint.replace("wss://", "https://")
    try:
        ddb   = boto3.resource("dynamodb", region_name=REGION)
        conns = ddb.Table("commitmatch_ws_connections").scan().get("Items", [])
        client = boto3.client("apigatewaymanagementapi", endpoint_url=mgmt_url, region_name=REGION)
        for conn in conns:
            try:
                client.post_to_connection(
                    ConnectionId=conn["connection_id"],
                    Data=json.dumps(event_data).encode(),
                )
            except Exception:
                pass
    except Exception as e:
        logger.warning("WS push failed: %s", e)


def handler(event, context):
    import pandas as pd

    now            = datetime.now(timezone.utc).isoformat()
    alerts_created = 0

    try:
        df = _load_csv()
    except Exception as e:
        logger.error("Failed to load CSV from S3: %s", e)
        return {"alerts": 0}

    # Split donors and patients
    donors_df   = df[df["bridge_id"].isna()].copy()
    patients_df = df[df["bridge_id"].notna()].copy()

    donors_df["latitude"]  = pd.to_numeric(donors_df["latitude"],  errors="coerce")
    donors_df["longitude"] = pd.to_numeric(donors_df["longitude"], errors="coerce")
    donors_df["is_eligible"] = (
        donors_df["eligibility_status"].str.lower().str.contains("eligible", na=False) &
        ~donors_df["eligibility_status"].str.lower().str.contains("ineligible", na=False)
    )

    ddb           = boto3.resource("dynamodb", region_name=REGION)
    alerts_table  = ddb.Table("commitmatch_shortage_alerts")

    for bg in ALL_BLOOD_GROUPS:
        compatible = COMPATIBILITY_MAP.get(bg, [])

        # Count eligible donors of this blood group within radius of city center
        bg_donors = donors_df[
            (donors_df["blood_group"] == bg) &
            donors_df["is_eligible"] &
            donors_df["latitude"].notna() &
            donors_df["longitude"].notna()
        ]
        eligible_count = int(sum(
            1 for _, d in bg_donors.iterrows()
            if _haversine(d["latitude"], d["longitude"], CITY_LAT, CITY_LON) <= RADIUS_KM
        ))

        if eligible_count >= SHORTAGE_THRESHOLD:
            continue

        patient_count = int(patients_df[
            patients_df["bridge_blood_group"].isin(compatible)
        ].shape[0])

        severity = "critical" if eligible_count < 3 else "medium"

        try:
            alerts_table.put_item(Item={
                "id":                   str(uuid.uuid4()),
                "blood_group":          bg,
                "city_cluster":         "Hyderabad",
                "eligible_donor_count": eligible_count,
                "active_patient_count": patient_count,
                "severity":             severity,
                "resolved":             False,
                "created_at":           now,
            })
            _push_ws({
                "type":         "shortage_alert",
                "blood_group":  bg,
                "city_cluster": "Hyderabad",
                "donor_count":  eligible_count,
                "severity":     severity,
            })
            alerts_created += 1
            logger.info("Alert: %s — %d eligible donors (%s)", bg, eligible_count, severity)
        except Exception as e:
            logger.error("Failed to write alert for %s: %s", bg, e)

    logger.info("Shortage detector complete: %d alerts", alerts_created)
    return {"alerts": alerts_created}
