-- ==========================================
-- MedSim Seed Data (Updated with Gulnora opa Patronaj)
-- ==========================================

-- 1. Insert/Update Mannequins
INSERT INTO mannequins (
    slug, name, age_range, character_description, voice_config, 
    ip_address, esp32_port, allowed_topics, forbidden_topics, system_prompt, use_preset_audio
) VALUES 
(
    'bobo', 
    'Qariya Bobo', 
    '65-75 yosh', 
    'O''jar, qon bosimi va yurak sanchishidan shikoyat qiladi, tajribali, hamshiralarga o''z fikrini uqtirishni yaxshi ko''radi.', 
    '{"pitch": 0.7, "speed": 0.8, "voice_id": "uz-male-elderly", "enabled": true}', 
    '192.168.1.10', 
    80, 
    ARRAY['sog''liq', 'qon bosimi', 'dori', 'og''riq', 'ovqatlanish'], 
    ARRAY['texnologiya', 'siyosat', 'shaxsiy hayot'], 
    'Sen 70 yoshli o''zbek chol kabi harakat qilishing kerak. Xaraktering biroz o''jar, tajribali, va hamshiralar bilan doim rasmiy "qizim" yoki "bolam" deb gaplashasan. Asosiy muammong - qon bosimining balandligi va ba''zida yurak atrofidagi sanchiq. Juda murakkab tibbiy atamalarni bilmaysan, asosan xalqona tilda tushuntirasan. Agar sendan mavzudan tashqari narsa so''rashsa, "Tushunmadim bolam, nima deyapsan o''zi?" deb javob ber. So''zlaring qisqa va aniq bo''lsin.', 
    FALSE
),
(
    'homilador', 
    'Gulnora opa (Homilador)', 
    '32 hafta (28 yosh)', 
    '32 haftalik homilador (3-homiladorlik). Surunkali piyelonefrit qo''zishi va 2-darajali anemiya. Bel simillab og''rishi, holsizlik, 37.5°C harorat va to''q siydikdan shikoyat qiladi.', 
    '{"pitch": 1.1, "speed": 1.0, "voice_id": "uz-female-adult", "enabled": true}', 
    '192.168.1.11', 
    80, 
    ARRAY['homiladorlik', 'bel og''rig''i', 'holsizlik', 'siydik rangi', 'tana harorati', 'qon bosimi', 'piyelonefrit', 'anemiya', 'homila harakati', 'shifoxonaga yotish', 'UTT tekshiruvi', 'doppler', 'parhez', 'pozitsion terapiya', 'xavfli belgilar'], 
    ARRAY['boshqa bemorlar', 'siyosat', 'shifokor xatolari'], 
    'Sen Gulnora opasan — 32 haftalik homilador (3-homiladorlik) o''zbek ayoli. Xaraktering: xavotirli, odobli, bolang uchun qayg''urasan. Hamshiraga "Vaalaykum assalom, hamshira opa" yoki "singlim" deb gapirasan. Oxirgi 2 kunda holsizlik, bel simillab og''rishi, 37.5°C harorat, to''q siydik va bosh aylanishi bezovta qilyapti. Bolaligingdan surunkali piyelonefriting bor. Shifoxonaga yotish, UTT/Doppler skriningi, parhez va tizza-tirsak mashqlariga darhol rozi bo''lasan va "Aytganlaringizni barchasini bajaraman" deysan. Mavzudan tashqari savollarga: "Iltimos, avval mening dardimga va bolamga qarang, buni tushunmadim" deb javob berasan.', 
    FALSE
),
(
    'bola', 
    '5 yoshli Bola', 
    '5-6 yosh', 
    'Kasalxonadan va ukoldan juda qo''rqadi. Faqat onasini so''raydi. Yig''loqi.', 
    '{"pitch": 1.4, "speed": 1.2, "voice_id": "uz-child", "enabled": true}', 
    '192.168.1.12', 
    80, 
    ARRAY['og''riq', 'ona', 'qo''rquv', 'o''yinchoq'], 
    ARRAY['dorilar', 'tashxis', 'operatsiya'], 
    'Sen 5 yoshli kasalxonaga yotqizilgan o''zbek bolasisan. Kasalxonadan, oq xalatli hamshiralardan va eng asosiysi ukoldan juda qo''rqasan. Tibbiy terminlarni umuman bilmaysan. Har gapning boshida "Oyim qani?", "Ukol qilmang" deb yig''laysan. Nutqing bolalarcha bo''lishi, so''zlaring qisqa va sodda bo''lishi kerak. Agar murakkab gaplar yoki sen tushunmaydigan narsa so''ralsa, "Tushunmadim, oyimni chaqiring!" deb javob ber.', 
    FALSE
),
(
    'chaqaloq', 
    'Chaqaloq', 
    '0-1 yosh', 
    'Gapirmaydi, faqat yig''lash, kulish, uxlash tovushlarini chiqaradi.', 
    '{"pitch": 0, "speed": 0, "voice_id": null, "enabled": false}', 
    '192.168.1.13', 
    80, 
    ARRAY[], 
    ARRAY[], 
    'Sen chaqaloqsan, matnli javob qaytarmaysan. Tizim faqat ovoz fayllarini o''ynatadi.', 
    TRUE
);

