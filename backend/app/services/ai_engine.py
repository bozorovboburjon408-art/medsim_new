"""
MedSim AI Engine
Asosiy AI moduli — manikenlar uchun javob generatsiya qilish.
Skriptlardan keyword matching + LLM fallback + Guardrails validatsiyasi.
"""
import logging
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.guardrails import Guardrails
from app.db.models import Mannequin, Scenario, ScriptQA
from typing import List, Optional

logger = logging.getLogger(__name__)


class AIResponse(BaseModel):
    """AI javobining strukturasi"""
    text: str
    emotion: str = "oddiy"
    confidence: float = 1.0
    used_script_id: Optional[int] = None


class AIEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.guardrails = Guardrails()

    async def generate_response(
        self,
        mannequin: Mannequin,
        user_text: str,
        scenario: Optional[Scenario],
        matched_scripts: List[ScriptQA]
    ) -> AIResponse:
        """
        Manikenning javobini generatsiya qilish.
        
        Tartib:
        1. Avval to'g'ridan-to'g'ri skript moslashtirish (eng tez, eng ishonchli)
        2. Agar mos skript topilmasa → LLM orqali javob (guardrails bilan)
        3. Javob validatsiyasi (taqiqlangan kontentni tekshirish)
        """

        # ========== 1. Skript asosida javob ==========
        if matched_scripts:
            # Eng yuqori prioritetli skriptni olish
            best_script = matched_scripts[0]
            logger.info(
                f"Skript #{best_script.id} mos keldi: "
                f"keywords={best_script.trigger_keywords}, "
                f"emotion={best_script.emotion}"
            )
            return AIResponse(
                text=best_script.answer_template,
                emotion=best_script.emotion or "oddiy",
                confidence=1.0,
                used_script_id=best_script.id
            )

        # ========== 2. LLM orqali javob ==========
        system_prompt = self.guardrails.build_system_prompt(mannequin, scenario, matched_scripts)
        filtered_text = self.guardrails.filter_inappropriate_content(user_text)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": filtered_text}
                ],
                temperature=0.7,
                max_tokens=200,  # Manikenning javoblari qisqa bo'lishi kerak
            )

            raw_text = response.choices[0].message.content.strip()
            logger.info(f"LLM javob: '{raw_text[:100]}...'")

            # ========== 3. Guardrails validatsiyasi ==========
            is_valid, safe_text = self.guardrails.validate_response(raw_text, mannequin)
            if not is_valid:
                logger.warning(f"Guardrail buzildi, original: '{raw_text}'")

            # Emotsiyani aniqlash (oddiy heuristik)
            emotion = self._detect_emotion(safe_text, mannequin)

            return AIResponse(
                text=safe_text,
                emotion=emotion,
                confidence=0.85 if is_valid else 0.5
            )

        except Exception as e:
            logger.error(f"LLM API xatosi: {e}")
            # Xatolik bo'lsa xarakterga mos umumiy javob
            fallback = self._get_fallback_response(mannequin)
            return AIResponse(
                text=fallback,
                emotion="og'riqli",
                confidence=0.0
            )

    def _detect_emotion(self, text: str, mannequin: Mannequin) -> str:
        """Matn asosida emotsiyani aniqlash (sodda heuristik)"""
        text_lower = text.lower()

        # Og'riq belgilari
        pain_words = ["og'ri", "sanchiy", "aching", "qiynaly", "azob", "yomon"]
        if any(w in text_lower for w in pain_words):
            return "og'riqli"

        # Xavotir belgilari
        worry_words = ["xavotir", "qo'rq", "nima bo'ladi", "zarar", "xavfli"]
        if any(w in text_lower for w in worry_words):
            return "xavotirli"

        # Qo'rquv (bola uchun)
        fear_words = ["qo'rqaman", "yig'la", "oyim", "ukol", "ketgim"]
        if any(w in text_lower for w in fear_words):
            return "qo'rqqan"

        # Yig'lash (chaqaloq)
        if mannequin.use_preset_audio:
            return "yig'lash"

        return "oddiy"

    def _get_fallback_response(self, mannequin: Mannequin) -> str:
        """Xatolik bo'lganda xarakterga mos javob"""
        fallbacks = {
            "bobo": "Kechirasiz bolam, hozir biroz charchab qoldim... Keyinroq gaplashsak bo'ladimi?",
            "homilador": "Opa, menga biroz yomon bo'lyapti... Shifokorni chaqiring iltimos.",
            "bola": "Oyimni chaqiring! Oyim qani?!",
            "chaqaloq": "*yig'lash*"
        }
        return fallbacks.get(mannequin.slug, "Tushunmadim, iltimos qaytadan ayting.")
