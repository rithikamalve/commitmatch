"""
Case Summarizer — generates a concise natural-language summary of a blood request
for handoff between coordinators or for audit logs.
"""
import json
import logging

import config

logger = logging.getLogger(__name__)


def summarize_request(request: dict, ranked_donors: list[dict], timeline: list[dict]) -> str:
    """Returns a 3-5 sentence plain-English summary of a blood request."""
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _rule_based_summary(request, ranked_donors, timeline)

    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)

        donor_summary = "\n".join(
            f"  Rank {d['rank']}: score {d.get('commitment_score','?')}, "
            f"outreach={d.get('outreach_status','?')}"
            for d in ranked_donors[:3]
        )
        events = "\n".join(
            f"  {e.get('direction','?')} — {e.get('sentiment') or 'no sentiment'}"
            for e in timeline[-5:]
        )

        prompt = (
            f"Summarize this blood donation request in 3–5 sentences for a coordinator handoff.\n"
            f"Request status: {request.get('status','?')}\n"
            f"Blood type: {request.get('patient_blood_group','?')}\n"
            f"Required date: {request.get('required_date','?')}\n"
            f"Top 3 donors:\n{donor_summary}\n"
            f"Recent interactions:\n{events}\n\n"
            "Be factual and concise. No fluff."
        )
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        })
        resp = client.invoke_model(body=body, modelId=config.BEDROCK_MODEL_ID)
        return json.loads(resp["body"].read())["content"][0]["text"]
    except Exception as e:
        logger.warning("Summarizer failed: %s", e)
        return _rule_based_summary(request, ranked_donors, timeline)


def _rule_based_summary(request: dict, ranked_donors: list, timeline: list) -> str:
    bg     = request.get("patient_blood_group", "unknown")
    status = request.get("status", "open")
    date   = request.get("required_date", "TBD")
    n      = len(ranked_donors)
    top    = ranked_donors[0] if ranked_donors else {}
    score  = top.get("commitment_score", "?")
    out    = top.get("outreach_status", "pending")
    events = len(timeline)

    return (
        f"Blood request for {bg} blood — required by {date}, currently {status}. "
        f"{n} compatible donors identified; top donor scored {score}. "
        f"Primary outreach status: {out}. "
        f"{events} interaction event(s) logged."
    )
