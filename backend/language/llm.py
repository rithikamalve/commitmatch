import json
import logging

import boto3

import config

logger = logging.getLogger(__name__)

_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    return _bedrock_client


def _invoke_bedrock(prompt: str, max_tokens: int = 300) -> str:
    client = _get_client()
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    })
    response = client.invoke_model(body=body, modelId=config.BEDROCK_MODEL_ID)
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


# ─── Fallback templates ───────────────────────────────────────────────────────

def _fallback_outreach_template(donor: dict, patient: dict, language: str) -> str:
    name = donor.get("donor_name") or donor.get("user_id", "Donor")
    bg = donor.get("blood_group", "")
    if language.lower() in ("hindi", "hi"):
        return (
            f"Namaste {name} ji, Blood Warriors ki taraf se {bg} blood ki zaroorat hai. "
            "Kya aap donate kar sakte hain? Reply HAAN ya NAHI."
        )
    return (
        f"Hello {name}, Blood Warriors needs a {bg} blood donor urgently. "
        "Can you help? Please reply YES or NO."
    )


def _fallback_impact_template(
    donor: dict, patient_first_name: str, donation_date: str, city: str
) -> str:
    name = donor.get("donor_name") or donor.get("user_id", "Donor")
    return (
        f"{name} ji, aapne {donation_date} ko donate kiya tha — woh {patient_first_name} ke kaam aaya. "
        "Woh theek hai. Unki family ne shukriya kaha. — Blood Warriors"
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_outreach_message(donor: dict, patient: dict, language: str = "Hindi") -> str:
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _fallback_outreach_template(donor, patient, language)

    try:
        name = donor.get("donor_name") or donor.get("user_id", "Donor")
        bg = patient.get("bridge_blood_group") or patient.get("blood_group", "")
        prompt = (
            f"Write a WhatsApp message in {language} under 80 words.\n"
            f"Donor name: {name}\n"
            f"Blood type needed: {bg}\n"
            "Rules:\n"
            "- Mention the blood need and urgency without sharing the patient's full name\n"
            "- Be warm and personal, not clinical\n"
            "- End with: Reply HAAN (yes) or NAHI (no)\n"
            "Return ONLY the message, no explanation."
        )
        return _invoke_bedrock(prompt)
    except Exception as e:
        logger.warning("Bedrock outreach failed, using fallback: %s", e)
        return _fallback_outreach_template(donor, patient, language)


def detect_hesitation(reply_text: str) -> dict:
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _keyword_fallback(reply_text)

    try:
        prompt = (
            "Classify this WhatsApp reply from a blood donor into exactly ONE of: "
            "confirmed / declined / hesitation / unclear\n\n"
            f'Reply: "{reply_text}"\n\n'
            "Return JSON: {\"sentiment\": \"<class>\", \"confidence\": <0-1>, \"reasoning\": \"<short>\"}"
        )
        text = _invoke_bedrock(prompt, max_tokens=150)
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Bedrock hesitation detection failed, using keyword fallback: %s", e)
        return _keyword_fallback(reply_text)


def generate_impact_message(
    donor: dict, patient_first_name: str, donation_date: str, city: str
) -> str:
    if config.DEMO_MODE and not config.DEMO_WHATSAPP:
        return _fallback_impact_template(donor, patient_first_name, donation_date, city)

    try:
        name = donor.get("donor_name") or donor.get("user_id", "Donor")
        language = donor.get("preferred_language", "Hindi")
        prompt = (
            f"Write a post-donation thank-you WhatsApp message in {language} under 60 words.\n"
            f"Donor name: {name}\n"
            f"Donation date: {donation_date}\n"
            f"Patient first name: {patient_first_name}\n"
            f"City: {city}\n"
            "Rules:\n"
            "- Mention the specific date and patient first name\n"
            "- Say the patient is doing well, family sends gratitude\n"
            "- Feel human, not automated\n"
            "Return ONLY the message."
        )
        return _invoke_bedrock(prompt)
    except Exception as e:
        logger.warning("Bedrock impact message failed, using fallback: %s", e)
        return _fallback_impact_template(donor, patient_first_name, donation_date, city)


# ─── Keyword fallback ─────────────────────────────────────────────────────────

_HESITATION_KEYWORDS = {
    "dekhunga", "dekhta hun", "maybe", "traffic", "shayad", "koshish",
    "ho sakta", "try karunga", "thoda late", "late", "try",
}
_CONFIRMED_KEYWORDS = {
    "haan", "yes", "ok", "okay", "aata hun", "coming", "aa raha", "sure", "bilkul",
}
_DECLINED_KEYWORDS = {
    "nahi", "no", "cannot", "busy", "nhi", "nahin", "not possible", "sorry",
}


def _keyword_fallback(reply_text: str) -> dict:
    text = reply_text.lower()
    tokens = set(text.split())

    if tokens & _CONFIRMED_KEYWORDS:
        return {"sentiment": "confirmed", "confidence": 0.8, "reasoning": "Keyword match"}
    if tokens & _DECLINED_KEYWORDS:
        return {"sentiment": "declined", "confidence": 0.8, "reasoning": "Keyword match"}
    if tokens & _HESITATION_KEYWORDS or any(k in text for k in _HESITATION_KEYWORDS):
        return {"sentiment": "hesitation", "confidence": 0.7, "reasoning": "Hesitation keyword"}
    return {"sentiment": "unclear", "confidence": 0.5, "reasoning": "No keyword matched"}
