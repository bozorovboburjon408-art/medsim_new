"""O'z-o'zini sinash: ssenariyli suhbat (matn) va ovozdan matn aniqligi. Faqat DEBUG_TOKEN bilan, natija oddiy matn."""
import asyncio
import difflib
import re
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from . import chirp, eleven, llm, tts
from .config import settings
from .patients import PATIENTS

router = APIRouter()

NURSE = [
    "Assalomu alaykum, yaxshimisiz?",
    "Ahvolingiz qanday?",
    "Sizni nima bezovta qilyapti? Hammasini aytib bering.",
    "Bu qachondan beri bezovta qilyapti?",
    "Kechasi uxlaysizmi?",
    "Hozir haroratingizni o'lchab ko'raman.",
    "Kecha futbolda kim yutdi?",
    "asd fgh jkl nima qilsa man san",
    "Xavotir olmang, hammasi yaxshi bo'ladi, sizga yordam beramiz.",
    "Bugun shifokorga murojaat qilamiz, rozimisiz?",
]

STT_SENTENCES = [
    "Assalomu alaykum, men patronaj hamshirasiman.",
    "Qon bosimingizni o'lchab ko'raman.",
    "Qandli diabet bo'yicha dori ichyapsizmi?",
    "Kechasi necha marta hojatxonaga chiqasiz?",
    "Oyoqlaringizda uvishish yoki yara bormi?",
    "Haroratni o'lchaymiz, qo'ltiq ostiga qo'ying.",
    "Qornim og'riyapti deb aytdingizmi?",
    "Gijja bo'lsa, bolani shifokorga ko'rsatish kerak.",
    "Ertaga qaytib kelaman, o'zingizni ehtiyot qiling.",
    "Tez yordam chaqirish kerak bo'lsa, bir yuz uchga qo'ng'iroq qiling.",
]


def _check(token: str):
    if not settings.debug_token.strip() or token.strip() != settings.debug_token.strip():
        raise HTTPException(403, "Ruxsat yo'q")


def _norm(t: str) -> str:
    t = t.lower().replace("ʻ", "'").replace("‘", "'").replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]", " ", t)).strip()


def _flags(pid: str, nurse: str, reply: str, prev: str) -> list[str]:
    f = []
    sents = len(re.findall(r"[.!?]+(?:\s|$)", reply)) or 1
    if re.search(r"yig['’‘ʻ`]?lay", reply, re.I) and pid == "bola":
        f.append("YIG'LAY so'zi")
    if pid == "bola" and re.search(r"\b(oyo[qg]\w*|bosh(im|ing)\b|ko'z\w*|quloq\w*|qo'l\w*)", reply, re.I):
        f.append("TO'QIMA a'zo (ssenariyda yo'q)")
    if prev and difflib.SequenceMatcher(None, _norm(prev), _norm(reply)).ratio() > 0.8:
        f.append("TAKROR")
    if sents > 5:
        f.append("JUDA UZUN")
    if len(nurse.split()) <= 3 and sents > 3:
        f.append("qisqa savolga uzun javob")
    if re.search(r"\bBemor\s*:", reply):
        f.append("'Bemor:' deb yozdi")
    return f


async def _reply(pid: str, history: list[dict]) -> tuple[str, int]:
    p = PATIENTS[pid]
    t0 = time.perf_counter()
    out = [s async for s in llm.stream_sentences(p.system_prompt(), history, {}, None)]
    return " ".join(out), int((time.perf_counter() - t0) * 1000)


async def _convo(pid: str) -> list[str]:
    lines = [f"=== {PATIENTS[pid].title} ({pid}) ==="]
    hist: list[dict] = []
    prev = ""
    for q in NURSE:
        hist.append({"role": "user", "content": q})
        try:
            reply, ms = await _reply(pid, hist)
        except Exception as e:
            lines.append(f"Siz: {q}\n  XATO: {str(e)[:200]}")
            break
        hist.append({"role": "assistant", "content": reply})
        fl = _flags(pid, q, reply, prev)
        lines.append(f"Siz: {q}\nBemor ({ms} ms): {eleven.strip_tags(reply)}" + (f"\n  !!! {', '.join(fl)}" if fl else ""))
        prev = reply
    return lines


@router.get("/self_test", response_class=PlainTextResponse)
async def self_test(token: str = "", patient: str = "all"):
    """Ssenariyli 10 savollik suhbat (ovozsiz) va avtomatik belgilar: takror, uzunlik, yig'lash so'zi, to'qima a'zolar."""
    _check(token)
    ids = list(PATIENTS) if patient == "all" else [patient]
    if any(i not in PATIENTS for i in ids):
        raise HTTPException(404, "Bemor topilmadi")
    res = await asyncio.gather(*[_convo(i) for i in ids])
    return "\n\n".join("\n".join(r) for r in res)


def _wer(ref: str, hyp: str) -> float:
    r, h = _norm(ref).split(), _norm(hyp).split()
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return d[len(h)] / max(1, len(r))


@router.get("/stt_selftest", response_class=PlainTextResponse)
async def stt_selftest(token: str = ""):
    """Ma'lum gaplarni ElevenLabs ovozi bilan aytdirib, Gemini va Scribe qanchalik aniq yozishini o'lchaydi (sun'iy ovoz bilan, taxminiy)."""
    _check(token)
    if not eleven.enabled():
        raise HTTPException(400, "ELEVENLABS_API_KEY o'rnatilmagan")
    vid = eleven.DEFAULT_VOICE["homilador"]

    sem = asyncio.Semaphore(2)  # ElevenLabs parallel so'rovlar chegarasi (429) dan saqlanish

    async def one(sent: str):
        try:
            async with sem:
                pcm = await eleven.tts(sent, vid, "eleven_multilingual_v2")
        except Exception as e:
            err = f"XATO (ovoz yaratish) {str(e)[:120]}"
            return sent, err, err, err, err
        wav = tts._pcm_to_wav(pcm, 24000)

        async def g():
            try:
                return (await llm.transcribe(wav, "audio/wav"))[0]
            except Exception as e:
                return f"XATO {str(e)[:80]}"

        async def s():
            try:
                return await eleven.stt(wav, "audio/wav")
            except Exception as e:
                return f"XATO {str(e)[:80]}"

        async def c(h):
            try:
                return await chirp.stt(wav, "audio/wav", hints=h)
            except Exception as e:
                return f"XATO {str(e)[:300]}"

        return sent, await g(), await s(), await c(True), await c(False)

    rows = await asyncio.gather(*[one(x) for x in STT_SENTENCES])
    lines, tot = [], [0.0] * 4
    names = ["Gemini", "Scribe", "Chirp+maslahat", "Chirp"]
    nl = chr(10)
    for sent, *outs in rows:
        ws = [_wer(sent, o) for o in outs]
        for k, w in enumerate(ws):
            tot[k] += w
        lines.append(f"ASL: {sent}" + nl + nl.join(f"{nm}: {o}   (xato {w:.0%})" for nm, o, w in zip(names, outs, ws)))
    n = len(rows)
    lines.append(nl + "O'RTACHA so'z xatosi: " + ", ".join(f"{nm} {t / n:.0%}" for nm, t in zip(names, tot))
                 + "  (sun'iy ovoz bilan; haqiqiy ovozda boshqacha bo'lishi mumkin)")
    return (nl + nl).join(lines)
