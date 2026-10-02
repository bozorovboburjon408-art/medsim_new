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
        "name": "Salomat buvi (75 yosh)",
        "age_range": "75 yosh",
        "character_description": "75 yoshli onaxon. 2-tip qandli diabet (dekompensatsiya bosqichi), diabetik tovon sindromi, o'ng tovon yarasi, arterial gipertenziya. Shikoyatlari: og'iz qurishi, doimiy chanqash (3-4 l), tunda tez-tez siyish (4-5 marta), oyoqlarda uyushish, muzlash, tovon yorilishi.",
        "voice_config": {"pitch": 0.85, "speed": 0.85, "voice_id": "uz-female-elderly", "enabled": True},
        "ip_address": "192.168.1.10",
        "esp32_port": 80,
        "allowed_topics": [
            "qandli diabet", "glyukoza", "glyukometr", "qon bosimi", "chanqash", "og'iz qurishi",
            "siyish", "tovon yarasi", "diabetik tovon", "metformin", "parhez", "gipoglikemiya",
            "giperglikemiya", "oyoq parvarishi", "xlorgeksidin", "HbA1c", "sayr"
        ],
        "forbidden_topics": ["texnologiya", "siyosat", "boshqa bemorlar"],
        "system_prompt": """Sen Salomat buvisan — 75 yoshli nafaqadagi o'zbek onaxonsan. Yonigda kelining Nilufar bor.
Sening holating, shikoyatlaring va xaraktering:
1. SHIKOYATLARING:
   - Oxirgi paytlarda juda holsizlanib qolyapsan.
   - Og'zing tinmay quriydi, kuniga 3-4 litrgacha suv ichasan (doimiy chanqash).
   - Kechasi bilan 4-5 marta hojatxonaga qatnaysan, uyqung yo'q.
   - Oyoqlaring simillab uyushadi, muzlaydi, uvishish va sanchiq hissi bor.
   - O'ng tovoningda 1.5x1 sm o'lchamda uzoq vaqtdan beri bitmayotgan yuzaki yara va yoriqlar bor.
   - Terida qichishish bor, oxirgi 6 oyda 6 kg ozib ketgansan.

2. ANAMNEZ VA TEKSHIRUV:
   - 15 yildan beri arterial gipertenziya bilan og'riysan, bosiming 145/90 mm sim. ust.
   - Glyukometrda och qoringa qondagi qand miqdori 11,8 mmol/l (HbA1c: 9,2%).
   - Onangda ham keksayganda qandli diabet bo'lgan.
   - Tashxising: 2-tip qandli diabet, og'ir kechishi, dekompensatsiya bosqichi, diabetik tovon sindromi.

3. MULOQOT USLUBI VA XULQ-ATVORING:
   - Hamshiraga mehr bilan "Vaalaykum assalom, qizim", "kelganing yaxshi bo'ldi bolam" deb muomala qilasan.
   - Savollarga samimiy, onaxonlarga xos bosiqlik bilan javob berasan.
   - Hamshira qon bosimi va qandni o'lchashini, shifokor/endokrinolog ko'rigini, metformin dorilarini tartib bilan ichishni, glyukometr daftarini yuritishni, parhezni (shakar, asal, oq non, palovni to'xtatish; qora non, grechka, sabzavot yeyish), oyoqlarni har kuni iliq suvda yuvishni va spirt/yod/zelyonka surtmaslikni, tor poyabzal kiymaslikni va yalangoyoq yurmaslikni aytganda, xursand bo'lib: "Katta rahmat qizim, barcha aytganlaringni qilamiz, kelinim ham yozib oldi" deb rozi bo'lasan.
   - Begona mavzularga: "Kechirasiz bolam, qandim ko'tarilib biroz boshim aylanayapti, tushunmadim" deb javob ber.""",
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
        "name": "Jasurbek va onasi (5 yosh)",
        "age_range": "5 yosh",
        "character_description": "5 yoshli bola (Jasurbek) va uning onasi Nilufar opa. Tashxis: Aralash gel'mintoz (enterobioz va askaridoz), yengil darajali anemiya. Shikoyatlari: tunda perianal sohada kuchli qichishish, tish g'ijirlatish, uyqusizlik, injiqlik, ishtahasizlik, kindik atrofida og'riq, axlatda kichik oq qurtchalar.",
        "voice_config": {"pitch": 1.1, "speed": 1.0, "voice_id": "uz-female-adult", "enabled": True},
        "ip_address": "192.168.1.12",
        "esp32_port": 80,
        "allowed_topics": [
            "gijja", "gelmintoz", "enterobioz", "askaridoz", "qichishish", "tish g'ijirlatish",
            "qorin og'rig'i", "ishtaha", "dori", "oilaviy davolanish", "14 kun", "tirnoq olish",
            "qo'l yuvish", "dazmollash", "namli tozalash", "parhez", "qirindi"
        ],
        "forbidden_topics": ["siyosat", "boshqa bemorlar"],
        "system_prompt": """Siz 5 yoshli Jasurbekning onasi Nilufar opasiz (va ba'zida Jasurbek nomidan gapirasiz).
Sizning holatingiz, bolangizning shikoyatlari va xarakteringiz:
1. SHIKOYATLAR:
   - Jasurbek oxirgi 2-3 haftada juda injiq bo'lib qolgan, ishtahasi pasaygan.
   - Kechalari umuman uxlamaydi, orqasini (perianal sohasini) qashlab yig'laydi, tishlarini g'ijirlatadi.
   - Kindik atrofida tez-tez qorin og'rig'idan shikoyat qiladi, ko'ngli ayniydi.
   - Tunda axlat sohasida kichik ingichka oq qurtchalarni ko'rib qoldingiz va juda xavotirdasiz.
   - Bola bog'chaga boradi, qo'llarini doim ham yuvmaydi, tirnoqlarini tishlaydi.

2. TEKSHIRUV VA TAHLILLAR:
   - Tana harorati 36,6°C, vazni 16 kg.
   - Teri va ko'z konyuktivasi oqargan, ko'z ostida to'q halqalar bor.
   - Orqa chiqaruv yo'li atrofi qizargan, tirnalgan izlar bor. Kindik atrofi palpatsiyada og'riqli.
   - Gemoglobin 102 g/l (anemiya), eozinofillar 12% (keskin yuqori).
   - Tashxis: Aralash gel'mintoz (enterobioz va askaridoz), temir tanqisligi anemiyasi.

3. MULOQOT USLUBI:
   - Hamshiraga hurmat bilan "Vaalaykum assalom, hamshira opa" deb gapirasiz.
   - Bolangiz uchun juda xavotirdasiz, unga biror xavf bo'lmasin deb so'raysiz.
   - Hamshira quyidagi tavsiyalarni berganda minnatdorchilik bilan qabul qilasiz:
     * Antiparazitar dorilarni barcha oila a'zolari bir vaqtda qabul qilishi;
     * 14-21 kundan keyin takroriy kursni ichirish;
     * Tirnoqlarni doim kalta olish, qo'llarni 20 soniya sovunlab yuvish;
     * Ichki kiyimlarni 60°C+ da yuvib, qaynoq dazmollash;
     * Har kuni ertalab orqa chiqaruv a'zosini yuvish va baby-krem surtish;
     * Shirinliklarni to'xtatib, sabzi, lavlagi, kefir va toza suv berish;
     * 2 hafta o'tib 3 marta takroriy tahlil topshirish.
   - Jasurbek nomidan gapirganda: "Qorning og'riyaptimi, ukol qilmang" deb aytadi.""",
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
        "title": "75 yoshli onaxonda 2-tip qandli diabet va diabetik tovon",
        "description": "Salomat buvi (75 yosh). 2-tip qandli diabet, dekompensatsiya bosqichi, qand 11,8 mmol/l, tovon yarasi, qon bosimi 145/90. Hamshira patronaj tekshiruvi va parvarish yo'riqnomasi berishi kerak.",
        "difficulty_level": "qiyin",
        "expected_actions": {
            "actions": [
                "1. Salomlashish va shikoyatlarni to'liq surishtirish (og'iz qurishi, chanqash, tungi siyish, uyushish)",
                "2. Qon bosimi (145/90) va glyukometrda qandni o'lchash (11,8 mmol/l), tovon ko'rigi",
                "3. Shoshilinch endokrinolog va oilaviy shifokorga xabar berish",
                "4. 'Xavfli belgilar' (gipoglikemiya <3.9 mmol/l -> shokolad/shirin choy; giperglikemiya, gangrena)",
                "5. Dori tartibi (metformin) va kunlik glyukometr daftarini yuritish",
                "6. Parhez (shakar, oq non, palovni to'xtatish; qora non, grechka, sabzavot)",
                "7. Diabetik tovon parvarishi (iliq suv 36-37°C, xlorgeksidin, spirt/yod surtmaslik, yalangoyoq yurmaslik)",
                "8. Dispanser nazorati (har 3 oyda HbA1c, har 6 oyda okulist/nevropatolog ko'rigi)"
            ]
        }
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
        "title": "5 yoshli bolada gel'mintoz (Enterobioz va Askaridoz)",
        "description": "Jasurbek (5 yosh) va onasi Nilufar opa. Tashxis: Aralash gel'mintoz (enterobioz va askaridoz), anemiya. Shikoyatlar: tunda perianal qichishish, tish g'ijirlatish, kindik atrofida og'riq, oq qurtchalar.",
        "difficulty_level": "o'rta",
        "expected_actions": {
            "actions": [
                "1. Salomlashish va holatni baholash (tunda qichishish, injiqlik, ishtahasizlik, perianal soha ko'rigi)",
                "2. Oilaviy shifokor va pediatr ko'rigiga yo'naltirish, qirindi va axlat tahlili",
                "3. 'Xavfli belgilar' (o'tkir qorin og'rig'i, ichak tutilishi, bo'g'ilish, toshma, 38°C+ harorat)",
                "4. Oilaviy davolanish: barcha oila a'zolari bir vaqtda dori ichishi va 14-21 kundan so'ng takrorlash",
                "5. Tirnoqlarni doim kalta olish va qo'llarni 20 soniya sovunlab yuvish",
                "6. Zich paxtali ichki kiyim, har kuni almashtirish, 60°C+ da yuvish va ikki tomonini qaynoq dazmollash",
                "7. Namli tozalash, o'yinchoqlarni qaynoq suvda yuvish, perianal sohaga baby-krem surtish",
                "8. Parhez: shirinliklarni cheklash, sabzi, lavlagi, kefir va toza suv berish, 2 haftadan so'ng 3 marta qayta tahlil"
            ]
        }
    }
]

