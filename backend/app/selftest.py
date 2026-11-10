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

NURSE = {  # hujjatdagi dialog tartibida (hamshira gaplari)
    "bobo": [
        "Assalomu alaykum, bobo! Yaxshimisiz?",
        "Oilada 1 yoshli kichkina bola ham bormi? Ismi nima, kimning o'g'li?",
        "Oila a’zolariz haqida tanishtirasizmi?",
        "Bobo, nechta farzandingiz bor? Ismingiz nima?",
        "Bugun ob-havo qanday ekan?",
        "Hozir qon bosimingizni o'lchab ko'raymi?",
        "Oilangizda kimlarda surunkali kasalliklar bor? Kimdir doimiy dori qabul qiladimi?",
        "Bobo, qon bosimingizni oxirgi marta qachon o'lchagansiz?",
        "Qon bosimining 160/100 bo'lishi e'tibor talab qiladi. Tuzli ovqatlarni ko'p iste'mol qilasizmi?",
        "Har kuni piyoda yurasizmi? Dorilaringizni muntazam qabul qilasizmi?",
        "Qon bosimingizni har kuni o'lchab, kundalikka yozib boring. Tuzni kuniga 5 grammdan oshirmang. Sog'lig'ingiz imkon bersa, har kuni 20-30 daqiqa piyoda yuring. Dorini belgilangan vaqtda ichib turing.",
        "Kecha futbolda kim yutdi?",
        "Agar qon bosimi juda yuqori bo'lsa shifokor bilan bog'laning. Ko'krak og'rig'i, nafas qisishi yoki nutq buzilishi bo'lsa darhol 103 ga qo'ng'iroq qiling.",
        "Oilada sog'lom ovqatlanish uchun sabzavot va meva ko'proq bo'lsin, tuz va shakarni me'yorida iste'mol qiling, fast-fud va gazlangan ichimliklarni cheklang.",
        "Sog' bo'ling, tashrif uchun rahmat, xayr.",
    ],
    "buvi": [
        "Assalomu alaykum, buvi! Yaxshimisiz?",
        "Oilada 1 yoshli kichkina bola ham bormi? Ismi nima, kimning o'g'li?",
        "oila a’zolarizda tanishtira olasizmi",
        "Buvi, ismingiz nima? Necha yoshdasiz?",
        "Bugun nima ovqat pishirdingiz?",
        "Qand kasalligingiz bormi?",
        "Oilangizda kimlarda surunkali kasalliklar bor?",
        "Buvi, tizza og'rig'i qachondan beri davom etmoqda?",
        "Sizda bo'g'im kasalligi bo'yicha shifokor tashxisi bormi?",
        "Tizza og'rig'ining sababini aniqlash uchun shifokor ko'rigidan o'ting, yengil gimnastika va sayr qilib turing, ortiqcha vazn bo'lsa kamaytiring.",
        "Uyda sirpanchiq gilamlarni olib tashlang, kalsiy va D vitaminiga boy ovqat yeng.",
        "asd fgh jkl nima qilsa man san",
        "Yoshingizda qon bosimi, qand, xolesterin, ko'rish va eshitishni tekshirtirib turish, grippga qarshi emlanish muhim.",
        "Oyoq shishishi yurak, buyrak yoki qon tomir kasalligidan bo'lishi mumkin, shifokorga yo'naltiramiz. Bir oyoq to'satdan shishib og'risa tez yordam chaqiring.",
        "Albatta, oilangiz bilan mashq qilsangiz bo'ladi, faqat yoshiga va salomatligiga mos bo'lsin. Xayr.",
    ],
    "homilador": [
        "Assalomu alaykum! Homiladorligingiz muborak bo'lsin!",
        "Oilada 1 yoshli kichkina bola ham bormi? Ismi nima, kimning o'g'li?",
        "oila a’zolariz haqida tanishtirasizmi",
        "Ismingiz nima? Eringiz nima ish qiladi?",
        "Bolangiz o'g'il bo'ladimi, qiz?",
        "Qon bosimingizni o'lchaymizmi?",
        "Oilangizda kimlarda surunkali kasalliklar bor? Sizni nima bezovta qilyapti?",
        "Hozir homiladorlikning nechanchi haftasidasiz? Antenatal nazoratga muntazam qatnayapsizmi?",
        "Temir va foliy kislotasini shifokor tavsiyasi bilan qabul qiling, yetarli suv iching, go'sht, baliq, tuxum, sabzavot va mevani me'yorida yeng, kofeinni kamaytiring.",
        "Muntazam piyoda yuring, yengil gimnastika qiling, og'ir yuk ko'tarmang va yetarli dam oling.",
        "asd fgh jkl nima qilsa man san",
        "Qindan qon kelishi, kuchli qorin og'rig'i, ko'rish xiralashishi, yuz va qo'llarning to'satdan shishishi yoki homila harakati kamayishi bo'lsa zudlik bilan tibbiy yordamga murojaat qiling.",
        "Antenatal ko'riklarni o'z vaqtida o'tkazing, UTT va laborator tekshiruvlarni shifokor belgilagan muddatda qiling.",
        "Qo'llarni sovunlab yuving, xonalarni shamollating, emlash taqvimiga amal qiling, gigiyenaga rioya qiling.",
        "Sog' bo'ling, xayr!",
    ],
    "bola": [
        "Salom, shirin qizaloq! Isming nima? Necha yoshdasan?",
        "Oilada 1 yoshli kichkina bola ham bormi? Ismi nima, kimning o'g'li?",
        "Oila a’zolaringni tanishtira olasanmi?",
        "Tug'ilgan kuning qachon?",
        "Qorning og'riyaptimi?",
        "Bugun nima ovqat yeding?",
        "Sen nimalarni yaxshi ko'rasan? Meva va sabzavotlarni yeysanmi?",
        "Qo'lingni ovqatdan oldin yuvasanmi?",
        "Nonushta qilasanmi? Tishlaringni yuvasanmi?",
        "Ovqatdan oldin qo'llaringni sovunlab yuv, ertalab va kechqurun tishingni tozala, shirinlikni kamroq yegin, telefonni cheklagin.",
        "Kecha futbolda kim yutdi?",
        "Sen uchun kun davomida kamida 180 daqiqa faol o'yinlar foydali, yugurish va sakrash ham kerak.",
        "Albatta! Olma, banan va nok juda foydali.",
    ],
}

