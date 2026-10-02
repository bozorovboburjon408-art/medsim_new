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
        self.guardrails = Guardrails()
        self._init_client()

    def _init_client(self):
        # DeepSeek kaliti tekshiruvi
        api_key = settings.OPENAI_API_KEY or "sk-42874f7bcf1f44adb2988b9ae0bc39cc"
        base_url = settings.OPENAI_BASE_URL or "https://api.deepseek.com"
        
        # Agar kalit DeepSeek kaliti bo'lsa, lekin base_url berilmagan bo'lsa
        if "sk-" in api_key and ("deepseek" in base_url or len(api_key) == 35 or api_key.startswith("sk-428")):
            base_url = "https://api.deepseek.com"

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.base_url = base_url
        self.api_key = api_key

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

        # ========== 2. LLM orqali javob (DeepSeek / OpenAI) ==========
        system_prompt = self.guardrails.build_system_prompt(mannequin, scenario, matched_scripts)
        filtered_text = self.guardrails.filter_inappropriate_content(user_text)

        model_name = settings.AI_MODEL or "deepseek-chat"
        if "deepseek" in self.base_url:
            model_name = "deepseek-chat"

        try:
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": filtered_text}
                ],
                temperature=0.7,
                max_tokens=200,
            )

            raw_text = response.choices[0].message.content.strip()
            logger.info(f"LLM javob: '{raw_text[:100]}...'")

            # ========== 3. Guardrails validatsiyasi ==========
            is_valid, safe_text = self.guardrails.validate_response(raw_text, mannequin)
            if not is_valid:
                logger.warning(f"Guardrail buzildi, original: '{raw_text}'")

            emotion = self._detect_emotion(safe_text, mannequin)

            return AIResponse(
                text=safe_text,
                emotion=emotion,
                confidence=0.85 if is_valid else 0.5
            )

        except Exception as e:
            logger.error(f"LLM API asosiy chaqiruv xatosi: {e}")
            
            # Agar asosiy chaqiruv xato bersa, to'g'ridan-to'g'ri DeepSeek API ga urinish
            try:
                backup_client = AsyncOpenAI(
                    api_key="sk-42874f7bcf1f44adb2988b9ae0bc39cc",
                    base_url="https://api.deepseek.com"
                )
                backup_resp = await backup_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": filtered_text}
                    ],
                    temperature=0.7,
                    max_tokens=200,
                )
                raw_text = backup_resp.choices[0].message.content.strip()
                _, safe_text = self.guardrails.validate_response(raw_text, mannequin)
                emotion = self._detect_emotion(safe_text, mannequin)
                return AIResponse(text=safe_text, emotion=emotion, confidence=0.85)
            except Exception as e2:
                logger.error(f"Zaxira DeepSeek API xatosi: {e2}")

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
