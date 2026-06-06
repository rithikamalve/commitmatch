"""
Coordinator Copilot — AI assistance for human coordinators.

Surfaces contextual recommendations based on current request state.
Does NOT make decisions. Surfaces options and surface risks.
"""
import json
import logging

import config

logger = logging.getLogger(__name__)


def _invoke(prompt: str, max_tokens: int = 400) -> str:
    import boto3
    from botocore.config import Config
    client = boto3.client(
        "bedrock-runtime",
        region_name=config.AWS_REGION,
        config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 1}),
    )
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    })
    resp = client.invoke_model(body=body, modelId=config.BEDROCK_MODEL_ID)
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]


def suggest_next_action(
    request: dict,
    top_donor: dict,
    donor_memory: dict,
) -> dict:
    """
    Given the current state of a blood request, suggest what the coordinator
    should do next. Returns {action, reasoning, urgency}.
    """
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _rule_based_suggestion(request, top_donor, donor_memory)

    try:
        status = request.get("status", "open")
        outreach = top_donor.get("outreach_status", "pending")
        hesitation = top_donor.get("hesitation_detected", False)
        req_date = request.get("required_date", "unknown")
        show_rate = donor_memory.get("lifetime_show_rate")
        score = top_donor.get("commitment_score", 0)

        prompt = (
            f"A blood coordinator is managing a blood donation request.\n\n"
            f"Request status: {status}\n"
            f"Required date: {req_date}\n"
            f"Top donor outreach status: {outreach}\n"
            f"Hesitation detected: {hesitation}\n"
            f"Donor commitment score: {score}\n"
            f"Donor historical show rate: {show_rate or 'unknown'}\n\n"
            "Suggest the single most important next action for the coordinator. "
            "Return JSON: {\"action\": \"<1 sentence>\", \"reasoning\": \"<2 sentences>\", \"urgency\": \"immediate|today|this_week\"}"
        )
        text = _invoke(prompt, max_tokens=200)
        start, end = text.find("{"), text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Copilot suggestion failed: %s", e)
        return _rule_based_suggestion(request, top_donor, donor_memory)


def _rule_based_suggestion(request: dict, top_donor: dict, donor_memory: dict) -> dict:
    outreach  = top_donor.get("outreach_status", "pending")
    hesitation = top_donor.get("hesitation_detected", False)
    score     = top_donor.get("commitment_score", 0)

    if hesitation:
        return {
            "action":    "Call donor directly — hesitation detected in WhatsApp reply",
            "reasoning": "The donor's reply contained soft-cancel language. A phone call resolves hesitation faster than text.",
            "urgency":   "immediate",
        }
    if outreach == "no_response":
        return {
            "action":    "Promote standby donor — primary has not responded",
            "reasoning": "4-hour window elapsed with no response. Standby donor is pre-ranked and ready to contact.",
            "urgency":   "immediate",
        }
    if outreach == "sent":
        show = donor_memory.get("lifetime_show_rate")
        label = f"({show:.0%} historical show rate)" if show else "(no history)"
        return {
            "action":    f"Wait for reply — outreach sent {label}",
            "reasoning": "Allow 2–4 hours for response before escalating to standby.",
            "urgency":   "today",
        }
    if score < 50:
        return {
            "action":    "Consider contacting rank-2 donor proactively",
            "reasoning": f"Top donor score is {score} — below the reliable threshold. Preparing standby early reduces risk.",
            "urgency":   "today",
        }
    return {
        "action":    "Send outreach to top-ranked donor",
        "reasoning": f"Donor scored {score} — high likelihood of confirmation.",
        "urgency":   "today",
    }
