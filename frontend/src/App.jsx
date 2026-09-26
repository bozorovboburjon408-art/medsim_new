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
      console.warn("Backend ulanganda API ishlaydi, hozir mock rejimda", e);
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
      console.warn("Backend javob bermadi, mock rejim:", error);

      // Mock javoblar (backend ishlamayotganda test uchun)
      const mockResponses = {
        bobo: [
          "Ha, qizim, tinglayapman. Bugun qon bosimim yana ko'tarildi shekilli...",
          "Rahmat bolam, biroz boshim aylanib, yuragim tez uryapti.",
          "Dori ichdim ertalab, lekin foydasi bo'lmadi shekilli.",
          "Oyoqlarim shishib ketdi, bolam, nima qilsam bo'ladi?"
        ],
        homilador: [
          "Opa, qornimning pasti sanchib og'riyapti... Bolamga zarar bo'lmaydimi?",
          "Kechadan beri bel og'rig'im qo'ymayapti, juda xavotirdaman.",
          "Bolam tepinyaptimi yoki og'riqmi, tushunmayapman...",
          "Iltimos, shifokorni chaqiring, menga yomon bo'lyapti!"
        ],
        bola: [
          "Oyim qani? Oyimni chaqiring!",
          "Ukol qilmang! Qo'rqaman!",
          "Qornim og'riyapti... Uyga ketgim kelyapti.",
          "Siz menga nima qilasiz? Qo'rqaman..."
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
      text: `📋 Seans boshlandi — ${data.scenarioTitle || 'Umumiy mashg\'ulot'}`,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  const handleEndSession = useCallback(() => {
    setConversation(prev => [...prev, {
      speaker: 'system',
      text: '✅ Seans yakunlandi.',
      timestamp: new Date().toISOString()
    }]);
    setSessionId(null);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-50 overflow-hidden">
      <StatusBar activeMannequin={activeMannequin} sessionId={sessionId} />

      <div className="flex flex-1 overflow-hidden">
        {/* Chap panel — Manikenlar */}
        <div className="w-1/4 h-full shrink-0">
          <MannequinSelector
            activeMannequin={activeMannequin}
            onSelect={handleSelectMannequin}
          />
        </div>

        {/* Markaziy panel — Suhbat + Mikrofon */}
        <div className="w-1/2 h-full flex flex-col shadow-[0_0_15px_rgba(0,0,0,0.05)] z-10 shrink-0 bg-white">
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

        {/* O'ng panel — Ssenariy */}
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
