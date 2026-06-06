"""
Donor Memory Store — DynamoDB-backed.

Stores a running profile of every donor's interaction history so future
outreach and prioritization can improve over repeated contacts.

Each memory record (table: commitmatch_memory, PK: donor_id):
{
  "donor_id":             "...",
  "total_requests_sent":  int,
  "total_confirmations":  int,
  "total_declines":       int,
  "total_no_responses":   int,
  "total_hesitations":    int,
  "lifetime_show_rate":   float,   # confirmations / (requests where response expected)
  "preferred_language":   str,
  "best_contact_time":    str,     # "morning" | "evening" | "unknown"
  "last_outcome":         str,     # "confirmed" | "declined" | "no_response" | "hesitation"
  "last_request_id":      str,
  "last_updated":         str (ISO),
  "notes":                list[str],
}
"""
import logging
from datetime import datetime, timezone

import db

logger = logging.getLogger(__name__)

TABLE = "memory"


def get_memory(donor_id: str) -> dict:
    """Retrieve donor memory — returns empty record if first contact."""
    if not donor_id or not donor_id.strip():
        return _empty(donor_id)
    record = db.get_item(TABLE, donor_id, pk="donor_id")
    if not record:
        return _empty(donor_id)
    return record


def batch_get_memory(donor_ids: list[str]) -> dict[str, dict]:
    """Fetch multiple donor memories in ONE DynamoDB BatchGetItem call."""
    import time
    valid = [d for d in donor_ids if d and d.strip()]
    if not valid:
        return {}

    if not db._use_real_ddb():
        return {did: db._mem.get(TABLE, did, pk="donor_id") or _empty(did) for did in valid}

    t0 = time.monotonic()
    try:
        import boto3
        import config
        ddb  = boto3.resource("dynamodb", region_name=config.AWS_REGION)
        resp = ddb.batch_get_item(
            RequestItems={
                f"commitmatch_{TABLE}": {"Keys": [{"donor_id": did} for did in valid]}
            }
        )
        fetched = {
            item["donor_id"]: item
            for item in resp["Responses"].get(f"commitmatch_{TABLE}", [])
        }
        print(f"[DDB] batch_get_memory({len(valid)}) ✓ {int((time.monotonic()-t0)*1000)}ms — {len(fetched)} found")
        return {did: fetched.get(did, _empty(did)) for did in valid}
    except Exception as e:
        print(f"[DDB] batch_get_memory ✗ {type(e).__name__}: {e} — falling back")
        logger.warning("batch_get_memory failed, using sequential: %s", e)
        return {did: get_memory(did) for did in valid}


def record_outcome(
    donor_id:   str,
    request_id: str,
    outcome:    str,   # "confirmed" | "declined" | "no_response" | "hesitation"
) -> dict:
    """
    Called after every resolved interaction.
    Updates lifetime metrics and returns the updated record.
    """
    mem = get_memory(donor_id)

    mem["total_requests_sent"]  = mem.get("total_requests_sent", 0) + 1
    mem["last_outcome"]         = outcome
    mem["last_request_id"]      = request_id
    mem["last_updated"]         = datetime.now(timezone.utc).isoformat()

    if outcome == "confirmed":
        mem["total_confirmations"] = mem.get("total_confirmations", 0) + 1
        # Track actual donation date and cumulative count for scoring overrides
        today = datetime.now(timezone.utc).date().isoformat()
        mem["last_donation_date_actual"] = today
        mem["actual_donations"]          = mem.get("actual_donations", 0) + 1
    elif outcome == "declined":
        mem["total_declines"] = mem.get("total_declines", 0) + 1
    elif outcome == "no_response":
        mem["total_no_responses"] = mem.get("total_no_responses", 0) + 1
    elif outcome == "hesitation":
        mem["total_hesitations"] = mem.get("total_hesitations", 0) + 1

    mem["lifetime_show_rate"] = _compute_show_rate(mem)

    db.put_item(TABLE, mem, pk="donor_id")
    return mem


def add_note(donor_id: str, note: str) -> None:
    """Add a coordinator freetext note to donor memory."""
    mem = get_memory(donor_id)
    notes = mem.get("notes", [])
    notes.append(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} — {note}")
    mem["notes"] = notes[-20:]  # keep last 20 notes
    db.put_item(TABLE, mem, pk="donor_id")


def _empty(donor_id: str) -> dict:
    return {
        "donor_id":            donor_id,
        "total_requests_sent": 0,
        "total_confirmations": 0,
        "total_declines":      0,
        "total_no_responses":  0,
        "total_hesitations":   0,
        "lifetime_show_rate":  None,
        "preferred_language":  "Hinglish",
        "best_contact_time":   "unknown",
        "last_outcome":        None,
        "last_request_id":     None,
        "last_updated":        None,
        "notes":               [],
    }


def _compute_show_rate(mem: dict) -> float | None:
    confirmed = mem.get("total_confirmations", 0)
    total     = mem.get("total_requests_sent", 0)
    if total == 0:
        return None
    return round(confirmed / total, 3)
