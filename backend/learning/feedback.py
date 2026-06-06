"""
Feedback Loop — closes the loop after every resolved interaction.

Flow:
  Request → Rank → Contact → Response → Outcome → Update Memory → Improve Future Ranking

This module is called:
  1. When a donor confirms       → record_confirmation()
  2. When a donor declines       → record_decline()
  3. When a donor doesn't respond→ record_no_response()
  4. When hesitation is detected → record_hesitation()
  5. When show-rate adjusts the  → apply_memory_boost()
     ranking on next match

Memory updates happen immediately in DynamoDB so the next
call to rank_donors_for_patient() benefits from real history.
"""
import logging
from datetime import datetime, timezone

import db
from memory.store import record_outcome

logger = logging.getLogger(__name__)


def record_confirmation(donor_id: str, request_id: str) -> None:
    """Donor confirmed. Update memory + mark failure log cleared."""
    mem = record_outcome(donor_id, request_id, "confirmed")
    logger.info(
        "Feedback [confirmed] donor=%s request=%s lifetime_show_rate=%.0f%%",
        donor_id, request_id,
        (mem.get("lifetime_show_rate") or 0) * 100,
    )


def record_decline(
    donor_id:        str,
    request_id:      str,
    predicted_score: int | None = None,
) -> None:
    """Donor declined. Log failure + update memory."""
    mem = record_outcome(donor_id, request_id, "declined")

    db.put_item("failure_log", {
        "request_id":      request_id,
        "donor_id":        donor_id,
        "failure_reason":  "declined",
        "predicted_score": predicted_score,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        "Feedback [declined] donor=%s request=%s lifetime_show_rate=%.0f%%",
        donor_id, request_id,
        (mem.get("lifetime_show_rate") or 0) * 100,
    )


def record_no_response(
    donor_id:        str,
    request_id:      str,
    predicted_score: int | None = None,
) -> None:
    """4-hour timeout — no response received."""
    mem = record_outcome(donor_id, request_id, "no_response")

    db.put_item("failure_log", {
        "request_id":      request_id,
        "donor_id":        donor_id,
        "failure_reason":  "no_response",
        "predicted_score": predicted_score,
        "created_at":      datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        "Feedback [no_response] donor=%s request=%s lifetime_show_rate=%.0f%%",
        donor_id, request_id,
        (mem.get("lifetime_show_rate") or 0) * 100,
    )


def record_hesitation(donor_id: str, request_id: str) -> None:
    """Hesitation detected. Memory updated but no failure logged yet."""
    record_outcome(donor_id, request_id, "hesitation")
    logger.info("Feedback [hesitation] donor=%s request=%s", donor_id, request_id)


def get_memory_reliability_boost(donor_id: str) -> float:
    """
    Returns a multiplier (0.5–1.2) based on historical show-rate.
    Applied to the reliability signal score at ranking time.

    High history show-rate → bump reliability upward.
    Low history show-rate  → penalise reliability.
    """
    from memory.retrieval import get_donor_context
    ctx = get_donor_context(donor_id)
    show_rate = ctx.get("show_rate")

    if show_rate is None:
        return 1.0          # new donor — no adjustment
    if show_rate >= 0.85:
        return 1.2          # very reliable — boost
    if show_rate >= 0.7:
        return 1.1
    if show_rate >= 0.5:
        return 1.0
    if show_rate >= 0.3:
        return 0.85         # below-average — slight penalty
    return 0.7              # unreliable history — penalise