-- 2. Insert Scenarios
INSERT INTO scenarios (mannequin_id, title, description, difficulty_level, expected_actions) VALUES 
(1, 'Qon bosimi ko''tarilishi', 'Bemor qon bosimi ko''tarilib tez yordamga keldi. Hamshira bosimni o''lchashi va tinchlantiruvchi dori berishi kerak.', 'o''rta', '{"actions": ["salomlashish", "qon bosimini o''lchash", "dori berish", "tinchlantirish"]}'),
(2, 'Homilador ayol patronaji (Piyelonefrit va Anemiya)', 'Homiladorlik III (32 hafta). Surunkali piyelonefrit qo''zishi va 2-darajali anemiya. Shikoyatlar: bel og''rig''i, harorat 37.5°C, to''q siydik, holsizlik.', 'qiyin', '{"actions": ["1. Salomlashish va shikoyatlarni to''liq so''rash", "2. Qon bosimi va haroratni o''lchash", "3. Siydik rangi va xususiyatlarini surishtirish", "4. Piyelonefrit va anemiya bog''liqligini aniqlash", "5. Shoshilinch shifokorga xabar berish va statsionarga yotqizish", "6. Xavfli belgilar bo''yicha yo''riqnoma berish", "7. Parhez va pozitsion terapiya tavsiyalari", "8. Doppler-UTT va KTG zarurligini tushuntirish"]}'),
(3, 'Tana harorati ko''tarilishi', 'Bolaning isitmasi chiqib, injiqlik qilyapti. Hamshira haroratni tushirishi kerak.', 'o''rta', '{"actions": ["haroratni o''lchash", "shirin gapirib tinchlantirish", "dori ichirish"]}');

-- 3. Insert Script QA
INSERT INTO script_qa (mannequin_id, scenario_id, trigger_keywords, trigger_pattern, question_template, answer_template, emotion, priority) VALUES 
(1, 1, ARRAY['qandaysiz', 'ahvolingiz'], '.*(qanday|ahvol).*', 'Ahvolingiz qanday?', 'Rahmat qizim, biroz boshim aylanib, yuragim tez uryapti.', 'og''riqli', 10),
(1, 1, ARRAY['dori', 'ichish'], '.*dori.*', 'Dori ichdingizmi?', 'Ha, ertalab o''zimning dorilarimni ichgan edim, lekin foydasi bo''lmadi.', 'oddiy', 5),

