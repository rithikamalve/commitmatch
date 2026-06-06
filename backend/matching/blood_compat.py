NORMALIZE_MAP = {
    "o-": "O Negative", "o negative": "O Negative",
    "o+": "O Positive", "o positive": "O Positive",
    "a-": "A Negative", "a negative": "A Negative",
    "a+": "A Positive", "a positive": "A Positive",
    "b-": "B Negative", "b negative": "B Negative",
    "b+": "B Positive", "b positive": "B Positive",
    "ab-": "AB Negative", "ab negative": "AB Negative",
    "ab+": "AB Positive", "ab positive": "AB Positive",
}

COMPATIBILITY_MAP: dict[str, list[str]] = {
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

ALL_BLOOD_GROUPS = list(COMPATIBILITY_MAP.keys())


def normalize_blood_group(bg) -> str | None:
    if not isinstance(bg, str) or not bg.strip():
        return None
    key = bg.strip().lower()
    return NORMALIZE_MAP.get(key, bg.strip())


def is_compatible(donor_bg: str | None, patient_bg: str | None) -> bool:
    d = normalize_blood_group(donor_bg)
    p = normalize_blood_group(patient_bg)
    if not d or not p:
        return False
    return p in COMPATIBILITY_MAP.get(d, [])
