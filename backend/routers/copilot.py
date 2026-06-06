"""
Coordinator Copilot — AI assistant endpoints for the coordinator dashboard.

Two surfaces:
  GET  /copilot/{request_id}   — contextual next-action suggestion for a request
  POST /copilot/chat           — freetext Q&A with full request context injected
"""
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import db
from ai.coordinator_copilot import suggest_next_action
from ai.outreach import _invoke

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────────────────────────

class CopilotSuggestion(BaseModel):
    action:    str
    reasoning: str
    urgency:   str


class ChatRequest(BaseModel):
    request_id: str
    message:    str


class ChatResponse(BaseModel):
    reply:   str
    context: str   # brief summary of what context was injected


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_context_block(req: dict, rankings: list[dict], interactions: list[dict]) -> str:
    top3 = sorted(rankings, key=lambda r: r.get("rank", 99))[:3]
    donors_text = "\n".join(
        f"  Rank {r.get('rank')}: score={r.get('commitment_score','?')}, "
        f"status={r.get('outreach_status','?')}, "
        f"hesitation={r.get('hesitation_detected', False)}"
        for r in top3
    )
    recent = sorted(interactions, key=lambda i: i.get("created_at", ""), reverse=True)[:5]
    timeline_text = "\n".join(
        f"  [{i.get('direction','?')}] {i.get('sentiment') or 'n/a'} — {i.get('message_body','')[:60]}"
        for i in recent
    ) or "  (no interactions yet)"

    return (
        f"Blood Request ID: {req.get('id','?')[:8]}...\n"
        f"Status: {req.get('status','?')} | Lifecycle: {req.get('lifecycle_state','?')}\n"
        f"Required date: {req.get('required_date','TBD')}\n"
        f"Patient blood group: {req.get('patient_blood_group','unknown')}\n\n"
        f"Top 3 ranked donors:\n{donors_text}\n\n"
        f"Recent interactions:\n{timeline_text}"
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/copilot/{request_id}", response_model=CopilotSuggestion)
async def copilot_suggestion(request_id: str, request: Request):
    """
    Returns the AI-recommended next action for a specific blood request.
    Useful for coordinators who are unsure what to do next.
    """
    req = db.get_item("requests", request_id)
    if not req:
        raise HTTPException(404, f"Request {request_id} not found")

    rankings     = db.query_by_field("rankings",     "request_id", request_id)
    interactions = db.query_by_field("interactions", "request_id", request_id)

    top_donor = next(
        (r for r in sorted(rankings, key=lambda r: r.get("rank", 99)) if r.get("is_primary")),
        rankings[0] if rankings else {},
    )

    # Fetch donor memory for the primary donor
    donor_memory = {}
    if top_donor.get("donor_id"):
        from memory.store import get_memory
        donor_memory = get_memory(top_donor["donor_id"])

    result = suggest_next_action(req, top_donor, donor_memory)
    return CopilotSuggestion(**result)


@router.post("/copilot/chat", response_model=ChatResponse)
async def copilot_chat(body: ChatRequest, request: Request):
    """
    Freetext Q&A with full request context injected.
    Coordinators (and judges) can ask anything about the current request.

    Examples:
      "Why was the top donor chosen?"
      "What should I do since the donor is hesitating?"
      "Who is the standby donor and how reliable are they?"
    """
    req = db.get_item("requests", body.request_id)
    if not req:
        raise HTTPException(404, f"Request {body.request_id} not found")

    rankings     = db.query_by_field("rankings",     "request_id", body.request_id)
    interactions = db.query_by_field("interactions", "request_id", body.request_id)

    context_block = _build_context_block(req, rankings, interactions)

    prompt = (
        "You are an AI assistant for Blood Warriors NGO coordinators. "
        "You have full visibility into the blood donation request below. "
        "Answer the coordinator's question clearly and concisely.\n\n"
        f"=== CURRENT REQUEST CONTEXT ===\n{context_block}\n"
        f"=== COORDINATOR QUESTION ===\n{body.message}\n\n"
        "Answer in 2–4 sentences. Be specific, factual, and actionable."
    )

    try:
        reply = _invoke(prompt, max_tokens=300)
    except Exception as e:
        logger.warning("Copilot chat Bedrock failed: %s", e)
        reply = (
            "I'm currently unable to reach the AI backend. "
            f"Based on the data: request is {req.get('lifecycle_state','unknown')}, "
            f"top donor outreach is {rankings[0].get('outreach_status','unknown') if rankings else 'n/a'}."
        )

    context_summary = (
        f"{len(rankings)} donors ranked, "
        f"{len(interactions)} interactions logged, "
        f"lifecycle={req.get('lifecycle_state','?')}"
    )

    return ChatResponse(reply=reply, context=context_summary)
