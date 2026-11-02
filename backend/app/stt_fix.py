"""Ovozdan matn (STT) tipik xatolarini tuzatadi: ismlar, oila so'zlari, tibbiy atamalar, tutuq belgilari.
Faqat aniq, xavfsiz almashtirishlar: ma'noni o'zgartirmaydi."""
import re

_APOS = str.maketrans({"’": "'", "ʻ": "'", "‘": "'", "`": "'", "ʼ": "'", "´": "'"})

# (regex, almashtirish); so'z chegarasi bilan, katta-kichik harfga e'tiborsiz
_RULES = [
    (r"\bsalomat\s+(?:bo'?lvi|bulvi|buvvi|bovi|bubi|bubbi|bo'?vi|buwi|buvvvi)\b", "Salomat buvi"),
    (r"\b(?:bo'?lvi|bulvi|buvvi|buwi|bubbi|bubi)\b", "buvi"),
    (r"\b(?:nilufer|nelufar|nilofar|nilufarr|nilufur|nilifar)\b", "Nilufar"),
    (r"\b(?:yasmina|jasmin|jazmina|yazmina|jesmina|jasmine|yasmin|jazmin)\b", "Jasmina"),
    (r"\b(?:sardar|sardorr|zardor)\b", "Sardor"),
    (r"\ba'zolar(?:iz|izda|izni|inz|ingz|ingizda)\b", "a'zolaringiz"),
    (r"\ba'zolari?z\b", "a'zolaringiz"),
    (r"\bo'?zolaringiz\b", "a'zolaringiz"),
    (r"\boila\s+azolar", "oila a'zolar"),
    (r"\b(?:kon|qon)\s+(?:bosum|bosin|bosim[ie])\b", "qon bosimi"),
    (r"\bqonbosimi\b", "qon bosimi"),
    (r"\bhomilador(?:lik)?(?:ligiz)\b", "homiladorligingiz"),
    (r"\bhamshira\s*opa\b", "hamshira opa"),
    (r"\btiz+a\b", "tizza"),
    (r"\bqichishiyapti\b", "qichiyapti"),
    (r"\bo'?ynashim\s+(?:mumkin)\b", "o'ynashim mumkin"),
]
_HIKMAT = re.compile(r"\bhikmat\w*(?:\s+(ota|bobo))?", re.I)


def fix(text: str) -> str:
    t = (text or "").translate(_APOS)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return t
    for rx, rep in _RULES:
        t = re.sub(rx, rep, t, flags=re.I)
    t = _HIKMAT.sub(lambda m: "Hikmatilla" + (" " + m.group(1).lower() if m.group(1) else ""), t)
    return t
