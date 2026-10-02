import React, { useState, useCallback } from 'react';
import StatusBar from './components/StatusBar';
import MannequinSelector from './components/MannequinSelector';
import ConversationPanel from './components/ConversationPanel';
import VoiceRecorder from './components/VoiceRecorder';
import ScenarioPanel from './components/ScenarioPanel';
import { focusMannequin, sendSpeech } from './services/api';

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
      console.warn("Backend ulanmagan, lokal rejimda ishlayapti", e);
    }
  };

  const handleAudioReady = useCallback(async (audioBlob) => {
    if (!activeMannequin) return;
    setIsProcessing(true);

    // Hamshira xabarini qo'shish
    setConversation(prev => [...prev, {
      speaker: 'nurse',
      text: '🎤 Ovozli xabar yuborildi...',
      timestamp: new Date().toISOString()
    }]);

    try {
      // Backend ga ovoz yuborish
      const result = await sendSpeech(audioBlob, activeMannequin.slug, sessionId);

      setConversation(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          text: result.user_text || '[Ovozli xabar yuborildi]'
        };
        return [
          ...updated,
          {
            speaker: 'mannequin',
            text: result.text,
            emotion: result.emotion || null,
            timestamp: new Date().toISOString()
          }
        ];
      });
    } catch (error) {
      console.warn("Backend javob bermadi, lokal dialog:", error);

      // Gulnora opa va boshqa bemorlarning aniq klinik replikalari
      const mockResponses = {
        bobo: [
          "Rahmat qizim, biroz boshim aylanib, yuragim tez uryapti.",
          "Ha, ertalab o'zimning dorilarimni ichgan edim, lekin foydasi bo'lmadi.",
          "Oyoqlarim shishib ketdi, qon bosimimni o'lchab bering bolam."
        ],
        homilador: [
          "Vaalaykum assalom, hamshira opa. Yaxshi deb bo'lmaydi... Oxirgi ikki kunda o'zimni juda holsiz his qilyapman. Boshim aylanib, tez charchab qolayapman. Belim ham simillab og'riyapti.",
          "Ha, oxirgi 2 kunda siydigimning rangi to'q bo'lib qoldi, biroz tez-tez siygim kelyapti.",
          "Ha, o'zim ham sezdim, tana haroratim 37,5°C ga chiqib, biroz qiziyapman. Boshim ham aylanib turibdi.",
          "Belimning orqa tomoni, ayniqsa o'ng tomoni simillab og'riyapti. Bolaligimdan surunkali piyelonefritim bor edi.",
          "Mayli hamshira opa, bolam va o'zimning sog'lig'im uchun shifoxonaga yotishga tayyorman. Hozir kiyimlarimni yig'ishtiraman.",
          "Xudoga shukur, bolam harakatlanyapti, lekin unga biror ziyon yetmaydimi deb juda xavotirdaman, hamshira opa.",
          "Yo'q, xudoga shukur, qonli ajralma yoki suv ketishi bo'lmadi.",
          "Aytganingizdek qilaman: tuzli taomlarni cheklab, na'matak damlamasi ichaman va kuniga 3-4 mahal tizza-tirsak holatida turaman."
        ],
        bola: [
          "Rostdanmi? Ukol qilmaysizmi? Oyim qachon keladilar?",
          "Oyim qani? Uyga ketaman!",
          "Menga dori bermang, qo'rqaman!"
        ],
        chaqaloq: [
          "👶 *yig'lash ovozi*",
          "👶 *kulish ovozi*",
          "👶 *uhh... uhh...*"
        ]
      };

      const responses = mockResponses[activeMannequin.slug] || ["Tushunmadim."];
      const resText = responses[Math.floor(Math.random() * responses.length)];

      const emotions = {
        bobo: "og'riqli",
        homilador: "xavotirli",
        bola: "qo'rqqan",
        chaqaloq: "yig'lash"
      };

      setConversation(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          text: '[Ovozli xabar yuborildi]'
        };
        return [
          ...updated,
          {
            speaker: 'mannequin',
            text: resText,
            emotion: emotions[activeMannequin.slug] || null,
            timestamp: new Date().toISOString()
          }
        ];
      });
    } finally {
      setIsProcessing(false);
    }
  }, [activeMannequin, sessionId]);

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

      {/* Asosiy ishchi maydon (3 ustunli) */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chap panel (25%): Bemorlar ro'yxati */}
        <div className="w-1/4 h-full shrink-0">
          <MannequinSelector
            activeMannequin={activeMannequin}
            onSelect={handleSelectMannequin}
          />
        </div>

        {/* Markaziy panel (50%): Muloqot jurnali + Mikrofon */}
        <div className="w-1/2 h-full flex flex-col shadow-[0_0_15px_rgba(0,0,0,0.03)] z-10 shrink-0 bg-white">
          <ConversationPanel
            conversation={conversation}
            activeMannequin={activeMannequin}
          />
          <VoiceRecorder
            activeMannequin={activeMannequin}
            isProcessing={isProcessing}
            onAudioReady={handleAudioReady}
          />
        </div>

        {/* O'ng panel (25%): Ssenariy va Nazorat */}
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
