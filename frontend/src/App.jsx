import React, { useState, useCallback } from 'react';
import StatusBar from './components/StatusBar';
import MannequinSelector from './components/MannequinSelector';
import ConversationPanel from './components/ConversationPanel';
import VoiceRecorder from './components/VoiceRecorder';
import ScenarioPanel from './components/ScenarioPanel';
import { focusMannequin, sendChatMessage, sendSpeech } from './services/api';
import { speakText } from './utils/speechSynthesis';

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

      // 4. BEMORNING OVOZINI DINAMIKDAN CHIQARIB O'QISH
      speakText(replyText, activeMannequin.slug);

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
        if (lower.includes('salom') || lower.includes('ahvol')) {
          fallbackText = "Rahmat qizim, biroz boshim aylanib, yuragim tez uryapti.";
        } else if (lower.includes('dori')) {
          fallbackText = "Ertalab o'zimning dorilarimni ichgan edim, lekin bosimim tushmadi.";
        } else {
          fallbackText = "Qon bosimim 180 ga chiqib ketgan shekilli, qizim, bir tekshirib bering.";
        }
      } else if (activeMannequin.slug === 'bola') {
        fallbackText = "Oyim qani? Ukol qilmang, qo'rqaman!";
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
      speakText(fallbackText, activeMannequin.slug);

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
