import React, { useState, useCallback } from 'react';
import StatusBar from './components/StatusBar';
import MannequinSelector from './components/MannequinSelector';
import ConversationPanel from './components/ConversationPanel';
import VoiceRecorder from './components/VoiceRecorder';
import ScenarioPanel from './components/ScenarioPanel';
import { focusMannequin, sendChatMessage, sendSpeech } from './services/api';
import { playAudioResponse } from './utils/speechSynthesis';

function App() {
  const [activeMannequin, setActiveMannequin] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  const handleSelectMannequin = async (mannequin) => {
    setActiveMannequin(mannequin);
    setConversation([]);
    try {
      await focusMannequin(mannequin.slug);
    } catch (e) {
      console.warn("Lokal rejimda ishlamoqda", e);
    }
  };

  // Savol yuborish (ham ovozdan aniqlangan matn, ham qo'lda yozilgan matn)
  const handleSendMessage = useCallback(async (userText, audioBlob = null) => {
    if (!activeMannequin) return;
    const textToSend = (userText || '').trim();
    if (!textToSend && !audioBlob) return;

    const displayNurseText = textToSend || "🎤 [Ovozli so'rov]";
    setIsProcessing(true);

    // 1. Hamshira xabarini darhol chatga chiqarish
    setConversation(prev => [...prev, {
      speaker: 'nurse',
      text: displayNurseText,
      timestamp: new Date().toISOString()
    }]);

    try {
      let result;

      // 2. Agar matn bo'lsa -> DeepSeek /chat ga yuborish
      if (textToSend) {
        result = await sendChatMessage(textToSend, activeMannequin.slug, sessionId);
      } else if (audioBlob) {
        // Agar faqat audio bo'lsa -> /speech ga yuborish
        result = await sendSpeech(audioBlob, activeMannequin.slug, sessionId);
      }

      const replyText = result?.text || "Tushunmadim, iltimos qaytadan ayting.";
      const emotion = result?.emotion || null;

      // 3. AI javobini chatga chiqarish
      setConversation(prev => [
        ...prev,
        {
          speaker: 'mannequin',
          text: replyText,
          emotion: emotion,
          timestamp: new Date().toISOString()
        }
      ]);

      // 4. BEMORNING OVOZINI DINAMIKDAN CHIQARIB O'QISH (Sof O'zbek tili)
      playAudioResponse(result?.audio_base64, replyText, activeMannequin.slug);

    } catch (error) {
      console.warn("Backend API xatosi, aqlli lokal javob tizimi:", error);

      // Agar server bilan aloqa uzilgan bo'lsa, xarakterga mos lokal javob
      let fallbackText = "Kechirasiz, sizni yaxshi eshitolmadim, yana bir bor ayta olasizmi?";
      const lower = displayNurseText.toLowerCase();

      if (activeMannequin.slug === 'homilador') {
        if (lower.includes('salom') || lower.includes('ahvol') || lower.includes('qanday')) {
          fallbackText = "Vaalaykum assalom, hamshira opa. Oxirgi ikki kunda o'zimni juda holsiz his qilyapman. Boshim aylanib, belim simillab og'riyapti.";
        } else if (lower.includes('siydik') || lower.includes('rang')) {
          fallbackText = "Ha, oxirgi 2 kunda siydigimning rangi to'q bo'lib qoldi, tez-tez siygim kelyapti.";
        } else if (lower.includes('bosim') || lower.includes('harorat') || lower.includes('isitma')) {
          fallbackText = "Qon bosimim yaxshi ekan, lekin haroratim 37.5°C ga chiqib biroz qiziyapman.";
        } else if (lower.includes('shifoxona') || lower.includes('yotish') || lower.includes('vrach')) {
          fallbackText = "Mayli hamshira opa, bolam uchun shifoxonaga yotishga tayyorman, hozir kiyimlarimni yig'ishtiraman.";
        } else {
          fallbackText = "Belimning o'ng tomoni simillab og'riyapti, bolaligimdan buyragimda piyelonefrit bor edi.";
        }
      } else if (activeMannequin.slug === 'bobo') {
        if (lower.includes('salom') || lower.includes('ahvol') || lower.includes('qanday')) {
          fallbackText = "Vaalaykum assalom, qizim. Juda darmonim yo'q, doim og'zim qurib chanqayapman. Kechalari ham tinchim yo'q, 4-5 marta hojatga chiqyapman.";
        } else if (lower.includes('bosim') || lower.includes('qand') || lower.includes('shakar') || lower.includes('o\'lcha')) {
          fallbackText = "Qon bosimim 145/90 ekan, qandim 11.8 mmol/l chiqdi. Tahlil javobimda glikatsiyalangan gemoglobin 9.2% chiqqan ekan.";
        } else if (lower.includes('oyoq') || lower.includes('tovon') || lower.includes('yara')) {
          fallbackText = "Oyoqlarim uvishib, muzlab, sanchadi. O'ng tovonimda kichik yara bor, ikki haftadan beri bitmayapti, og'riqni deyarli sezmayapman.";
        } else if (lower.includes('parhez') || lower.includes('dori') || lower.includes('metformin') || lower.includes('tavsiya')) {
          fallbackText = "Tushundim bolam. Metforminni vaqtida ichaman, shirinlik va palovni cheklayman, tovonimga yod surtmasdan iliq suvda yuvaman.";
        } else {
          fallbackText = "Og'zim qurib chanqayapman, oyoqlarimda sezuvchanlik pasaygan. Shifokor tavsiyalarini bajaryapman.";
        }
      } else if (activeMannequin.slug === 'bola') {
        if (lower.includes('salom') || lower.includes('ahvol') || lower.includes('jasur')) {
          fallbackText = "Assalomu alaykum, hamshira opa. Jasurbek kechalari juda bezovta bo'lib orqa chiqaruv yo'lini qashiyapti, uyqusida tishini g'ijirlatyapti, ishtahasi ham yo'q.";
        } else if (lower.includes('qorin') || lower.includes('kindik') || lower.includes('og\'riq')) {
          fallbackText = "Onasi: Kindik atrofida tez-tez simillab og'riq bo'lyapti deydi. Jasurbek: Qornim achishyapti opa...";
        } else if (lower.includes('dori') || lower.includes('oila') || lower.includes('davolash')) {
          fallbackText = "Rahmat hamshira opa! Butun oilamiz bilan bir kunda dori ichamiz va 14-21 kundan so'ng albatta qaytaramiz.";
        } else if (lower.includes('gigiyena') || lower.includes('tirnoq') || lower.includes('dazmol') || lower.includes('yuvish')) {
          fallbackText = "Tushundim, tirnoqlarini doim kalta olaman, ichki kiyimlarini 60 darajadan yuqorida yuvib, ikki tomonini qaynoq dazmollayman.";
        } else {
          fallbackText = "Jasurbekning orqasi qichishyapti, axlatida oq mayda qurtchalar ko'rdim. Nima qilishimiz kerak?";
        }
      } else if (activeMannequin.slug === 'chaqaloq') {
        fallbackText = "👶 *yig'lash ovozi*";
      }

      setConversation(prev => [
        ...prev,
        {
          speaker: 'mannequin',
          text: fallbackText,
          emotion: 'oddiy',
          timestamp: new Date().toISOString()
        }
      ]);

      // Ovoz chiqarish
      playAudioResponse(null, fallbackText, activeMannequin.slug);

    } finally {
      setIsProcessing(false);
    }
  }, [activeMannequin, sessionId]);

  const handleAudioReady = useCallback(({ audioBlob, transcript }) => {
    handleSendMessage(transcript, audioBlob);
  }, [handleSendMessage]);

  const handleTextSubmit = useCallback((text) => {
    handleSendMessage(text);
  }, [handleSendMessage]);

  const handleStartSession = useCallback((data) => {
    const newId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    setSessionId(newId);
    setConversation([{
      speaker: 'system',
      text: `📋 Mashg'ulot boshlandi — ${data.scenarioTitle || 'Umumiy ssenariy'}`,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  const handleEndSession = useCallback(() => {
    setConversation(prev => [...prev, {
      speaker: 'system',
      text: '✅ Mashg\'ulot yakunlandi.',
      timestamp: new Date().toISOString()
    }]);
    setSessionId(null);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-50 overflow-hidden font-sans select-none antialiased">
      {/* Yuqori panel */}
      <StatusBar activeMannequin={activeMannequin} sessionId={sessionId} />

      {/* Asosiy ishchi maydon */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chap panel (25%): Bemorlar */}
        <div className="w-1/4 h-full shrink-0">
          <MannequinSelector
            activeMannequin={activeMannequin}
            onSelect={handleSelectMannequin}
          />
        </div>

        {/* Markaziy panel (50%): Muloqot jurnali + Mikrofon & Matn kiritish */}
        <div className="w-1/2 h-full flex flex-col shadow-[0_0_15px_rgba(0,0,0,0.03)] z-10 shrink-0 bg-white">
          <ConversationPanel
            conversation={conversation}
            activeMannequin={activeMannequin}
          />
          <VoiceRecorder
            activeMannequin={activeMannequin}
            isProcessing={isProcessing}
            onAudioReady={handleAudioReady}
            onTextSubmit={handleTextSubmit}
          />
        </div>

        {/* O'ng panel (25%): Ssenariy */}
        <ScenarioPanel
          activeMannequin={activeMannequin}
          sessionId={sessionId}
          onStartSession={handleStartSession}
          onEndSession={handleEndSession}
        />
      </div>
    </div>
  );
}

export default App;
