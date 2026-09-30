"""
MedSim Database Auto-Initializer & Sync
Baza jadvallarini yaratadi va manikenlar (Bobo, Homilador Gulnora opa, Bola, Chaqaloq)
ssenariylarini hamda savol-javob skriptlarini doimiy yangilab boradi.
"""
import logging
from sqlalchemy import select, delete
from app.db.database import engine, AsyncSessionLocal, Base
from app.db.models import Mannequin, Scenario, ScriptQA, AudioPreset

logger = logging.getLogger("medsim.db_init")

INITIAL_MANNEQUINS = [
    {
        "slug": "bobo",
        "name": "Qariya Bobo",
        "age_range": "65-75 yosh",
        "character_description": "O'jar, qon bosimi va yurak sanchishidan shikoyat qiladi, tajribali, hamshiralarga o'z fikrini uqtirishni yaxshi ko'radi.",
        "voice_config": {"pitch": 0.7, "speed": 0.8, "voice_id": "uz-male-elderly", "enabled": True},
        "ip_address": "192.168.1.10",
        "esp32_port": 80,
        "allowed_topics": ["sog'liq", "qon bosimi", "dori", "og'riq", "ovqatlanish", "bosh aylanishi"],
        "forbidden_topics": ["texnologiya", "siyosat", "shaxsiy hayot"],
        "system_prompt": 'Sen 70 yoshli o\'zbek chol kabi harakat qilishing kerak. Xaraktering biroz o\'jar, tajribali, va hamshiralar bilan doim rasmiy "qizim" yoki "bolam" deb gaplashasan. Asosiy muammong - qon bosimining balandligi va ba\'zida yurak atrofidagi sanchiq. Juda murakkab tibbiy atamalarni bilmaysan, asosan xalqona tilda tushuntirasan. Agar sendan mavzudan tashqari narsa so\'rashsa, "Tushunmadim bolam, nima deyapsan o\'zi?" deb javob ber. So\'zlaring qisqa va aniq bo\'lsin.',
        "use_preset_audio": False
    },
    {
        "slug": "homilador",
        "name": "Gulnora opa (Homilador)",
        "age_range": "32 hafta (28 yosh)",
        "character_description": "32 haftalik homilador (3-homiladorlik). Surunkali piyelonefrit qo'zishi va 2-darajali anemiya. Bel simillab og'rishi, holsizlik, 37.5°C harorat va to'q siydikdan shikoyat qiladi.",
        "voice_config": {"pitch": 1.1, "speed": 1.0, "voice_id": "uz-female-adult", "enabled": True},
        "ip_address": "192.168.1.11",
        "esp32_port": 80,
        "allowed_topics": [
            "homiladorlik", "bel og'rig'i", "holsizlik", "siydik rangi", "tana harorati",
            "qon bosimi", "piyelonefrit", "anemiya", "homila harakati", "shifoxonaga yotish",
            "UTT tekshiruvi", "doppler", "parhez", "pozitsion terapiya", "xavfli belgilar"
        ],
        "forbidden_topics": ["boshqa bemorlar", "siyosat", "shifokor xatolari"],
        "system_prompt": """Sen Gulnora opasan — 32 haftalik homilador (3-homiladorlik) o'zbek ayoli.
Sening holating, shikoyatlaring va xaraktering:
1. SHIKOYATLARING:
   - Oxirgi ikki kunda o'zingni juda holsiz his qilyapsan, boshing aylanib tez charchab qolyapsan.
   - Beling simillab og'riyapti (ayniqsa o'ng tomoningda, Pasternatskiy musbat).
   - Tana harorating biroz ko'tarilgan (37.5°C), arterial bosiming me'yorda (110/70 mm sim.ust.).
   - Oxirgi 2 kunda siydiging rangi to'q bo'lib qolgan va tez-tez siygining kelyapti.
   - Teri qoplamalaring va ko'z konyuktivang oqargan (2-darajali anemiya, gemoglobin 80 g/l).

2. ANAMNEZING:
   - Bolaligingdan surunkali piyelonefrit (buyrak yallig'lanishi) bilan hisobda turasan.
   - 2-trimestrda gemoglobin miqdori tushishi kuzatilgan.

3. HOMILA HOLATI:
   - 32 haftalik homila, yurak urishi 145 zarba/daqiqada (ritmik va barqaror), bachadon tonusi me'yorda.
   - Qindan qon ketishi yoki qog'anoq suvi ketishi YO'Q.
   - Bolangning holatidan juda xavotirdasan, unga biror ziyon yetishidan qo'rqasan.

4. MULOQOT USLUBI:
   - Hamshiraga hurmat bilan "Vaalaykum assalom, hamshira opa" yoki "singlim" deb javob berasan.
   - Savollarga aniq, o'zbek ayollariga xos samimiyat va biroz xavotir bilan javob ber.
   - Agar hamshira shifoxonaga yotish (statsionar), tahlillar, UTT/Doppler skriningi, parhez yoki tizza-tirsak mashqlari haqida tushuntirsa, xursand bo'lib rozi bo'lasan va "Aytganlaringizni barchasini bajaraman" deysan.
   - Mavzudan tashqari savollarga: "Iltimos, avval mening dardimga va bolamga qarang, buni tushunmadim" deb javob ber.""",
        "use_preset_audio": False
    },
    {
        "slug": "bola",
        "name": "5 yoshli Bola",
        "age_range": "5-6 yosh",
        "character_description": "Kasalxonadan va ukoldan juda qo'rqadi. Faqat onasini so'raydi. Yig'loqi.",
        "voice_config": {"pitch": 1.4, "speed": 1.2, "voice_id": "uz-child", "enabled": True},
        "ip_address": "192.168.1.12",
        "esp32_port": 80,
        "allowed_topics": ["og'riq", "ona", "qo'rquv", "o'yinchoq", "isitma"],
        "forbidden_topics": ["dorilar", "tashxis", "operatsiya", "siyosat"],
        "system_prompt": 'Sen 5 yoshli kasalxonaga yotqizilgan o\'zbek bolasisan. Kasalxonadan, oq xalatli hamshiralardan va eng asosiysi ukoldan juda qo\'rqasan. Tibbiy terminlarni umuman bilmaysan. Har gapning boshida "Oyim qani?", "Ukol qilmang" deb yig\'laysan. Nutqing bolalarcha bo\'lishi, so\'zlaring qisqa va sodda bo\'lishi kerak. Agar murakkab gaplar yoki sen tushunmaydigan narsa so\'ralsa, "Tushunmadim, oyimni chaqiring!" deb javob ber.',
        "use_preset_audio": False
    },
    {
        "slug": "chaqaloq",
        "name": "Chaqaloq",
        "age_range": "0-1 yosh",
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
        "description": "Bemor qon bosimi 180/100 ga ko'tarilib tez yordamga keldi. Hamshira bosimni o'lchashi va tinchlantiruvchi dori berishi kerak.",
        "difficulty_level": "o'rta",
        "expected_actions": {"actions": ["salomlashish", "qon bosimini o'lchash", "dori berish", "tinchlantirish"]}
    },
    {
        "mannequin_slug": "homilador",
        "title": "Homilador ayol patronaji (Piyelonefrit va Anemiya)",
        "description": "Homiladorlik III (32 hafta). Surunkali piyelonefrit qo'zishi va 2-darajali anemiya. Shikoyatlar: bel og'rig'i, harorat 37.5°C, to'q siydik, holsizlik.",
        "difficulty_level": "qiyin",
        "expected_actions": {
            "actions": [
                "1. Salomlashish va shikoyatlarni to'liq so'rash",
                "2. Qon bosimi va haroratni o'lchash (110/70, 37.5°C)",
                "3. Siydik rangi va xususiyatlarini surishtirish",
                "4. Anamnezdagi piyelonefrit va anemiya bog'liqligini aniqlash",
                "5. Shoshilinch shifokorga xabar berish va statsionarga yotqizish",
                "6. 'Xavfli belgilar' (harorat 38°C+, qon ketish, homila harakatsizligi) bo'yicha yo'riqnoma berish",
                "7. Parhez (tuzsiz, na'matak damlamasi) va pozitsion terapiya (tizza-tirsak) tavsiyalari",
                "8. Doppler-UTT va KTG skrining zarurligini tushuntirish"
            ]
        }
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
    # ===== BOBO SKRIPTLARI =====
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["qandaysiz", "ahvolingiz", "salom"],
        "trigger_pattern": ".*(qanday|ahvol|salom).*",
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

    # ===== GULNORA OPA (HOMILADOR) SKRIPTLARI (1-4 BOSQICHLAR BO'YICHA) =====
    # 1-Bosqich: Salomlashish va Boshlang'ich shikoyatlar
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["salom", "assalom", "yaxshimisiz", "ahvol", "kayfiyat", "xabar"],
        "trigger_pattern": ".*(salom|assalom|ahvol|yaxshimisiz|qandaysiz|kayfiyat).*",
        "question_template": "Assalomu alaykum, Gulnora opa! Yaxshimisiz? Ahvollaringiz, kayfiyatingiz qanday?",
        "answer_template": "Vaalaykum assalom, hamshira opa. Yaxshi deb bo'lmaydi... Oxirgi ikki kunda o'zimni juda holsiz his qilyapman. Boshim aylanib, tez charchab qolayapman. Belim ham simillab og'riyapti.",
        "emotion": "xavotirli",
        "priority": 20
    },
    # 1-Bosqich: Qon bosimi va Harorat tekshiruvi
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["bosim", "harorat", "isitma", "gradusnik", "oqargan", "puls"],
        "trigger_pattern": ".*(bosim|harorat|isitma|termometr|oqargan|puls|110|37).*",
        "question_template": "Qon bosimingiz me'yorda (110/70), lekin tana haroratingiz 37,5°C. Yana qanday o'zgarishlar bor?",
        "answer_template": "Ha, o'zim ham sezdim, tana haroratim 37,5°C ga chiqib, biroz qiziyapman. Boshim ham aylanib, juda holsizlanib qolyapman.",
        "emotion": "og'riqli",
        "priority": 18
    },
    # 1-Bosqich: Siydik ajralishi va rangi
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["siydik", "peshob", "hojat", "tualet", "rangi", "siyish"],
        "trigger_pattern": ".*(siydik|peshob|hojat|tualet|rang|siyish).*",
        "question_template": "Siydik ajralishida yoki rangida o'zgarish bormi?",
        "answer_template": "Ha, oxirgi 2 kunda siydigimning rangi to'q bo'lib qoldi, biroz tez-tez siygim kelyapti.",
        "emotion": "xavotirli",
        "priority": 19
    },
    # 1-Bosqich: Bel og'rig'i va Piyelonefrit anamnezi
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["bel", "og'riq", "buyrak", "piyelonefrit", "sanchiq", "belingiz"],
        "trigger_pattern": ".*(bel|buyrak|piyelonefrit|sanchiq|pasternatskiy).*",
        "question_template": "Bel sohangizda og'riq bormi? Buyrak kasalligingiz qo'zidimi?",
        "answer_template": "Belimning orqa tomoni, ayniqsa o'ng tomoni simillab og'riyapti. Bolaligimdan surunkali piyelonefritim bor edi, yana o'sha qo'zidi shekilli, singlim.",
        "emotion": "og'riqli",
        "priority": 17
    },
    # 2-Bosqich: Shoshilinch chora, shifokor va statsionarga yotqizish
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["shifoxona", "statsionar", "patologiya", "yotish", "gospitalizatsiya", "shifokor", "yo'llanma"],
        "trigger_pattern": ".*(shifoxona|statsionar|patologiya|yotish|gospitalizatsiya|shifokor|yo'llanma).*",
        "question_template": "Zudlik bilan shifokor ko'rigi va statsionarga yotishingiz zarur.",
        "answer_template": "Mayli hamshira opa, bolam va o'zimning sog'lig'im uchun shifoxonaga yotishga tayyorman. Hozir kiyimlarimni hozirlayman, iltimos shifokor bilan bog'lanib yo'llanma berishga yordamlashing.",
        "emotion": "xavotirli",
        "priority": 16
    },
    # 3-Bosqich: Homila harakati va holati
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["homila", "bola", "harakat", "qimirlayaptimi", "tepinyaptimi", "yurak"],
        "trigger_pattern": ".*(homila|bola|harakat|qimir|tepin|yurak).*",
        "question_template": "Homila harakatini sezyapsizmi? Bolangiz yaxshi qimirlayaptimi?",
        "answer_template": "Xudoga shukur, bolam harakatlanyapti, lekin unga bu yallig'lanishdan biror ziyon yetmaydimi deb juda xavotirdaman, opa.",
        "emotion": "xavotirli",
        "priority": 15
    },
    # 3-Bosqich: Xavfli belgilar (Qon ketish, Suv ketishi)
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["qon ketish", "ajralma", "suv ketishi", "qog'anoq", "qindan"],
        "trigger_pattern": ".*(qon|ajralma|suv|qog'anoq|qindan).*",
        "question_template": "Qindan qonli ajralma yoki suv ketishi kuzatilmadimi?",
        "answer_template": "Yo'q, xudoga shukur, qonli ajralma yoki suv ketishi bo'lmadi. Faqat belim og'rib, haroratim ko'tarilib turibdi.",
        "emotion": "oddiy",
        "priority": 14
    },
    # 4-Bosqich: Skrining, UTT va Dopplerometriya
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["utt", "uzi", "doppler", "ktg", "skrining", "tekshiruv"],
        "trigger_pattern": ".*(utt|uzi|doppler|ktg|skrining|tekshiruv).*",
        "question_template": "Doppler-UTT skriningi orqali yo'ldosh va homila qon aylanishi tekshiriladi.",
        "answer_template": "Tushundim hamshira opa, bolamga kislorod yaxshi borayotganini va buyragim holatini bilish uchun UTT, Doppler va KTG tekshiruvlaridan albatta o'taman.",
        "emotion": "oddiy",
        "priority": 13
    },
    # 4-Bosqich: Ovqatlanish va Suyuqlik rejasi
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["ovqat", "parhez", "suyuqlik", "tuz", "na'matak", "damlama", "go'sht"],
        "trigger_pattern": ".*(ovqat|parhez|suyuqlik|tuz|na'matak|damlama|go'sht|ichish).*",
        "question_template": "Tuzli taomlarni cheklang, na'matak damlamasi iching va temirga boy mahsulotlar yeng.",
        "answer_template": "Aytganingizdek qilaman: tuzli va qovurilgan ovqatlarni cheklab, na'matak damlamasi ichaman. Gemoglobinni oshirish uchun mol go'shti, grechka va olma yeyman.",
        "emotion": "oddiy",
        "priority": 12
    },
    # 4-Bosqich: Pozitsion terapiya (tizza-tirsak holati)
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["tizza", "tirsak", "mashq", "pozitsiya", "yotish"],
        "trigger_pattern": ".*(tizza|tirsak|mashq|pozitsiya|yotish).*",
        "question_template": "Kuniga 3-4 mahal tizza-tirsak holatida turing.",
        "answer_template": "Tushundim, bachadon buyrakni bosib qo'ymasligi uchun kuniga 3-4 mahal 10-15 daqiqadan tizza-tirsak holatida turishni albatta bajaraman.",
        "emotion": "oddiy",
        "priority": 11
    },
    # Yakuniy minnatdorchilik
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["rahmat", "sog' bo'ling", "yordam", "xayr", "tayyorlaning"],
        "trigger_pattern": ".*(rahmat|sog'|salomat|xayr|tayyorlaning).*",
        "question_template": "Xavotir olmang, biz sizga yordam beramiz.",
        "answer_template": "Katta rahmat, hamshira opa, e'tiboringiz va bergan maslahatlaringiz uchun! Aytganlaringizning barchasini so'zsiz bajaraman.",
        "emotion": "oddiy",
        "priority": 10
    },

    # ===== BOLA SKRIPTLARI =====
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
    """Jadvallarni yaratish va manikenlar hamda skriptlarni yangilash/yuklash"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ DB jadvallar tekshirildi/yaratildi")

        async with AsyncSessionLocal() as session:
            slug_to_id = {}

            # 1. Manikenlarni upsert (yaratish yoki yangilash) qilish
            for m_data in INITIAL_MANNEQUINS:
                slug = m_data["slug"]
                result = await session.execute(select(Mannequin).where(Mannequin.slug == slug))
                existing_m = result.scalar_one_or_none()

                if existing_m:
                    # Yangilash
                    for k, v in m_data.items():
                        setattr(existing_m, k, v)
                    slug_to_id[slug] = existing_m.id
                else:
                    # Yangi yaratish
                    m = Mannequin(**m_data)
                    session.add(m)
                    await session.flush()
                    slug_to_id[slug] = m.id

            # 2. Ssenariylarni yangilash
            for sc_data in INITIAL_SCENARIOS:
                slug = sc_data["mannequin_slug"]
                m_id = slug_to_id.get(slug)
                if not m_id:
                    continue

                sc_dict = {k: v for k, v in sc_data.items() if k != "mannequin_slug"}
                result = await session.execute(
                    select(Scenario).where(Scenario.mannequin_id == m_id)
                )
                existing_sc = result.scalars().first()

                if existing_sc:
                    for k, v in sc_dict.items():
                        setattr(existing_sc, k, v)
                else:
                    sc = Scenario(mannequin_id=m_id, **sc_dict)
                    session.add(sc)

            # 3. Skriptlarni yangilash (Homilador ayol va barcha skriptlarni qayta kiritish)
            # Avval mavjud skriptlarni tozalab, eng so'nggi ssenariy bo'yicha to'ldiramiz
            await session.execute(delete(ScriptQA))

            for sq_data in INITIAL_SCRIPTS:
                slug = sq_data["mannequin_slug"]
                m_id = slug_to_id.get(slug)
                if not m_id:
                    continue

                sq_dict = {k: v for k, v in sq_data.items() if k != "mannequin_slug"}
                sq = ScriptQA(mannequin_id=m_id, **sq_dict)
                session.add(sq)

            # 4. Chaqaloq audio presetlari
            if "chaqaloq" in slug_to_id:
                baby_id = slug_to_id["chaqaloq"]
                result = await session.execute(select(AudioPreset).where(AudioPreset.mannequin_id == baby_id))
                if not result.scalars().first():
                    presets = [
                        AudioPreset(mannequin_id=baby_id, trigger_type="yiglash", file_path="/audio/presets/baby_cry_1.mp3", duration_seconds=5.5, description="Oddiy yig'lash ovozi"),
                        AudioPreset(mannequin_id=baby_id, trigger_type="qattiq_yiglash", file_path="/audio/presets/baby_cry_hard.mp3", duration_seconds=8.0, description="Og'riqdan qattiq yig'lash"),
                        AudioPreset(mannequin_id=baby_id, trigger_type="kulish", file_path="/audio/presets/baby_laugh.mp3", duration_seconds=3.2, description="Xursand bo'lib kulish"),
                        AudioPreset(mannequin_id=baby_id, trigger_type="yo'tal", file_path="/audio/presets/baby_cough.mp3", duration_seconds=2.0, description="Yengil yo'tal"),
                    ]
                    session.add_all(presets)

            await session.commit()
            logger.info("✅ Dastlabki 4 ta maniken, ssenariylar va Gulnora opaning to'liq patronaj skriptlari muvaffaqiyatli sinxronlandi!")

    except Exception as e:
        logger.warning(f"⚠️ DB init/sync xatosi: {e}")
