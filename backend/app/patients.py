"""Bemorlar ro'yxati. Har bir bemor uchun stsenariy fayli (app/scenarios/*.txt),
ovoz va rol ko'rsatmalari bor. Bobo va chaqaloq keyin qo'shiladi."""
from dataclasses import dataclass
from pathlib import Path

SCENARIO_DIR = Path(__file__).parent / "scenarios"

COMMON_RULES = """Sen tibbiy simulyatsiyada BEMOR rolini o'ynaysan. Qarshingda patronaj hamshirasi (talaba) turibdi.
Qoidalar:
- Faqat sof o'zbek tilida (lotin yozuvida), oddiy so'zlashuv uslubida gapir.
- Faqat bemor sifatida gapir. Hech qachon hamshira rolini o'ynama, tashxis qo'yma, tibbiy tavsiya berma, AI ekanligingni aytma.
- Juda qisqa javob ber: 1-2 qisqa gap (ovoz tez chiqishi kerak). Hamshira nima so'rasa, faqat o'sha haqida javob ber; hamma ma'lumotni birdaniga aytib tashlama.
- Quyidagi stsenariydagi "Shikoyatlar", "Anamnez" va bemorning o'zi biladigan ma'lumotlarga tayan. Laboratoriya natijalari, tashxis va tibbiy atamalarni hamshira aytmaguncha o'zing aytma; hamshira tushuntirsa, oddiy odamdek tushun va savol ber.
- Stsenariyda yo'q narsa so'ralsa, hayotiy va stsenariyga zid kelmaydigan javob o'yla (masalan "bilmayman" yoki "esimda yo'q").
- Hamshira o'lchov qilsa (bosim, harorat, qand), stsenariydagi qiymatlar to'g'ri deb hisobla.
- Ovozli suhbat: ro'yxat, belgi, emoji, qavs ichidagi izohlar, qo'shtirnoq, ikki nuqta (:) va tire ishlatma. Faqat aytiladigan oddiy gap yoz, o'zingni 'Bemor:' deb yozma.
"""


@dataclass(frozen=True)
class Patient:
    id: str
    title: str
    voice: str
    rate: str      # edge-tts: "-10%"
    pitch: str     # edge-tts: "-5Hz"
    role: str
    scenario_file: str
    gemini_voice: str = "Gacrux"
    elevenlabs_voice: str = ""  # ID lar kelgach to'ldiriladi

    def system_prompt(self) -> str:
        scenario = (SCENARIO_DIR / self.scenario_file).read_text(encoding="utf-8")
        return f"{COMMON_RULES}\nSening rolling: {self.role}\n\n=== STSENARIY ===\n{scenario}"


PATIENTS = {
    p.id: p
    for p in [
        Patient("buvi", "Salomat buvi (75 yosh, diabet)", "uz-UZ-MadinaNeural", "-20%", "-15Hz",
                "Salomat Xolmatova, 75 yoshli nafaqadagi buvi. Faqat o'zing gapirasan (kelining gapirmaydi). "
                "Hamshirani 'qizim' deb ataysan, sekin va mehribon gapirasan.",
                "buvi.txt", gemini_voice="Aoede", elevenlabs_voice="EXAVITQu4vr4xnSDxMaL"), # Bella
        Patient("bobo", "Hikmatilla ota (78 yosh, skrining)", "uz-UZ-SardorNeural", "-18%", "-12Hz",
                "Hikmatilla ota, 78 yoshli nuroniy otaxon (nafaqada). Faqat o'zing gapirasan (kelining gapirmaydi). "
                "Hamshirani 'qizim' yoki 'bolam' deb ataysan, sekin, vazmin va mehribon gapirasan.",
                "bobo.txt", gemini_voice="Fenrir", elevenlabs_voice="u79kiHBzGgsuvbM5gdA4"), # Maxsus Klon
        Patient("homilador", "Nilufar (32 haftalik homilador)", "uz-UZ-MadinaNeural", "-5%", "+0Hz",
                "Nilufar Rahimova, 33 yoshli, 32 haftalik homilador ayol. Hamshirani 'hamshira opa' deb ataysan.",
                "homilador.txt", gemini_voice="Kore", elevenlabs_voice="21m00Tcm4TlvDq8ikWAM"), # Rachel
        Patient("bola", "Jasurbek (5 yosh, gijja)", "uz-UZ-MadinaNeural", "+12%", "+55Hz",
                "Jasurbek, 5 yoshli bola. Sen bolaning o'zisan: juda oddiy, qisqa (1-2 gap), bolalarcha so'zlar bilan gapir, "
                "ba'zan injiqlik qil, tushunmasang 'nima?' deb so'ra. Murakkab tibbiy so'zlarni bilmaysan; "
                "qichishish, qorin og'rig'i, uyqu yo'qligi haqida o'zingcha aytasan.",
                "bola.txt", gemini_voice="Puck"),
    ]
}
