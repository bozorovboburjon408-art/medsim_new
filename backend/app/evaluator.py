"""Suhbat tugagach hamshira (talaba) ishini stsenariy asosida baholaydi."""
import json
import re

import httpx

from . import llm
from .config import settings
from .patients import SCENARIO_DIR, Patient

STAGES = [
    "1-bosqich: Muloqotni boshlash va holatni baholash",
    "2-bosqich: Holatni tushuntirish va shoshilinch chora (shifokor bilan bog'lanish)",
    "3-bosqich: Xavfli belgilar bo'yicha yo'riqnoma",
    "4-bosqich: Tavsiyalar (parvarish, dori, parhez/gigiyena, qayta ko'rik)",
    "Muloqot madaniyati",
]
MAX_PER_STAGE = 20

SYSTEM = """You are an experienced nursing instructor grading a nursing student's patient-visit (patronage) conversation.
The student played the NURSE (lines marked HAMSHIRA). The AI played the PATIENT (lines marked BEMOR) — do not grade the patient.
Use the SCENARIO below as the reference of what a good nurse should cover. Grade ONLY what the nurse actually said or did in the transcript.
Be fair but strict: a stage the nurse did not touch gets 0. A short conversation cannot cover all stages. Wrong or unsafe medical advice must lower the score and be listed as missed/wrong.

Score exactly these 5 criteria, each 0-20:
1. Starting the conversation and assessing the condition (greeting, asking complaints, anamnesis questions, offering measurements such as blood pressure, temperature, glucose, examining).
2. Explaining the condition simply and urgent action (contacting the family doctor/specialist, referrals, tests).
3. Danger-signs instruction (when to call an ambulance / doctor urgently), specific to this patient's illness.
4. Recommendations (medication adherence, diet/hygiene, care, follow-up visits), specific to this illness.
5. Communication culture (polite address, simple clear language, empathy, reassurance, not interrupting, checking understanding).

Write ALL text values in Uzbek (Latin script), short and concrete. Respond with JSON only, in this exact shape:
{"stages":[{"score":int,"done":[str,...],"missed":[str,...]} x5 in the order above],
 "strengths":[str,...], "advice":[str,...], "summary":str}
"done" = what the nurse did well in that criterion (max 3 short items); "missed" = important things not done or wrong (max 3 short items);
"strengths" max 3 items; "advice" = 3 concrete suggestions for improvement; "summary" = 1-2 sentences."""


def build_prompt(p: Patient, history: list[dict]) -> str:
    scenario = (SCENARIO_DIR / p.scenario_file).read_text(encoding="utf-8")
    lines = [("HAMSHIRA: " if t["role"] == "user" else "BEMOR: ") + t["content"] for t in history]
    return f"=== SCENARIO (reference) ===\n{scenario}\n\n=== TRANSCRIPT ===\n" + "\n".join(lines)


def parse(text: str) -> dict:
    """Modelning JSON javobini tekshirib, tartibga keltiradi (umumiy ballni o'zimiz hisoblaymiz)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    data = json.loads(text)
    stages_in = data.get("stages") or []
    stages = []
    for i, name in enumerate(STAGES):
        s = stages_in[i] if i < len(stages_in) and isinstance(stages_in[i], dict) else {}
        try:
            score = int(round(float(s.get("score", 0))))
        except (TypeError, ValueError):
            score = 0
        stages.append({
            "name": name, "score": max(0, min(MAX_PER_STAGE, score)), "max": MAX_PER_STAGE,
            "done": [str(x) for x in (s.get("done") or [])][:4],
            "missed": [str(x) for x in (s.get("missed") or [])][:4],
        })
    return {
        "total": sum(s["score"] for s in stages),
        "stages": stages,
        "strengths": [str(x) for x in (data.get("strengths") or [])][:4],
        "advice": [str(x) for x in (data.get("advice") or [])][:5],
        "summary": str(data.get("summary") or ""),
    }


async def evaluate(p: Patient, history: list[dict], model: str | None = None) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": build_prompt(p, history)}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096, "responseMimeType": "application/json"},
    }
    models = [m.strip() for m in settings.gemini_eval_models.split(",") if m.strip()]
    if model and re.fullmatch(r"[a-z0-9.\-]+", model):
        models = [model] + [m for m in models if m != model]
    models = llm.healthy_first(models)
    last = "model ro'yxati bo'sh"
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=45, write=5, pool=5)) as c:
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                r = await c.post(url, json=body, headers={"x-goog-api-key": settings.gemini_api_key})
            except httpx.TimeoutException:
                last = f"{m}: timeout"
                continue
            if r.status_code >= 400:
                last = f"{m}: {r.status_code} {r.text[:150]}"
                continue
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(x.get("text", "") for x in parts if not x.get("thought"))
                return parse(text)
            except (KeyError, IndexError, ValueError, TypeError) as e:
                last = f"{m}: javobni o'qib bo'lmadi ({type(e).__name__})"
    raise RuntimeError(last)
