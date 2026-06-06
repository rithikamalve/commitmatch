"""
Request Lifecycle State Machine.

Tracks and transitions a blood request through its complete automated workflow:
  created → ranked → outreach_sent → awaiting_response
  → confirmed | declined_promoting_standby | escalated

Each transition writes to DB and pushes a real-time WebSocket event so the
dashboard shows the live automated workflow, not just isolated status fields.
"""
import logging
from datetime import datetime, timezone

import db
from websocket.push import push_event

logger = logging.getLogger(__name__)

STATES = [
    "created",
    "ranked",
    "outreach_sent",
    "awaiting_response",
    "confirmed",
    "declined_promoting_standby",
    "escalated",
]

RESPONSE_TIMEOUT_SECONDS = 4 * 3600  # 4 hours — matches standby_promoter Lambda


def transition(request_id: str, new_state: str, meta: dict | None = None) -> None:
    """Update lifecycle state on a request and broadcast via WebSocket."""
    if new_state not in STATES:
        logger.warning("Unknown lifecycle state '%s' for request %s", new_state, request_id)
        return

    updates = {
        "lifecycle_state":  new_state,
        "state_entered_at": datetime.now(timezone.utc).isoformat(),
    }
    if meta:
        updates.update(meta)

    db.update_item("requests", request_id, updates)

    push_event({
        "type":       "lifecycle_transition",
        "request_id": request_id,
        "state":      new_state,
        **(meta or {}),
    })
    logger.info("Request %s → %s", request_id, new_state)


def get_state(request_id: str) -> str:
    req = db.get_item("requests", request_id)
    return (req or {}).get("lifecycle_state", "created")


def is_terminal(state: str) -> bool:
    return state in ("confirmed", "escalated")


def get_lifecycle_summary(request_id: str) -> dict:
    """Returns the full lifecycle view for a request, used by the dashboard."""
    req = db.get_item("requests", request_id)
    if not req:
        return {}

    state = req.get("lifecycle_state", "created")
    state_idx = STATES.index(state) if state in STATES else 0

    return {
        "request_id":      request_id,
        "current_state":   state,
        "state_index":     state_idx,
        "total_states":    len(STATES),
        "progress_pct":    round(state_idx / (len(STATES) - 1) * 100),
        "is_terminal":     is_terminal(state),
        "states":          STATES,
        "state_entered_at": req.get("state_entered_at"),
    }
