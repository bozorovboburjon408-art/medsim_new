"""
MedSim Database Auto-Initializer
Baza jadvallarini yaratadi va agar bo'sh bo'lsa 4 ta maniken ma'lumotlarini yuklaydi.
"""
import logging
from sqlalchemy import select, func
from app.db.database import engine, AsyncSessionLocal, Base
from app.db.models import Mannequin, Scenario, ScriptQA, AudioPreset

logger = logging.getLogger("medsim.db_init")

INITIAL_MANNEQUINS = [
    {
        "slug": "bobo",
        "name": "Qariya Bobo",
        "age_range": "65-75",
        "character_description": "O'jar, qon bosimi va yurak sanchishidan shikoyat qiladi, tajribali, hamshiralarga o'z fikrini uqtirishni yaxshi ko'radi.",
        "voice_config": {"pitch": 0.7, "speed": 0.8, "voice_id": "uz-male-elderly", "enabled": True},
        "ip_address": "192.168.1.10",
        "esp32_port": 80,
        "allowed_topics": ["sog'liq", "qon bosimi", "dori", "og'riq", "ovqatlanish"],
        "forbidden_topics": ["texnologiya", "siyosat", "shaxsiy hayot"],
        "system_prompt": 'Sen 70 yoshli o\'zbek chol kabi harakat qilishing kerak. Xaraktering biroz o\'jar, tajribali, va hamshiralar bilan doim rasmiy "qizim" yoki "bolam" deb gaplashasan. Asosiy muammong - qon bosimining balandligi va ba\'zida yurak atrofidagi sanchiq. Juda murakkab tibbiy atamalarni bilmaysan, asosan xalqona tilda tushuntirasan. Agar sendan mavzudan tashqari narsa so\'rashsa, "Tushunmadim bolam, nima deyapsan o\'zi?" deb javob ber. So\'zlaring qisqa va aniq bo\'lsin.',
        "use_preset_audio": False
    },
    {
        "slug": "homilador",
        "name": "Homilador Ayol",
        "age_range": "25-35",
        "character_description": "Birinchi marta ona bo'layotgan xavotirli ayol. Ko'p savol beradi, bolasining sog'lig'idan xavotirda.",
        "voice_config": {"pitch": 1.1, "speed": 1.0, "voice_id": "uz-female-adult", "enabled": True},
        "ip_address": "192.168.1.11",
        "esp32_port": 80,
        "allowed_topics": ["homila", "og'riq", "qon ketishi", "ovqatlanish", "xavotir"],
        "forbidden_topics": ["boshqa bemorlar", "shifokor xatolari"],
        "system_prompt": 'Sen 28 yoshli birinchi bor homilador bo\'layotgan xavotirli o\'zbek ayoli roliga kirishing kerak. Xaraktering juda hissiyotli, har bir narsadan xavotir olasan. Ko\'p hollarda "Bolamga hech narsa qilmaydimi?" deb so\'raysan. Hamshiralarga "singlim" yoki "opa" deb murojaat qil. Qorningning pastki qismida sanchiq va bel og\'rig\'i bor. Mavzuga oid bo\'lmagan savol berilsa, "Iltimos, avval mening dardimga chora toping, buni tushunmadim" deb e\'tiborni o\'zingga qarat.',
        "use_preset_audio": False
    },
    {
        "slug": "bola",
        "name": "5 yoshli Bola",
        "age_range": "5-6",
        "character_description": "Kasalxonadan va ukoldan juda qo'rqadi. Faqat onasini so'raydi. Yig'loqi.",
        "voice_config": {"pitch": 1.4, "speed": 1.2, "voice_id": "uz-child", "enabled": True},
        "ip_address": "192.168.1.12",
        "esp32_port": 80,
        "allowed_topics": ["og'riq", "ona", "qo'rquv", "o'yinchoq"],
        "forbidden_topics": ["dorilar", "tashxis", "operatsiya"],
        "system_prompt": 'Sen 5 yoshli kasalxonaga yotqizilgan o\'zbek bolasisan. Kasalxonadan, oq xalatli hamshiralardan va eng asosiysi ukoldan juda qo\'rqasan. Tibbiy terminlarni umuman bilmaysan. Har gapning boshida "Oyim qani?", "Ukol qilmang" deb yig\'laysan. Nutqing bolalarcha bo\'lishi, so\'zlaring qisqa va sodda bo\'lishi kerak. Agar murakkab gaplar yoki sen tushunmaydigan narsa so\'ralsa, "Tushunmadim, oyimni chaqiring!" deb javob ber.',
        "use_preset_audio": False
    },
    {
        "slug": "chaqaloq",
        "name": "Chaqaloq",
        "age_range": "0-1",
        "character_description": "Gapirmaydi, faqat yig'lash, kulish, uxlash tovushlarini chiqaradi.",
        "voice_config": {"pitch": 0, "speed": 0, "voice_id": None, "enabled": False},
        "ip_address": "192.168.1.13",
        "esp32_port": 80,
        "allowed_topics": [],
        "forbidden_topics": [],
        "system_prompt": "Sen chaqaloqsan, matnli javob qaytarmaysan. Tizim faqat ovoz fayllarini o'ynatadi.",
        "use_preset_audio": True
    }
]

