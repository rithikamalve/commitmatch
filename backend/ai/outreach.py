"""
AI Outreach — Layer 3.  Language only.

Claude via AWS Bedrock.
Used ONLY for:
  1. Generating personalised WhatsApp messages
  2. Detecting hesitation signals in donor replies

Never for ranking. Never for decisions.
"""
import json
import logging

import config

logger = logging.getLogger(__name__)

_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        from botocore.config import Config
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION,
            config=Config(
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 1},
            ),
        )
    return _bedrock_client


def _invoke(prompt: str, max_tokens: int = 300) -> str:
    import time
    client = _get_client()
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    })
    print(f"[BEDROCK] → Calling model={config.BEDROCK_MODEL_ID} max_tokens={max_tokens}")
    t0 = time.monotonic()
    resp = client.invoke_model(body=body, modelId=config.BEDROCK_MODEL_ID)
    result = json.loads(resp["body"].read())
    text = result["content"][0]["text"]
    print(f"[BEDROCK] ✓ Response in {int((time.monotonic()-t0)*1000)}ms — {len(text)} chars")
    return text


# ── Fallback templates (no API needed) ────────────────────────────────────────

def _fallback_outreach(donor: dict, patient: dict, language: str) -> str:
    name = donor.get("donor_name") or donor.get("user_id", "Donor")
    bg   = patient.get("bridge_blood_group") or patient.get("blood_group", "")
    show_rate = donor.get("lifetime_show_rate")

    # Personalise tone if memory is available
    if show_rate and show_rate >= 0.8:
        trust_line = "Aap humare sabse bharosemand donors mein se hain." if language.lower() == "hindi" else "You are one of our most trusted donors."
    elif donor.get("is_first_contact"):
        trust_line = "Blood Warriors mein aapka swagat hai." if language.lower() == "hindi" else "Welcome to Blood Warriors."
    else:
        trust_line = ""

    if language.lower() in ("hindi", "hi"):
        return (
            f"Namaste {name} ji, Blood Warriors ki taraf se {bg} blood ki zaroorat hai. "
            f"{trust_line} Kya aap donate kar sakte hain? Reply HAAN ya NAHI."
        ).strip()
    return (
        f"Hello {name}, Blood Warriors urgently needs a {bg} blood donor. "
        f"{trust_line} Can you help? Reply YES or NO."
    ).strip()


def _fallback_impact(donor: dict, patient_first_name: str, donation_date: str, city: str) -> str:
    name = donor.get("donor_name") or donor.get("user_id", "Donor")
    return (
        f"{name} ji, aapne {donation_date} ko donate kiya tha — woh {patient_first_name} ke kaam aaya. "
        "Woh theek hai. Unki family ne shukriya kaha. — Blood Warriors"
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_outreach_message(
    donor: dict, patient: dict, language: str = "Hindi"
) -> str:
    """Personalised WhatsApp outreach. Uses donor memory for tone."""
    print(f"[OUTREACH] generate_outreach_message — DEMO_MODE={config.DEMO_MODE} DEMO_WHATSAPP={config.DEMO_WHATSAPP}")
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        print(f"[OUTREACH] Using fallback (demo mode, no WhatsApp)")
        return _fallback_outreach(donor, patient, language)

    try:
        name     = donor.get("donor_name") or donor.get("user_id", "Donor")
        bg       = patient.get("bridge_blood_group") or patient.get("blood_group", "")
        mem_note = donor.get("memory_summary", "")
        prompt = (
            f"Write a WhatsApp message in {language} under 80 words.\n"
            f"Donor name: {name}\n"
            f"Blood type needed: {bg}\n"
            f"Donor history: {mem_note}\n"
            "Rules:\n"
            "- Mention blood need and urgency; do NOT share patient's full name\n"
            "- Be warm and personal — reference past donations if history exists\n"
            "- End with: Reply HAAN (yes) or NAHI (no)\n"
            "Return ONLY the message text."
        )
        return _invoke(prompt)
    except Exception as e:
        print(f"[OUTREACH] ✗ Bedrock failed — {type(e).__name__}: {e}")
        logger.warning("Bedrock outreach failed, using fallback: %s", e)
        return _fallback_outreach(donor, patient, language)


def detect_hesitation(reply_text: str) -> dict:
    """Classify a donor reply. Returns sentiment, confidence, reasoning."""
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _keyword_fallback(reply_text)

    try:
        prompt = (
            'Classify this WhatsApp reply from a blood donor:\n'
            f'Reply: "{reply_text}"\n\n'
            'Return exactly one JSON object:\n'
            '{"sentiment":"confirmed|declined|hesitation|unclear","confidence":0.0-1.0,"reasoning":"brief"}'
        )
        text = _invoke(prompt, max_tokens=120)
        start, end = text.find("{"), text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Bedrock hesitation detection failed: %s", e)
        return _keyword_fallback(reply_text)


def generate_impact_message(
    donor: dict, patient_first_name: str, donation_date: str, city: str
) -> str:
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _fallback_impact(donor, patient_first_name, donation_date, city)

    try:
        name     = donor.get("donor_name") or donor.get("user_id", "Donor")
        language = donor.get("preferred_language", "Hindi")
        prompt = (
            f"Write a 48-hour post-donation thank you WhatsApp message in {language} under 60 words.\n"
            f"Donor name: {name}\nDonation date: {donation_date}\n"
            f"Patient first name: {patient_first_name}\nCity: {city}\n"
            "Rules: mention the date and patient name; say patient is doing well; feel human, not automated.\n"
            "Return ONLY the message text."
        )
        return _invoke(prompt)
    except Exception as e:
        logger.warning("Bedrock impact message failed: %s", e)
        return _fallback_impact(donor, patient_first_name, donation_date, city)


# ── Keyword fallback ───────────────────────────────────────────────────────────

_HESITATION = {"dekhunga","dekhta hun","maybe","traffic","shayad","koshish",
               "ho sakta","try karunga","thoda late","late","try"}
_CONFIRMED  = {"haan","yes","ok","okay","aata hun","coming","aa raha","sure","bilkul"}
_DECLINED   = {"nahi","no","cannot","busy","nhi","nahin","not possible","sorry"}


def _keyword_fallback(reply_text: str) -> dict:
    text   = reply_text.lower()
    tokens = set(text.split())
    if tokens & _CONFIRMED:
        return {"sentiment": "confirmed",   "confidence": 0.8, "reasoning": "Keyword match"}
    if tokens & _DECLINED:
        return {"sentiment": "declined",    "confidence": 0.8, "reasoning": "Keyword match"}
    if tokens & _HESITATION or any(k in text for k in _HESITATION):
        return {"sentiment": "hesitation",  "confidence": 0.7, "reasoning": "Hesitation keyword"}
    return     {"sentiment": "unclear",     "confidence": 0.5, "reasoning": "No match"}