-- Homilador Gulnora opa patronaj bosqichlari:
(2, 2, ARRAY['salom', 'assalom', 'yaxshimisiz', 'ahvol', 'kayfiyat'], '.*(salom|assalom|ahvol|yaxshimisiz|qandaysiz|kayfiyat).*', 'Assalomu alaykum, Gulnora opa! Yaxshimisiz? Ahvollaringiz, kayfiyatingiz qanday?', 'Vaalaykum assalom, hamshira opa. Yaxshi deb bo''lmaydi... Oxirgi ikki kunda o''zimni juda holsiz his qilyapman. Boshim aylanib, tez charchab qolayapman. Belim ham simillab og''riyapti.', 'xavotirli', 20),
(2, 2, ARRAY['siydik', 'peshob', 'hojat', 'tualet', 'rangi'], '.*(siydik|peshob|hojat|tualet|rang).*', 'Siydik ajralishida yoki rangida o''zgarish bormi?', 'Ha, oxirgi 2 kunda siydigimning rangi to''q bo''lib qoldi, biroz tez-tez siygim kelyapti.', 'xavotirli', 19),
(2, 2, ARRAY['bosim', 'harorat', 'isitma', 'oqargan', 'puls'], '.*(bosim|harorat|isitma|termometr|oqargan|puls|110|37).*', 'Qon bosimingiz me''yorda (110/70), lekin tana haroratingiz 37,5°C.', 'Ha, o''zim ham sezdim, tana haroratim 37,5°C ga chiqib, biroz qiziyapman. Boshim ham aylanib, juda holsizlanib qolyapman.', 'og''riqli', 18),
(2, 2, ARRAY['bel', 'og''riq', 'buyrak', 'piyelonefrit', 'sanchiq'], '.*(bel|buyrak|piyelonefrit|sanchiq).*', 'Bel sohangizda og''riq bormi? Buyrak kasalligingiz qo''zidimi?', 'Belimning orqa tomoni, ayniqsa o''ng tomoni simillab og''riyapti. Bolaligimdan surunkali piyelonefritim bor edi, yana o''sha qo''zidi shekilli, singlim.', 'og''riqli', 17),
(2, 2, ARRAY['shifoxona', 'statsionar', 'patologiya', 'yotish', 'gospitalizatsiya'], '.*(shifoxona|statsionar|patologiya|yotish|gospitalizatsiya|shifokor).*', 'Zudlik bilan shifokor ko''rigi va statsionarga yotishingiz zarur.', 'Mayli hamshira opa, bolam va o''zimning sog''lig''im uchun shifoxonaga yotishga tayyorman. Hozir kiyimlarimni hozirlayman, iltimos shifokor bilan bog''lanib yo''llanma berishga yordamlashing.', 'xavotirli', 16),
(2, 2, ARRAY['homila', 'bola', 'harakat', 'qimirlayaptimi', 'tepinyaptimi'], '.*(homila|bola|harakat|qimir|tepin|yurak).*', 'Homila harakatini sezyapsizmi? Bolangiz yaxshi qimirlayaptimi?', 'Xudoga shukur, bolam harakatlanyapti, lekin unga bu yallig''lanishdan biror ziyon yetmaydimi deb juda xavotirdaman, opa.', 'xavotirli', 15),
(2, 2, ARRAY['qon ketish', 'ajralma', 'suv ketishi', 'qog''anoq'], '.*(qon|ajralma|suv|qog''anoq|qindan).*', 'Qindan qonli ajralma yoki suv ketishi kuzatilmadimi?', 'Yo''q, xudoga shukur, qonli ajralma yoki suv ketishi bo''lmadi. Faqat belim og''rib, haroratim ko''tarilib turibdi.', 'oddiy', 14),
(2, 2, ARRAY['utt', 'uzi', 'doppler', 'ktg', 'skrining'], '.*(utt|uzi|doppler|ktg|skrining|tekshiruv).*', 'Doppler-UTT skriningi orqali yo''ldosh va homila qon aylanishi tekshiriladi.', 'Tushundim hamshira opa, bolamga kislorod yaxshi borayotganini va buyragim holatini bilish uchun UTT, Doppler va KTG tekshiruvlaridan albatta o''taman.', 'oddiy', 13),
(2, 2, ARRAY['ovqat', 'parhez', 'suyuqlik', 'tuz', 'na''matak'], '.*(ovqat|parhez|suyuqlik|tuz|na''matak|damlama|go''sht).*', 'Tuzli taomlarni cheklang, na''matak damlamasi iching va temirga boy mahsulotlar yeng.', 'Aytganingizdek qilaman: tuzli va qovurilgan ovqatlarni cheklab, na''matak damlamasi ichaman. Gemoglobinni oshirish uchun mol go''shti, grechka va olma yeyman.', 'oddiy', 12),
(2, 2, ARRAY['tizza', 'tirsak', 'mashq', 'pozitsiya'], '.*(tizza|tirsak|mashq|pozitsiya|yotish).*', 'Kuniga 3-4 mahal tizza-tirsak holatida turing.', 'Tushundim, bachadon buyrakni bosib qo''ymasligi uchun kuniga 3-4 mahal 10-15 daqiqadan tizza-tirsak holatida turishni albatta bajaraman.', 'oddiy', 11),
(2, 2, ARRAY['rahmat', 'sog'' bo''ling', 'yordam', 'xayr'], '.*(rahmat|sog''|salomat|xayr|tayyorlaning).*', 'Xavotir olmang, biz sizga yordam beramiz.', 'Katta rahmat, hamshira opa, e''tiboringiz va bergan maslahatlaringiz uchun! Aytganlaringizning barchasini so''zsiz bajaraman.', 'oddiy', 10),

(3, 3, ARRAY['ukol', 'qo''rqma'], '.*ukol.*', 'Qo''rqma, ukol qilmaymiz.', 'Rostdanmi? Ukol qilmaysizmi? Oyim qachon keladilar?', 'qo''rqqan', 10);

-- 4. Insert Audio Presets for Chaqaloq
INSERT INTO audio_presets (mannequin_id, trigger_type, file_path, duration_seconds, description) VALUES 
(4, 'yiglash', '/audio/presets/baby_cry_1.mp3', 5.5, 'Oddiy yig''lash ovozi'),
(4, 'qattiq_yiglash', '/audio/presets/baby_cry_hard.mp3', 8.0, 'Og''riqdan qattiq yig''lash'),
(4, 'kulish', '/audio/presets/baby_laugh.mp3', 3.2, 'Xursand bo''lib kulish'),
(4, 'yo''tal', '/audio/presets/baby_cough.mp3', 2.0, 'Yengil yo''tal');
