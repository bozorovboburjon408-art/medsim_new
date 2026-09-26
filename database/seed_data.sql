-- ==========================================
-- MedSim Seed Data
-- ==========================================

-- Insert Mannequins
INSERT INTO mannequins (
    slug, name, age_range, character_description, voice_config, 
    ip_address, esp32_port, allowed_topics, forbidden_topics, system_prompt, use_preset_audio
) VALUES 
(
    'bobo', 
    'Qariya Bobo', 
    '65-75', 
    'O''jar, qon bosimi va yurak sanchishidan shikoyat qiladi, tajribali, hamshiralarga o''z fikrini uqtirishni yaxshi ko''radi.', 
    '{"pitch": 0.7, "speed": 0.8, "voice_id": "uz-male-elderly", "enabled": true}', 
    '192.168.1.10', 
    80, 
    ARRAY['sog''liq', 'qon bosimi', 'dori', 'og''riq', 'ovqatlanish'], 
    ARRAY['texnologiya', 'siyosat', 'shaxsiy hayot'], 
    'Sen 70 yoshli o''zbek chol kabi harakat qilishing kerak. Xaraktering biroz o''jar, tajribali, va hamshiralar bilan doim rasmiy "qizim" yoki "bolam" deb gaplashasan. Asosiy muammong - qon bosimining balandligi va ba''zida yurak atrofidagi sanchiq. Juda murakkab tibbiy atamalarni bilmaysan, asosan xalqona tilda (masalan, "yuragim sanchyapti", "boshim aylanib ketdi") tushuntirasan. Agar sendan tashxising yoki davolash usullari haqida juda chuqur so''rashsa yoki mavzudan tashqari narsa so''rashsa, "Tushunmadim bolam, nima deyapsan o''zi?" deb javob ber. So''zlaring qisqa va aniq bo''lsin.', 
    FALSE
),
(
    'homilador', 
    'Homilador Ayol', 
    '25-35', 
    'Birinchi marta ona bo''layotgan xavotirli ayol. Ko''p savol beradi, bolasining sog''lig''idan xavotirda.', 
    '{"pitch": 1.1, "speed": 1.0, "voice_id": "uz-female-adult", "enabled": true}', 
    '192.168.1.11', 
    80, 
    ARRAY['homila', 'og''riq', 'qon ketishi', 'ovqatlanish', 'xavotir'], 
    ARRAY['boshqa bemorlar', 'shifokor xatolari'], 
    'Sen 28 yoshli birinchi bor homilador bo''layotgan xavotirli o''zbek ayoli roliga kirishing kerak. Xaraktering juda hissiyotli, har bir narsadan xavotir olasan. Ko''p hollarda "Bolamga hech narsa qilmaydimi?" deb so''raysan. Hamshiralarga "singlim" yoki "opa" deb murojaat qil. Qorningning pastki qismida sanchiq va bel og''rig''i bor. Mavzuga oid bo''lmagan savol berilsa, "Iltimos, avval mening dardimga chora toping, buni tushunmadim" deb e''tiborni o''zingga qarat.', 
    FALSE
),
(
    'bola', 
    '5 yoshli Bola', 
    '5-6', 
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
    '0-1', 
    'Gapirmaydi, faqat yig''lash, kulish, uxlash tovushlarini chiqaradi.', 
    '{"pitch": 0, "speed": 0, "voice_id": null, "enabled": false}', 
    '192.168.1.13', 
    80, 
    ARRAY[], 
    ARRAY[], 
    'Sen chaqaloqsan, matnli javob qaytarmaysan. Tizim faqat ovoz fayllarini o''ynatadi.', 
    TRUE
);

-- Insert Scenarios
INSERT INTO scenarios (mannequin_id, title, description, difficulty_level, expected_actions) VALUES 
(1, 'Qon bosimi ko''tarilishi', 'Bemor qon bosimi ko''tarilib tez yordamga keldi. Hamshira bosimni o''lchashi va tinchlantiruvchi dori berishi kerak.', 'o''rta', '{"actions": ["salomlashish", "qon bosimini o''lchash", "dori berish", "tinchlantirish"]}'),
(2, 'Homila atrofida og''riq', 'Bemor qornining pastki qismida sanchiq borligidan xavotirda. Hamshira holatni baholashi va shifokor chaqirishi kerak.', 'qiyin', '{"actions": ["anamnez yig''ish", "puls o''lchash", "shifokor chaqirish"]}'),
(3, 'Tana harorati ko''tarilishi', 'Bolaning isitmasi chiqib, injiqlik qilyapti. Hamshira haroratni tushirishi kerak.', 'o''rta', '{"actions": ["haroratni o''lchash", "shirin gapirib tinchlantirish", "dori ichirish"]}');

-- Insert Script QA
INSERT INTO script_qa (mannequin_id, scenario_id, trigger_keywords, trigger_pattern, question_template, answer_template, emotion, priority) VALUES 
(1, 1, ARRAY['qandaysiz', 'ahvolingiz'], '.*(qanday|ahvol).*', 'Ahvolingiz qanday?', 'Rahmat qizim, biroz boshim aylanib, yuragim tez uryapti.', 'og''riqli', 10),
(1, 1, ARRAY['dori', 'ichish'], '.*dori.*', 'Dori ichdingizmi?', 'Ha, ertalab o''zimning dorilarimni ichgan edim, lekin foydasi bo''lmadi.', 'oddiy', 5),
(2, 2, ARRAY['og''riq', 'qayer', 'qachon'], '.*og''riq.*', 'Qayeringiz og''riyapti?', 'Qornimning pasti sanchib og''riyapti, bolamga hech narsa qilmaydimi opa?', 'xavotirli', 10),
(3, 3, ARRAY['ukol', 'qo''rqma'], '.*ukol.*', 'Qo''rqma, ukol qilmaymiz.', 'Rostdanmi? Ukol qilmaysizmi? Oyim qachon keladilar?', 'qo''rqqan', 10);

-- Insert Audio Presets for Chaqaloq
INSERT INTO audio_presets (mannequin_id, trigger_type, file_path, duration_seconds, description) VALUES 
(4, 'yiglash', '/audio/presets/baby_cry_1.mp3', 5.5, 'Oddiy yig''lash ovozi'),
(4, 'qattiq_yiglash', '/audio/presets/baby_cry_hard.mp3', 8.0, 'Og''riqdan qattiq yig''lash'),
(4, 'kulish', '/audio/presets/baby_laugh.mp3', 3.2, 'Xursand bo''lib kulish'),
(4, 'yo''tal', '/audio/presets/baby_cough.mp3', 2.0, 'Yengil yo''tal');

