import json
import logging

import boto3
from botocore.exceptions import ClientError

import config

logger = logging.getLogger(__name__)

_mgmt_client = None


def _get_mgmt_client():
    global _mgmt_client
    if _mgmt_client is None and config.WEBSOCKET_ENDPOINT:
        # Management API uses https://, not wss://
        endpoint = (
            config.WEBSOCKET_ENDPOINT
            .replace("wss://", "https://")
            .replace("ws://", "http://")
        )
        _mgmt_client = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=endpoint,
            region_name=config.AWS_REGION,
        )
    return _mgmt_client


def push_event(event: dict, db=None) -> None:
    print(f"[WS] push_event type={event.get('type')} DEMO_MODE={config.DEMO_MODE}")
    if config.DEMO_MODE:
        logger.info("WS push (demo): %s", json.dumps(event))
        return

    client = _get_mgmt_client()
    if client is None:
        print(f"[WS] ✗ No WebSocket client — WEBSOCKET_ENDPOINT not set")
        logger.warning("WebSocket endpoint not configured — skipping push")
        return

    if db is None:
        import db as _db
        db = _db

    try:
        connections = db.scan_table("ws_connections")
        print(f"[WS] {len(connections)} active connection(s)")
    except Exception as e:
        print(f"[WS] ✗ Failed to fetch connections: {type(e).__name__}: {e}")
        logger.error("Failed to fetch WS connections: %s", e)
        return

    data = json.dumps(event).encode()
    stale = []
    for row in connections:
        cid = row.get("connection_id")
        if not cid:
            continue
        try:
            client.post_to_connection(ConnectionId=cid, Data=data)
        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                stale.append(cid)
            else:
                logger.warning("WS push failed for %s: %s", cid, e)

    for cid in stale:
        try:
            db.delete_item("ws_connections", cid, pk="connection_id")
        except Exception:
            pass