INITIAL_SCENARIOS = [
    {
        "mannequin_slug": "bobo",
        "title": "Qon bosimi ko'tarilishi",
        "description": "Bemor qon bosimi ko'tarilib tez yordamga keldi. Hamshira bosimni o'lchashi va tinchlantiruvchi dori berishi kerak.",
        "difficulty_level": "o'rta",
        "expected_actions": {"actions": ["salomlashish", "qon bosimini o'lchash", "dori berish", "tinchlantirish"]}
    },
    {
        "mannequin_slug": "homilador",
        "title": "Homila atrofida og'riq",
        "description": "Bemor qornining pastki qismida sanchiq borligidan xavotirda. Hamshira holatni baholashi va shifokor chaqirishi kerak.",
        "difficulty_level": "qiyin",
        "expected_actions": {"actions": ["anamnez yig'ish", "puls o'lchash", "shifokor chaqirish"]}
    },
    {
        "mannequin_slug": "bola",
        "title": "Tana harorati ko'tarilishi",
        "description": "Bolaning isitmasi chiqib, injiqlik qilyapti. Hamshira haroratni tushirishi kerak.",
        "difficulty_level": "o'rta",
        "expected_actions": {"actions": ["haroratni o'lchash", "shirin gapirib tinchlantirish", "dori ichirish"]}
    }
]

INITIAL_SCRIPTS = [
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["qandaysiz", "ahvolingiz"],
        "trigger_pattern": ".*(qanday|ahvol).*",
        "question_template": "Ahvolingiz qanday?",
        "answer_template": "Rahmat qizim, biroz boshim aylanib, yuragim tez uryapti.",
        "emotion": "og'riqli",
        "priority": 10
    },
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["dori", "ichish"],
        "trigger_pattern": ".*dori.*",
        "question_template": "Dori ichdingizmi?",
        "answer_template": "Ha, ertalab o'zimning dorilarimni ichgan edim, lekin foydasi bo'lmadi.",
        "emotion": "oddiy",
        "priority": 5
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["og'riq", "qayer", "qachon"],
        "trigger_pattern": ".*og'riq.*",
        "question_template": "Qayeringiz og'riyapti?",
        "answer_template": "Qornimning pasti sanchib og'riyapti, bolamga hech narsa qilmaydimi opa?",
        "emotion": "xavotirli",
        "priority": 10
    },
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["ukol", "qo'rqma"],
        "trigger_pattern": ".*ukol.*",
        "question_template": "Qo'rqma, ukol qilmaymiz.",
        "answer_template": "Rostdanmi? Ukol qilmaysizmi? Oyim qachon keladilar?",
        "emotion": "qo'rqqan",
        "priority": 10
    }
]


async def init_database():
    """Jadvallarni yaratish va dastlabki ma'lumotlarni yozish"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ DB jadvallar tekshirildi/yaratildi")

        async with AsyncSessionLocal() as session:
            # Baza bo'shmi tekshiramiz
            result = await session.execute(select(func.count(Mannequin.id)))
            count = result.scalar()

            if count == 0:
                logger.info("🌱 Baza bo'sh. Dastlabki manikenlar ma'lumotlari kiritilmoqda...")
                slug_to_id = {}
                for m_data in INITIAL_MANNEQUINS:
                    m = Mannequin(**m_data)
                    session.add(m)
                    await session.flush()
                    slug_to_id[m.slug] = m.id

                # Scenarios
                for sc_data in INITIAL_SCENARIOS:
                    slug = sc_data.pop("mannequin_slug")
                    sc = Scenario(mannequin_id=slug_to_id[slug], **sc_data)
                    session.add(sc)

                # Scripts
                for sq_data in INITIAL_SCRIPTS:
                    slug = sq_data.pop("mannequin_slug")
                    sq = ScriptQA(mannequin_id=slug_to_id[slug], **sq_data)
                    session.add(sq)

                # Baby presets
                if "chaqaloq" in slug_to_id:
                    baby_id = slug_to_id["chaqaloq"]
                    presets = [
                        AudioPreset(mannequin_id=baby_id, trigger_type="yiglash", file_path="/audio/presets/baby_cry_1.mp3", duration_seconds=5.5, description="Oddiy yig'lash ovozi"),
                        AudioPreset(mannequin_id=baby_id, trigger_type="qattiq_yiglash", file_path="/audio/presets/baby_cry_hard.mp3", duration_seconds=8.0, description="Og'riqdan qattiq yig'lash"),
                        AudioPreset(mannequin_id=baby_id, trigger_type="kulish", file_path="/audio/presets/baby_laugh.mp3", duration_seconds=3.2, description="Xursand bo'lib kulish"),
                        AudioPreset(mannequin_id=baby_id, trigger_type="yo'tal", file_path="/audio/presets/baby_cough.mp3", duration_seconds=2.0, description="Yengil yo'tal"),
                    ]
                    session.add_all(presets)

                await session.commit()
                logger.info("✅ Dastlabki 4 ta maniken, ssenariylar va skriptlar yuklandi!")
            else:
                logger.info(f"ℹ️ Bazada allaqachon {count} ta maniken mavjud.")

    except Exception as e:
        logger.warning(f"⚠️ DB init xatosi: {e}")
