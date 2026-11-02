"""Bemorning o'z savollarini berish vaqtini serverda nazorat qiladi.
Model o'zi bilmaydi "qachon" so'rashni, shuning uchun har gal tarixga qarab: qaysi savol allaqachon berilgan,
qaysi biri ochilgan (hamshira kerakli mavzuni aytgan) va hozir so'rash mumkinmi, hal qilinadi.
Natija system promptning oxiriga qo'shiladigan ko'rsatma sifatida beriladi."""
import re
from dataclasses import dataclass

from . import stt_fix


@dataclass(frozen=True)
class Q:
    id: str
    text: str          # bemor aytadigan savol (deyarli so'zma-so'z)
    sig: str           # bemor shu savolni bergani tarixdan bilinadigan belgi (regex)
    trig: str          # hamshira gapida shu mavzu chiqsa savol "ochiladi" (regex)
    after: str = ""    # shu savol berilgandan keyingina


# Taklif: hamshira "savolingiz bormi" desa, ochilgan-ochilmaganidan qat'i nazar navbatdagi savol beriladi
INVITE = re.compile(r"savol(ingiz|laringiz|ingiz)?\s+(bor|yo'q)|so'ramoqchi|nimani bilmoqchi|tushunmagan|qiziqtirgan|aytmoqchi", re.I)
# Hamshira bemorga savol berayotgan bo'lsa, bemor javob beradi, o'z savolini bermaydi
ASKS = re.compile(r"\?|\b(mi|misiz|musiz|bormi|qanday|qancha|necha|qachon|qayer\w*|nega|nima|kim|qaysi|qaysilar|yo'qmi)\b", re.I)
CLOSE = re.compile(r"\b(xayr|ko'rishguncha|sog' bo'ling|tashrif\w* uchun|yana ko'rishamiz|suhbat\w* uchun rahmat|yakun)", re.I)

QUESTIONS: dict[str, list[Q]] = {
    "bobo": [
        Q("b1", "Qon bosimim ko'tarilib, boshim qattiq og'risa nima qilishim kerak?",
          r"qattiq og'ris|nima qilishim kerak",
          r"tuz|bosim.*(yozib|kundalik|o'lcha)|kundalik|sabzavot|piyoda|dori.*(vaqt|qabul)|chekish|alkogol"),
        Q("b2", "Biz oilamiz bilan qanday ovqatlanish tartibiga amal qilishimiz kerak?",
          r"ovqatlanish tartib|oilamiz bilan",
          r"103|tez yordam|ko'krak og'ri|nafas qisish|zudlik", after="b1"),
    ],
    "buvi": [
        Q("v1", "Yoshimiz katta bo'lganda qanday kasalliklarni tekshirtirib turishimiz kerak?",
          r"qanday kasalliklarni tekshir",
          r"gimnastika|vazn|kalsiy|vitamin|gilam|yiqil|sayr|mashq|shifokor ko'rig"),
        Q("v2", "Ba'zan oyoqlarim shishib ketadi. Bu nimadan bo'lishi mumkin?",
          r"shishib ketadi",
          r"tekshir|skrining|emlash|glyukoza|xolesterin|bosim|suyak|ko'rish|eshitish", after="v1"),
        Q("v3", "Oilamiz bilan birgalikda jismoniy mashqlar qilsak bo'ladimi?",
          r"jismoniy mashq\w* qilsak|oilamiz bilan birgalikda",
          r"shishish|yurak|buyrak|qon tomir|to'satdan|qizar", after="v2"),
    ],
    "homilador": [
        Q("h1", "Homiladorlik paytida qaysi belgilar xavfli hisoblanadi?",
          r"qaysi belgilar xavfli",
          r"ovqat|iste'mol|temir|foliy|kofein|alkogol|piyoda|gimnastika|dam ol|og'ir yuk|uyqu"),
        Q("h2", "Bolamning rivojlanishi yaxshi ekanini qanday bilsam bo'ladi?",
          r"rivojlanishi yaxshi ekan",
          r"qon kelishi|suv ketishi|103|zudlik|belgilar|xiralash|shish|harakat", after="h1"),
        Q("h3", "Oilamizda yuqumli kasalliklarning oldini olish uchun nimalarga e'tibor berishimiz kerak?",
          r"yuqumli kasallik",
          r"UTT|antenatal|ko'rik|laborator|tekshiruv|rivojlan", after="h2"),
    ],
    "bola": [
        Q("j1", "Men har kuni qancha o'ynashim mumkin?",
          r"qancha o'ynashim",
          r"yuv|tish|nonushta|odat|telefon|televizor|uxla|sabzavot|meva|chekla|chekla"),
        Q("j2", "Men shirinlik o'rniga olma yesam bo'ladimi?",
          r"olma yesam",
          r"180|daqiqa|yugur|sakra|faol|o'yin|shirinlik", after="j1"),
    ],
}

# Suhbat tugash payti aytiladigan yakuniy gap (bemor o'zi aytadi, hamshira xayrlashganda)
ENDING = {
    "bobo": "Bugungi suhbatdan ko'p foydali ma'lumot oldik. Endi oilamiz bilan birgalikda sog'lom turmush tarziga amal qilamiz.",
    "homilador": "Rahmat, endi o'zimga ko'proq e'tibor beraman.",
}


def _is_ask(text: str) -> bool:
    return bool(ASKS.search(text)) and not INVITE.search(text)


def hint(pid: str, history: list[dict]) -> str:
    """Hozirgi vaziyat bo'yicha ko'rsatma matni (system promptga qo'shiladi)."""
    qs = QUESTIONS.get(pid, [])
    nurse = [stt_fix.fix(t["content"]) for t in history if t["role"] == "user"]
    bot = [t["content"] for t in history if t["role"] == "assistant"]
    if not nurse:
        return ""
    last = nurse[-1]
    asked = {q.id for q in qs if any(re.search(q.sig, b, re.I) for b in bot)}
    unlocked = set()
    for i, m in enumerate(nurse):
        for q in qs:
            if q.id in unlocked or q.id in asked:
                continue
            if re.search(q.trig, m, re.I) and (not q.after or q.after in asked or q.after in unlocked):
                unlocked.add(q.id)
    prev_own = bool(bot) and any(re.search(q.sig, bot[-1], re.I) for q in qs)
    out = ["=== HOZIRGI VAZIYAT (bu ko'rsatma hamma narsadan muhimroq) ==="]
    ending = ENDING.get(pid)
    if CLOSE.search(last) and ending and ending not in " ".join(bot):
        out.append(f"Hamshira xayrlashyapti. Qisqa javob ber va ayt: «{ending}»")
        return "\n".join(out)
    invited = bool(INVITE.search(last))
    nxt = None
    for q in qs:
        if q.id in asked:
            continue
        if q.after and q.after not in asked:
            continue
        if q.id in unlocked or invited:
            nxt = q
            break
    if nxt and not prev_own and (invited or not _is_ask(last)):
        out.append("Avval hamshiraning gapiga bir-ikki so'z bilan javob ber (rozilik yoki minnatdorchilik). "
                   f"KEYIN javobing oxirida mana shu savolni ber, deyarli so'zma-so'z: «{nxt.text}»")
    else:
        out.append("Hozir o'zing hech qanday yangi savol BERMA: javobing savol belgisi bilan tugamasin. "
                   "Faqat hamshiraning aytganiga javob ber. Agar hamshira sendan nimadir so'ragan bo'lsa, faqat so'ralgan narsaga javob ber, qolganini aytma.")
        if nxt is None and not asked and not invited:
            pass
    return "\n".join(out)