STT_SENTENCES = [
    "Assalomu alaykum, men patronaj hamshirasiman.",
    "Qon bosimingizni o'lchab ko'raman.",
    "Qon bosimingiz baland bo'lsa shifokorga boring.",
    "Tuz iste'molini kamaytiring.",
    "Oyoqlaringiz shishmaydimi?",
    "Haroratni o'lchaymiz, qo'ltiq ostiga qo'ying.",
    "Homiladorlik muborak bo'lsin.",
    "Olma yesang juda foydali bo'ladi.",
    "Ertaga qaytib kelaman, o'zingizni ehtiyot qiling.",
    "Tez yordam chaqirish kerak bo'lsa, bir yuz uchga qo'ng'iroq qiling.",
]


def _check(token: str):
    if not settings.debug_token.strip() or token.strip() != settings.debug_token.strip():
        raise HTTPException(403, "Ruxsat yo'q")


def _norm(t: str) -> str:
    t = t.lower().replace("ʻ", "'").replace("‘", "'").replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]", " ", t)).strip()


def _flags(pid: str, nurse: str, reply: str, prev: str, hint: str = "") -> list[str]:
    f = []
    if hint:
        asks = "?" in reply and "Tushunmadim" not in reply and not re.search(r"^\W*nima[?]?\W*$", reply, re.I)
        if "BERMA" in hint and asks:
            f.append("VAQTSIZ SAVOL (hozir savol berish kerak emas edi)")
        if "mana shu savolni ber" in hint and "?" not in reply:
            f.append("SAVOL BERMADI (hozir berishi kerak edi)")
    sents = len(re.findall(r"[.!?]+(?:\s|$)", reply)) or 1
    if re.search(r"yig['’‘ʻ`]?lay", reply, re.I) and pid == "bola":
        f.append("YIG'LAY so'zi")
    if re.search(r"turolmayman|qila olmayman|kasalman|bo'lmaydi", reply, re.I):
        f.append("QARSHILIK (tavsiyaga rozi bo'lishi kerak)")
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
    out = [s async for s in llm.stream_sentences(p.system_prompt(history), history, {}, None)]
    return " ".join(out), int((time.perf_counter() - t0) * 1000)


async def _convo(pid: str) -> list[str]:
    lines = [f"=== {PATIENTS[pid].title} ({pid}) ==="]
    hist: list[dict] = []
    prev = ""
    for q in NURSE[pid]:
        hist.append({"role": "user", "content": q})
        hint_before = dialog.hint(pid, hist)
        try:
            reply, ms = await _reply(pid, hist)
        except Exception as e:
            lines.append(f"Siz: {q}\n  XATO: {str(e)[:200]}")
            break
        hist.append({"role": "assistant", "content": reply})
        fl = _flags(pid, q, reply, prev, hint_before)
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