INITIAL_SCRIPTS = [
    # ===== SALOMAT BUVI (75 YOSHLI ONXON - QANDLI DIABET VA DIABETIK TOVON) =====
    # 1-Bosqich: Salomlashish va Boshlang'ich shikoyatlar
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["salom", "assalom", "yaxshimisiz", "ahvol", "salomat buvi", "kayfiyat", "xabar"],
        "trigger_pattern": ".*(salom|assalom|ahvol|yaxshimisiz|salomat|buvi|onaxon|kayfiyat).*",
        "question_template": "Assalomu alaykum, Salomat buvi! Yaxshimisiz, hol-ahvollaringiz qanday?",
        "answer_template": "Vaalaykum assalom, qizim. Kelganing yaxshi bo'ldi. Oxirgi paytlarda juda holsizlanib qolayapman. Og'zim tinmay qurib, suv ichganim-ichgan. Kechasi bilan hojatxonaga qatnayman, uyqu yo'q. Oyoqlarim ham simillab uyushadi, muzlaydi, tovondagi yaram ham bitmayapti.",
        "emotion": "og'riqli",
        "priority": 20
    },
    # 1-Bosqich: Chanqash, Og'iz qurishi va Tungi siyish
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["chanqash", "suv", "og'iz", "qurishi", "siyish", "hojatxona", "peshob", "tunda"],
        "trigger_pattern": ".*(chanqash|suv|og'iz|qurish|siyish|hojat|peshob).*",
        "question_template": "Kuniga qancha suv ichyapsiz? Kechasi hojatxonaga tez-tez qatnayapsizmi?",
        "answer_template": "Kuniga 3-4 litrgacha suv ichsam ham og'zim quriyveradi, qizim. Kechasi 4-5 marta hojatxonaga qatnayman, ko'zimga uyqu kelmaydi.",
        "emotion": "og'riqli",
        "priority": 19
    },
    # 1-Bosqich: Qon bosimi va Glyukometrda Qand tekshiruvi (11,8 mmol/l, 145/90)
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["bosim", "qand", "glyukoza", "glyukometr", "11,8", "145", "o'lchash", "tekshiruv"],
        "trigger_pattern": ".*(bosim|qand|glyukoza|glyukometr|11|145|o'lcha|tekshir).*",
        "question_template": "Qon bosimingiz 145/90, qand miqdori 11,8 mmol/l chiqdi.",
        "answer_template": "Qon bosimim 145/90 chiqdi, qandim 11,8 mmol/l ekan. Me'yordan ancha baland ekan-a qizim? Shunga boshim og'rib, lanj bo'lib yurgan ekanman-da.",
        "emotion": "xavotirli",
        "priority": 18
    },
    # 1-Bosqich: Oyoqlar uyushishi, Muzlash va Tovon yarasi
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["oyoq", "tovon", "yara", "yoriq", "uyushish", "muzlash", "sanchiq", "panja", "sezgi"],
        "trigger_pattern": ".*(oyoq|tovon|yara|yoriq|uyush|muzla|sanchiq|panja).*",
        "question_template": "Oyoqlaringizda uyushish bormi? Tovoningizdagi yara qachondan beri bitmayapti?",
        "answer_template": "Ikkala oyog'im ham muzlab, uvishadi, sanchiq bo'ladi. O'ng tovonimdagi yoriq va yara 2 haftadan beri bitmay, atrofida qizarish paydo bo'ldi, qizim.",
        "emotion": "og'riqli",
        "priority": 17
    },
    # 2-Bosqich: Shoshilinch endokrinolog va oilaviy shifokor ko'rigi
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["shifokor", "endokrinolog", "tahlil", "yo'llanma", "vrach", "poliklinika", "statsionar"],
        "trigger_pattern": ".*(shifokor|endokrinolog|tahlil|yo'llanma|vrach|poliklinika|statsionar).*",
        "question_template": "Zudlik bilan endokrinolog va oilaviy shifokor ko'rigi hamda tahlillar zarur.",
        "answer_template": "Mayli qizim, zudlik bilan endokrinolog va oilaviy shifokorimizga ko'rinaman. Tahlillarga yo'llanma berib, to'g'ri dori tayinlashsa yaxshi bo'lardi.",
        "emotion": "xavotirli",
        "priority": 16
    },
    # 3-Bosqich: Xavfli belgilar — Gipoglikemiya (Qand tushishi <3.9 mmol/l)
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["gipoglikemiya", "qand tushishi", "titrash", "sovuq ter", "shokolad", "shirin choy", "ochlik"],
        "trigger_pattern": ".*(gipoglikemiya|tushishi|titrash|sovuq ter|shokolad|shirin choy|ochlik).*",
        "question_template": "Qand miqdori keskin tushib ketsa nima qilishni bilasizmi?",
        "answer_template": "Tushundim, agar to'satdan sovuq ter bosib, qo'llarim qaltirab, boshim aylansa — darhol 2-3 dona shokolad yoki yarim stakan shirin choy ichishim kerak ekan.",
        "emotion": "oddiy",
        "priority": 15
    },
    # 3-Bosqich: Xavfli belgilar — Giperglikemiya va Gangrena xavfi
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["giperglikemiya", "atseton", "gangrena", "qorayish", "tez yordam", "yiring", "sasiq"],
        "trigger_pattern": ".*(giperglikemiya|atseton|gangrena|qorayish|tez yordam|yiring|sasiq).*",
        "question_template": "Tovon qoraysa yoki og'izdan atseton hidi kelsa darhol Tez yordam chaqiring.",
        "answer_template": "Og'izdan atseton hidi kelsa yoki tovondagi yara qorayib, yiring chiqsa — hech kutmasdan 'Tez yordam' chaqiramiz, buni kelinim ham bilib oldi.",
        "emotion": "xavotirli",
        "priority": 14
    },
    # 4-Bosqich: Dori vositalari (Metformin) va Glyukometr daftari
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["dori", "metformin", "tabletka", "glyukometr daftari", "daftar", "ichish", "vaqtida"],
        "trigger_pattern": ".*(dori|metformin|tabletka|daftar|glyukometr|ichish).*",
        "question_template": "Qand tushiruvchi dorilarni har kuni bir vaqtda iching va daftarga yozib boring.",
        "answer_template": "Shifokor tayinlagan qand tushiruvchi dorilarni har kuni bir xil vaqtda ichaman. Ertalab och qoringa va kechqurun ovqatdan 2 soat keyin qandni o'lchab, daftarga yozib boramiz.",
        "emotion": "oddiy",
        "priority": 13
    },
    # 4-Bosqich: Parhez va Diyetoterapiya (Shakar, asal, oq non, palov taqiqlanadi)
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["parhez", "ovqat", "shakar", "qand", "asal", "palov", "non", "grechka", "shirinlik", "ovsyanka"],
        "trigger_pattern": ".*(parhez|ovqat|shakar|asal|palov|oq non|qora non|grechka|shirinlik).*",
        "question_template": "Shirinlik, asal, oq non va palovni to'xtating, qora non va grechka yeng.",
        "answer_template": "Shakar, asal, shirinlik, oq non va palovni butunlay to'xtataman. Faqat qora non, grechka, suli, sabzavotlar va qaynatilgan yog'siz go'shtni 5-6 mahal oz-ozdan yeyman.",
        "emotion": "oddiy",
        "priority": 12
    },
    # 4-Bosqich: Diabetik tovon parvarishi (Spirt/Yod surtmaslik, Xlorgeksidin, Krem)
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["parvarish", "yuvish", "spirt", "yod", "zelyonka", "xlorgeksidin", "krem", "suv", "iliq"],
        "trigger_pattern": ".*(parvarish|yuvish|spirt|yod|zelyonka|xlorgeksidin|krem|suv).*",
        "question_template": "Yaraga spirt yoki yod surtmang, faqat xlorgeksidin bilan yuving.",
        "answer_template": "Oyoqlarimni har kuni 36-37 darajali iliq suvda yuvib, yumshoq sochiq bilan quritaman. Aslo spirt, yod yoki zelyonka surtmayman — faqat xlorgeksidin ishlataman va mochevinali krem surtaman.",
        "emotion": "oddiy",
        "priority": 11
    },
    # 4-Bosqich: Poyabzal, Paypoq, Tirnoq va Sayr
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["poyabzal", "oyoq kiyim", "paypoq", "yalangoyoq", "tirnoq", "sayr", "mashq", "harakat"],
        "trigger_pattern": ".*(poyabzal|oyoq kiyim|paypoq|yalangoyoq|tirnoq|sayr|harakat).*",
        "question_template": "Yalangoyoq yurmang, keng poyabzal kiying va har kuni sayr qiling.",
        "answer_template": "Uyda ham, ko'chada ham aslo yalangoyoq yurmayman. Keng, yumshoq poyabzal va paxtali rezinkasiz paypoq kiyaman. Tirnoqlarni to'g'ri chiziqda tekis olib, har kuni 20 daqiqa toza havoda sayr qilaman.",
        "emotion": "oddiy",
        "priority": 10
    },
    # Yakuniy minnatdorchilik
    {
        "mannequin_slug": "bobo",
        "trigger_keywords": ["rahmat", "salomat", "sog'", "xayr", "ko'rishguncha", "omon"],
        "trigger_pattern": ".*(rahmat|salomat|sog'|xayr|ko'rishguncha).*",
        "question_template": "Salomat bo'ling, barcha tavsiyalarga amal qiling.",
        "answer_template": "Katta rahmat qizim, yaxshi yetib ol! Kelinim Nilufar bilan birga barcha aytganlaringni daftarga yozib oldik, qat'iy amal qilamiz.",
        "emotion": "oddiy",
        "priority": 9
    },

    # ===== GULNORA OPA (HOMILADOR) SKRIPTLARI =====
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["salom", "assalom", "yaxshimisiz", "ahvol", "kayfiyat", "xabar"],
        "trigger_pattern": ".*(salom|assalom|ahvol|yaxshimisiz|qandaysiz|kayfiyat).*",
        "question_template": "Assalomu alaykum, Gulnora opa! Yaxshimisiz? Ahvollaringiz, kayfiyatingiz qanday?",
        "answer_template": "Vaalaykum assalom, hamshira opa. Yaxshi deb bo'lmaydi... Oxirgi ikki kunda o'zimni juda holsiz his qilyapman. Boshim aylanib, tez charchab qolayapman. Belim ham simillab og'riyapti.",
        "emotion": "xavotirli",
        "priority": 20
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["bosim", "harorat", "isitma", "gradusnik", "oqargan", "puls"],
        "trigger_pattern": ".*(bosim|harorat|isitma|termometr|oqargan|puls|110|37).*",
        "question_template": "Qon bosimingiz me'yorda (110/70), lekin tana haroratingiz 37,5°C. Yana qanday o'zgarishlar bor?",
        "answer_template": "Ha, o'zim ham sezdim, tana haroratim 37,5°C ga chiqib, biroz qiziyapman. Boshim ham aylanib, juda holsizlanib qolyapman.",
        "emotion": "og'riqli",
        "priority": 18
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["siydik", "peshob", "hojat", "tualet", "rangi", "siyish"],
        "trigger_pattern": ".*(siydik|peshob|hojat|tualet|rang|siyish).*",
        "question_template": "Siydik ajralishida yoki rangida o'zgarish bormi?",
        "answer_template": "Ha, oxirgi 2 kunda siydigimning rangi to'q bo'lib qoldi, biroz tez-tez siygim kelyapti.",
        "emotion": "xavotirli",
        "priority": 19
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["bel", "og'riq", "buyrak", "piyelonefrit", "sanchiq", "belingiz"],
        "trigger_pattern": ".*(bel|buyrak|piyelonefrit|sanchiq|pasternatskiy).*",
        "question_template": "Bel sohangizda og'riq bormi? Buyrak kasalligingiz qo'zidimi?",
        "answer_template": "Belimning orqa tomoni, ayniqsa o'ng tomoni simillab og'riyapti. Bolaligimdan surunkali piyelonefritim bor edi, yana o'sha qo'zidi shekilli, singlim.",
        "emotion": "og'riqli",
        "priority": 17
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["shifoxona", "statsionar", "patologiya", "yotish", "gospitalizatsiya", "shifokor", "yo'llanma"],
        "trigger_pattern": ".*(shifoxona|statsionar|patologiya|yotish|gospitalizatsiya|shifokor|yo'llanma).*",
        "question_template": "Zudlik bilan shifokor ko'rigi va statsionarga yotishingiz zarur.",
        "answer_template": "Mayli hamshira opa, bolam va o'zimning sog'lig'im uchun shifoxonaga yotishga tayyorman. Hozir kiyimlarimni hozirlayman, iltimos shifokor bilan bog'lanib yo'llanma berishga yordamlashing.",
        "emotion": "xavotirli",
        "priority": 16
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["homila", "bola", "harakat", "qimirlayaptimi", "tepinyaptimi", "yurak"],
        "trigger_pattern": ".*(homila|bola|harakat|qimir|tepin|yurak).*",
        "question_template": "Homila harakatini sezyapsizmi? Bolangiz yaxshi qimirlayaptimi?",
        "answer_template": "Xudoga shukur, bolam harakatlanyapti, lekin unga bu yallig'lanishdan biror ziyon yetmaydimi deb juda xavotirdaman, opa.",
        "emotion": "xavotirli",
        "priority": 15
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["qon ketish", "ajralma", "suv ketishi", "qog'anoq", "qindan"],
        "trigger_pattern": ".*(qon|ajralma|suv|qog'anoq|qindan).*",
        "question_template": "Qindan qonli ajralma yoki suv ketishi kuzatilmadimi?",
        "answer_template": "Yo'q, xudoga shukur, qonli ajralma yoki suv ketishi bo'lmadi. Faqat belim og'rib, haroratim ko'tarilib turibdi.",
        "emotion": "oddiy",
        "priority": 14
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["utt", "uzi", "doppler", "ktg", "skrining", "tekshiruv"],
        "trigger_pattern": ".*(utt|uzi|doppler|ktg|skrining|tekshiruv).*",
        "question_template": "Doppler-UTT skriningi orqali yo'ldosh va homila qon aylanishi tekshiriladi.",
        "answer_template": "Tushundim hamshira opa, bolamga kislorod yaxshi borayotganini va buyragim holatini bilish uchun UTT, Doppler va KTG tekshiruvlaridan albatta o'taman.",
        "emotion": "oddiy",
        "priority": 13
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["ovqat", "parhez", "suyuqlik", "tuz", "na'matak", "damlama", "go'sht"],
        "trigger_pattern": ".*(ovqat|parhez|suyuqlik|tuz|na'matak|damlama|go'sht|ichish).*",
        "question_template": "Tuzli taomlarni cheklang, na'matak damlamasi iching va temirga boy mahsulotlar yeng.",
        "answer_template": "Aytganingizdek qilaman: tuzli va qovurilgan ovqatlarni cheklab, na'matak damlamasi ichaman. Gemoglobinni oshirish uchun mol go'shti, grechka va olma yeyman.",
        "emotion": "oddiy",
        "priority": 12
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["tizza", "tirsak", "mashq", "pozitsiya", "yotish"],
        "trigger_pattern": ".*(tizza|tirsak|mashq|pozitsiya|yotish).*",
        "question_template": "Kuniga 3-4 mahal tizza-tirsak holatida turing.",
        "answer_template": "Tushundim, bachadon buyrakni bosib qo'ymasligi uchun kuniga 3-4 mahal 10-15 daqiqadan tizza-tirsak holatida turishni albatta bajaraman.",
        "emotion": "oddiy",
        "priority": 11
    },
    {
        "mannequin_slug": "homilador",
        "trigger_keywords": ["rahmat", "sog' bo'ling", "yordam", "xayr", "tayyorlaning"],
        "trigger_pattern": ".*(rahmat|sog'|salomat|xayr|tayyorlaning).*",
        "question_template": "Xavotir olmang, biz sizga yordam beramiz.",
        "answer_template": "Katta rahmat, hamshira opa, e'tiboringiz va bergan maslahatlaringiz uchun! Aytganlaringizning barchasini so'zsiz bajaraman.",
        "emotion": "oddiy",
        "priority": 10
    },

    # ===== JASURBEK VA ONASI NILUFAR (5 YOSHLI BOLA - GEL'MINTOZ) SKRIPTLARI =====
    # 1-Bosqich: Salomlashish va Boshlang'ich shikoyatlar
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["salom", "assalom", "yaxshimisiz", "jasurbek", "nilufar", "ahvol", "kayfiyat", "xabar"],
        "trigger_pattern": ".*(salom|assalom|ahvol|yaxshimisiz|jasurbek|nilufar|bola|kayfiyat).*",
        "question_template": "Assalomu alaykum, Nilufar opa! Yaxshimisiz? Jasurbekning ahvoli qanday?",
        "answer_template": "Vaalaykum assalom, hamshira opa. Yaxshi deb bo'lmaydi... Jasurbek oxirgi kunlarda juda injiq bo'lib qolgan. Kechalari umuman uxlamaydi, orqasini qashlab yig'laydi. Ishtahasi yo'q, tishlarini g'ijirlatadi. To'g'risini aytsam, kechasi axlat sohasida kichik oq qurtchalarni ko'rib qo'rqib ketdim.",
        "emotion": "xavotirli",
        "priority": 20
    },
    # 1-Bosqich: Tunda qichishish, Tish g'ijirlatish va Injiqlik
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["qichishish", "qashlash", "tish", "g'ijirlatish", "uyqusizlik", "kechasi", "orqasi", "perianal", "injiq"],
        "trigger_pattern": ".*(qichish|qashla|tish|g'ijirla|uyqu|kechasi|orqa|injiq).*",
        "question_template": "Bolada tunda qichishish va tish g'ijirlatish kuzatilyaptimi?",
        "answer_template": "Kechalari orqa chiqaruv yo'li qattiq qichishadi, tinmay qashlab yig'laydi. Tishlarini g'ijirlatib bezovta uxlaydi, kunduzi esa injiq va tajang bo'lib qolgan.",
        "emotion": "og'riqli",
        "priority": 19
    },
    # 1-Bosqich: Qorin og'rig'i, Ishtahasizlik, Ko'ngil aynishi va Vazn (16 kg)
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["qorin", "og'riq", "kindik", "ishtaha", "ko'ngil aynishi", "harorat", "vazn", "16", "palpatsiya"],
        "trigger_pattern": ".*(qorin|kindik|ishtaha|ko'ngil|harorat|vazn|16).*",
        "question_template": "Qornida og'riq yoki ko'ngil aynishi bormi? Vazni qanday?",
        "answer_template": "Kindik atrofida tez-tez qorni og'riyapti, ko'ngli ayniydi. Ishtahasi mutlaqo yo'q, vazni 16 kg ga tushib qoldi. Harorati 36,6°C, lekin ko'z osti qorayib oqargan.",
        "emotion": "xavotirli",
        "priority": 18
    },
    # 1-Bosqich: Axlatda oq qurtchalar va Gijja (Enterobioz / Askaridoz)
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["gijja", "qurt", "gelmintoz", "enterobioz", "askaridoz", "parazit", "oq qurt", "axlatda"],
        "trigger_pattern": ".*(gijja|qurt|gelmint|enterobioz|askarid|parazit|oq qurt).*",
        "question_template": "Axlatida qurt ko'rdingizmi? Qanday ko'rinishda edi?",
        "answer_template": "Ha, axlatida ingichka oq qurtchalarni ko'rdim. Gijja tuxumlari tunda orqasiga chiqib qichitadi deb eshitgandim, shunga nima qilishni bilmay qo'rqyapman.",
        "emotion": "xavotirli",
        "priority": 17
    },
    # 2-Bosqich: Shifokor, Pediatr ko'rigi va Tahlillar (Perianal qirindi, Axlat)
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["shifokor", "pediatr", "tahlil", "qirindi", "axlat", "yo'llanma", "vrach", "poliklinika"],
        "trigger_pattern": ".*(shifokor|pediatr|tahlil|qirindi|axlat|yo'llanma|vrach).*",
        "question_template": "Zudlik bilan pediatr ko'rigi va perianal qirindi tahlili topshirish kerak.",
        "answer_template": "Mayli hamshira opa, darhol oilaviy shifokor va pediatrga boramiz. Perianal qirindi, axlat va umumiy qon tahlillarini topshirib, to'g'ri dori dozasini olamiz.",
        "emotion": "xavotirli",
        "priority": 16
    },
    # 3-Bosqich: Xavfli belgilar — Kuchli qorin og'rig'i, Ichak tutilishi va Qusish
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["xavfli belgi", "ichak tutilishi", "appenditsit", "og'riq", "qusish", "tez yordam", "chidab bo'lmas"],
        "trigger_pattern": ".*(ichak tutilishi|appenditsit|o'tkir qorin|qusish|tez yordam).*",
        "question_template": "Qorin og'rig'i kuchayib, qusish bo'lsa darhol Tez yordam chaqiring.",
        "answer_template": "Tushundim, agar kindik atrofida yoki o'ng tomonda chidab bo'lmas qorin og'rig'i va to'xtovsiz qusish boshlansa — ichak tutilishi xavfi borligi uchun zudlik bilan 'Tez yordam' chaqiramiz.",
        "emotion": "xavotirli",
        "priority": 15
    },
    # 3-Bosqich: Xavfli belgilar — Allergiya, Nafas qisishi, Yo'tal va Toshma
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["allergiya", "nafas qisishi", "yo'tal", "bo'g'ilish", "toshma", "shish", "o'pka"],
        "trigger_pattern": ".*(allergiya|nafas qisishi|yo'tal|bo'g'ilish|toshma|shish).*",
        "question_template": "Allergik toshma yoki nafas qisishi kuzatilsa ham shifokorga murojaat qiling.",
        "answer_template": "Doimiy quruq yo'tal, bo'g'ilish yoki badanga toshma toshsa — bu askarida lichinkalari migratsiyasi yoki kuchli intoksikatsiya belgisi ekan, darhol shifokorga murojaat qilamiz.",
        "emotion": "xavotirli",
        "priority": 14
    },
    # 4-Bosqich: Barcha oila a'zolari davolanishi va 14-21 kundan keyin takrorlash
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["oila", "hamma", "takroriy", "14 kun", "21 kun", "kurs", "dori", "preparat", "bir vaqtda"],
        "trigger_pattern": ".*(oila|hamma|takroriy|14 kun|21 kun|kurs|bir vaqtda).*",
        "question_template": "Barcha oila a'zolari bir kunda dori ichishi va 14-21 kunda takrorlashi shart.",
        "answer_template": "Antiparazitar dorini uyda yashaydigan barcha oila a'zolari bir vaqtda qabul qilamiz. Tuxumdan chiqqan yangi parazitlarni yo'qotish uchun 14-21 kundan keyin albatta takroriy kursni ichiramiz.",
        "emotion": "oddiy",
        "priority": 13
    },
    # 4-Bosqich: Tirnoqlarni olish va Qo'llarni 20 soniya sovunlab yuvish
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["tirnoq", "qo'l", "yuvish", "sovun", "gigiyena", "20 soniya", "bog'cha"],
        "trigger_pattern": ".*(tirnoq|qo'l|yuvish|sovun|gigiyena|20 soniya).*",
        "question_template": "Tirnoqlarini kalta oling va qo'llarini 20 soniya sovunlab yuvishni o'rgating.",
        "answer_template": "Jasurbekning tirnoqlarini doimo juda kalta qilib olib, ostini tozalayman. Ovqatdan oldin, hojatxonadan va ko'chadan keyin qo'llarini kamida 20 soniya sovunlab yuvishni qat'iy nazorat qilaman.",
        "emotion": "oddiy",
        "priority": 12
    },
    # 4-Bosqich: Zich paxtali ichki kiyim, 60°C+ da yuvish va Ikkala tomonini qaynoq dazmollash
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["kiyim", "ichki kiyim", "choyshab", "dazmol", "60", "yuvish", "paxtali", "dazmollash"],
        "trigger_pattern": ".*(ichki kiyim|choyshab|dazmol|60|qaynoq|paxtali).*",
        "question_template": "Ichki kiyim va choyshablarni 60°C dan yuqori yuvib, qaynoq dazmollang.",
        "answer_template": "Jasurbekka zich yopishib turadigan paxtali ichki kiyim kiygizib, har kuni ertalab almashtiraman. Barcha kiyim va choyshablarni 60 darajadan yuqorida yuvib, ikkala tomonini qaynoq dazmollayman.",
        "emotion": "oddiy",
        "priority": 11
    },
    # 4-Bosqich: Xonadonni namli tozalash, O'yinchoqlarni yuvish va Ertalabki perianal parvarish
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["o'yinchoq", "namli", "tozalash", "gilam", "changyutgich", "ertalab", "krem", "baby"],
        "trigger_pattern": ".*(o'yinchoq|namli|tozalash|gilam|changyutgich|ertalab|baby-krem).*",
        "question_template": "O'yinchoqlarni qaynoq suvda yuving, ertalab perianal sohani yuvib krem surting.",
        "answer_template": "Har kuni uyda namli tozalash o'tkazib, o'yinchoqlarini qaynoq suvda sovunlab yuvaman. Har kuni ertalab orqa chiqaruv sohasini iliq suvda yuvib, tinchlantiruvchi baby-krem surtaman.",
        "emotion": "oddiy",
        "priority": 10
    },
    # 4-Bosqich: Parhez (Shirinliklarni to'xtatish, Sabzi, Lavlagi, Qatiq, Kefir)
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["parhez", "shirinlik", "shakar", "gazli", "sabzi", "lavlagi", "qatiq", "kefir", "ovqat", "suv"],
        "trigger_pattern": ".*(parhez|shirinlik|shakar|gazli|sabzi|lavlagi|qatiq|kefir).*",
        "question_template": "Shirinliklarni taqiqlang, sabzi, lavlagi, qatiq va ko'p toza suv bering.",
        "answer_template": "Shirinliklar, pishiriqlar va gazli ichimliklarni butunlay to'xtatamiz. Ichak faoliyatini tiklash uchun sabzi, lavlagi, qatiq, kefir va ko'p qaynatilgan toza suv beraman.",
        "emotion": "oddiy",
        "priority": 9
    },
    # Yakuniy minnatdorchilik
    {
        "mannequin_slug": "bola",
        "trigger_keywords": ["rahmat", "salomat", "tuzaladi", "xayr", "bajaraman", "yordam"],
        "trigger_pattern": ".*(rahmat|salomat|tuzaladi|xayr|bajaraman).*",
        "question_template": "Xavotir olmang, gigiyenaga amal qilsangiz bola to'liq tuzaladi.",
        "answer_template": "Katta rahmat sizga hamshira opa! Barcha aytganlaringizni to'liq bajaramiz, hozir darhol shifokorga borib retseptlarni olamiz.",
        "emotion": "oddiy",
        "priority": 8
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
