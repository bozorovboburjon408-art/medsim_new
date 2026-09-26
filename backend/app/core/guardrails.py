"""
MedSim AI Guardrails
AI javoblarini nazorat qilish — xarakter chegaralarini buzmaslik uchun.
"""
import logging
from typing import Optional
from app.db.models import Mannequin, Scenario, ScriptQA

logger = logging.getLogger(__name__)


class Guardrails:
    """
    AI uchun qat'iy qoidalar va cheklovlar.
    Har bir manikenning xarakteri, mavzu chegaralari va til uslubini nazorat qiladi.
    """

    # AI o'zini AI deb oshkor qilmasligi uchun taqiqlangan so'zlar
    FORBIDDEN_AI_PHRASES = [
        "sun'iy intellekt", "artificial intelligence", "AI model",
        "men AI", "men model", "men chatbot", "men dastur",
        "openai", "gpt", "language model", "chatgpt",
        "men robot", "dasturlangan", "algoritmik"
    ]

    # Har qanday xarakter uchun taqiqlangan mavzular
    GLOBAL_FORBIDDEN_TOPICS = [
        "siyosat", "politika", "diniy bahslar", "irqchilik",
        "zo'ravonlik", "pornografiya", "noqonuniy", "giyohvand"
    ]

    def build_system_prompt(
        self,
        mannequin: Mannequin,
        scenario: Optional[Scenario],
        matched_scripts: list[ScriptQA]
    ) -> str:
        """
        AI uchun tizimli prompt qurish.
        Qatlamlar: Umumiy qoidalar → Qahramon shaxsiyati → Ssenariy konteksti → Skript konteksti
        """

        # ===== 1-qatlam: Umumiy qoidalar =====
        base_rules = (
            "SEN TIBBIYOT TALABALARI UCHUN BEMOR ROLINI O'YNAYOTGAN MANIKENSAN.\n\n"
            "QOIDALAR (HECH QACHON BUZMA):\n"
            "1. Har doim rolingda qol. Hech qachon sun'iy intellekt yoki robot ekanligingni tan olma.\n"
            "2. Qisqa va tabiiy javob ber (1-3 gapdan ko'p bo'lmasin).\n"
            "3. Faqat O'ZBEK tilida javob ber.\n"
            "4. Agar savol sening mavzu doirangdan tashqarida bo'lsa, xarakteringga mos 'tushunmadim' javobini ber.\n"
            "5. Tibbiy tashxis, diagnoz yoki davolash usuli BERMA — sen bemorsan, shifokor emas.\n"
            "6. Siyosiy, diniy, zo'ravonlik yoki boshqa noto'g'ri kontentga javob berma.\n"
            "7. Javobingda qahramon yoshiga mos til va lug'at ishlat.\n"
            "\n"
        )

        # ===== 2-qatlam: Qahramon shaxsiyati =====
        character_prompt = f"SENING SHAXSING:\n{mannequin.system_prompt}\n\n"

        # Ruxsat etilgan va taqiqlangan mavzular
        topics_prompt = ""
        if mannequin.allowed_topics:
            topics_prompt += f"Ruxsat etilgan mavzular: {', '.join(mannequin.allowed_topics)}\n"
        if mannequin.forbidden_topics:
            topics_prompt += f"Taqiqlangan mavzular: {', '.join(mannequin.forbidden_topics)}\n"
        if topics_prompt:
            topics_prompt += "\n"

        # ===== 3-qatlam: Ssenariy konteksti =====
        scenario_prompt = ""
        if scenario:
            scenario_prompt = (
                f"HOZIRGI SSENARIY: {scenario.title}\n"
                f"Tavsif: {scenario.description}\n"
            )
            if scenario.expected_actions:
                actions = scenario.expected_actions.get("actions", [])
                if actions:
                    scenario_prompt += f"Hamshira qilishi kerak: {', '.join(actions)}\n"
            scenario_prompt += "\n"

        # ===== 4-qatlam: Mos skriptlar konteksti =====
        script_context = ""
        if matched_scripts:
            script_context = "MAVJUD JAVOB SHABLONLARI (ulardan foydalanishing mumkin):\n"
            for s in matched_scripts[:5]:  # Max 5 ta
                script_context += f"- Savol haqida: '{', '.join(s.trigger_keywords or [])}' → Javob: '{s.answer_template}'\n"
            script_context += "\n"

        return base_rules + character_prompt + topics_prompt + scenario_prompt + script_context

    def validate_response(self, response_text: str, mannequin: Mannequin) -> tuple[bool, str]:
        """
        AI javobini tekshirish — qoidalarga zid bo'lsa tuzatish.
        
        Returns:
            (is_valid, safe_text) — javob to'g'rimi va tuzatilgan matn
        """
        text_lower = response_text.lower()

        # 1. AI o'zini oshkor qilayotganini tekshirish
        for phrase in self.FORBIDDEN_AI_PHRASES:
            if phrase.lower() in text_lower:
                logger.warning(f"AI o'zini oshkor qilmoqchi: '{phrase}' topildi")
                return False, self._get_rejection_response(mannequin)

        # 2. Taqiqlangan mavzularni tekshirish
        for topic in self.GLOBAL_FORBIDDEN_TOPICS:
            if topic.lower() in text_lower:
                logger.warning(f"Taqiqlangan mavzu topildi: '{topic}'")
                return False, self._get_rejection_response(mannequin)

        # 3. Manikenning maxsus taqiqlangan mavzularini tekshirish
        if mannequin.forbidden_topics:
            for topic in mannequin.forbidden_topics:
                if topic.lower() in text_lower:
                    logger.warning(f"Manikenning taqiqlangan mavzusi: '{topic}'")
                    return False, self._get_rejection_response(mannequin)

        # 4. Javob juda uzun emasligini tekshirish (manikenlar qisqa gapiradi)
        if len(response_text) > 500:
            response_text = response_text[:500].rsplit('.', 1)[0] + '.'
            logger.info("Javob qisqartirildi (500 belgidan oshgan)")

        return True, response_text

    def filter_inappropriate_content(self, text: str) -> str:
        """Kirish matnidagi noto'g'ri kontentni tozalash"""
        # Hozircha oddiy — kengaytirilishi mumkin
        return text.strip()

    def _get_rejection_response(self, mannequin: Mannequin) -> str:
        """Xarakterga mos 'tushunmadim' javobi"""
        rejections = {
            "bobo": "Tushunmadim bolam, nima deyapsan o'zi? Menga oddiyroq tushuntirib ber.",
            "homilador": "Iltimos, avval mening dardimga chora toping, buni tushunmadim.",
            "bola": "Tushunmadim, oyimni chaqiring!",
            "chaqaloq": "*yig'lash*"
        }
        return rejections.get(mannequin.slug, "Tushunmadim.")
