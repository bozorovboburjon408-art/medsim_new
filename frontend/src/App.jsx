import React, { useState, useCallback } from 'react';
import StatusBar from './components/StatusBar';
import VitalSignsMonitor from './components/VitalSignsMonitor';
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
  const [completedActions, setCompletedActions] = useState([]);

  const handleSelectMannequin = async (mannequin) => {
    setActiveMannequin(mannequin);
    setConversation([]);
    setCompletedActions([]);
    try {
      await focusMannequin(mannequin.slug);
    } catch (e) {
      console.warn("Backend API ulanmagan, lokal rejimda ishlayapti", e);
    }
  };

  const handleAudioReady = useCallback(async (audioBlob) => {
    if (!activeMannequin) return;
    setIsProcessing(true);

    // Hamshiraning yuborilgan ovozli xabari
    setConversation(prev => [...prev, {
      speaker: 'nurse',
      text: '🎤 [Ovozli so\'rov uzatildi...]',
      timestamp: new Date().toISOString()
    }]);

    try {
      // Backend FastAPI ga yuborish
      const result = await sendSpeech(audioBlob, activeMannequin.slug, sessionId);

      setConversation(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          text: result.user_text || '[Ovozli patronaj savoli]'
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

      // Avtomatik cheklist progressini yangilash
      setCompletedActions(prev => {
        const nextIdx = prev.length;
        if (nextIdx < 5 && !prev.includes(nextIdx)) {
          return [...prev, nextIdx];
        }
        return prev;
      });

    } catch (error) {
      console.warn("Backend aloqasi yo'q, lokal klinik dialog ishga tushdi:", error);

      // Klinik replikalar (offline fallback)
      const mockResponses = {
        bobo: [
          "Rahmat qizim, biroz boshim aylanib, yuragim tez uryapti.",
          "Ha, ertalab o'zimning dorilarimni ichgan edim, lekin foydasi bo'lmadi.",
          "Boshim qattiq og'riyapti, qon bosimimni o'lchab bering bolam."
        ],
        homilador: [
          "Vaalaykum assalom, hamshira opa. Yaxshi deb bo'lmaydi... Oxirgi ikki kunda o'zimni juda holsiz his qilyapman. Boshim aylanib, tez charchab qolayapman. Belim ham simillab og'riyapti.",
          "Ha, oxirgi 2 kunda siydigimning rangi to'q bo'lib qoldi, biroz tez-tez siygim kelyapti.",
          "Ha, o'zim ham sezdim, tana haroratim 37,5°C ga chiqib, biroz qiziyapman. Boshim ham aylanib turibdi.",
          "Belimning orqa tomoni, ayniqsa o'ng tomoni simillab og'riyapti. Bolaligimdan surunkali piyelonefritim bor edi.",
          "Mayli hamshira opa, bolam va o'zimning sog'lig'im uchun shifoxonaga yotishga tayyorman. Hozir kiyimlarimni yig'ishtiraman.",
          "Xudoga shukur, bolam harakatlanyapti, lekin unga biror ziyon yetmaydimi deb juda xavotirdaman, hamshira opa.",
          "Aytganingizdek qilaman: tuzli taomlarni cheklab, na'matak damlamasi ichaman va kuniga 3-4 mahal tizza-tirsak holatida turaman."
        ],
        bola: [
          "Rostdanmi? Ukol qilmaysizmi? Oyim qachon keladilar?",
          "Oyim qani? Qornim og'riyapti, uyga ketaman!",
          "Menga dori bermang, qo'rqaman!"
        ],
        chaqaloq: [
          "👶 *qattiq yig'lash ovozi*",
          "👶 *xursand bo'lib kulish ovozi*",
          "👶 *yengil yo'tal va injiqlik ovozi*"
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
          text: '[Hamshira patronaj savoli uzatildi]'
        };
        return [
          ...updated,
          {
            speaker: 'mannequin',
            text: resText,
            emotion: emotions[activeMannequin.slug] || 'oddiy',
            timestamp: new Date().toISOString()
          }
        ];
      });

      setCompletedActions(prev => {
        const nextIdx = prev.length;
        if (nextIdx < 5 && !prev.includes(nextIdx)) {
          return [...prev, nextIdx];
        }
        return prev;
      });
    } finally {
      setIsProcessing(false);
    }
  }, [activeMannequin, sessionId]);

  const handleStartSession = useCallback((data) => {
    const newId = 'SES-' + Math.random().toString(36).substr(2, 6).toUpperCase();
    setSessionId(newId);
    setCompletedActions([0]);
    setConversation([{
      speaker: 'system',
      text: `🏥 Klinik patronaj seansi boshlandi — ${data.scenarioTitle || 'Standart Ssenariy'}`,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  const handleEndSession = useCallback(() => {
    setConversation(prev => [...prev, {
      speaker: 'system',
      text: '🏁 Patronaj seansi yakunlandi. Protokol baholashga yuborildi.',
      timestamp: new Date().toISOString()
    }]);
    setSessionId(null);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans select-none antialiased">
      {/* Yuqori Tizim Paneli */}
      <StatusBar activeMannequin={activeMannequin} sessionId={sessionId} />

      {/* Real-Vaqtli Vital Signs & EKG Monitori */}
      <VitalSignsMonitor activeMannequin={activeMannequin} />

      {/* Asosiy 3 Ustunli Ishchi Maydon */}
      <div className="flex flex-1 overflow-hidden bg-slate-900">
        
        {/* Chap Panel (25%): Triaj va Bemorlar */}
        <div className="w-1/4 h-full shrink-0">
          <MannequinSelector
            activeMannequin={activeMannequin}
            onSelect={handleSelectMannequin}
          />
        </div>

        {/* Markaziy Panel (50%): Transkript Jurnali + Ovoz Konsoli */}
        <div className="w-1/2 h-full flex flex-col shrink-0 bg-slate-900 border-x border-slate-800 shadow-2xl relative z-10">
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

        {/* O'ng Panel (25%): Klinik Protokol, Cheklist va Baholash */}
        <ScenarioPanel
          activeMannequin={activeMannequin}
          sessionId={sessionId}
          onStartSession={handleStartSession}
          onEndSession={handleEndSession}
          completedActions={completedActions}
        />
      </div>
    </div>
  );
}

export default App;
