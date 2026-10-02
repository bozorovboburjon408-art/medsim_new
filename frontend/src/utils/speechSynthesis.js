/**
 * Audio Player & Speech Synthesis Helper
 * Serverdan kelgan yuqori sifatli sof O'zbek tili Neural MP3 ovozini yangratadi.
 */

let currentAudio = null;

export function playAudioResponse(audioBase64, text, mannequinSlug = 'homilador') {
  // Avvalgi audio/ovozni to'xtatish
  if (currentAudio) {
    try {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    } catch (e) {}
    currentAudio = null;
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }

  // Chaqaloq ovozi bo'lsa
  if (mannequinSlug === 'chaqaloq') {
    if (audioBase64) {
      try {
        const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
        currentAudio = audio;
        audio.play().catch(e => console.warn("Audio play xatosi:", e));
      } catch (e) {}
    }
    return;
  }

  // 1. Agar serverdan sof O'zbek tili Base64 MP3 kelgan bo'lsa (Eng mukammal ovoz)
  if (audioBase64) {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
      currentAudio = audio;
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch(error => {
          console.warn("Autoplay cheklovi, brauzer sinteziga o'tilmoqda:", error);
          speakBrowserFallback(text, mannequinSlug);
        });
      }
      return;
    } catch (e) {
      console.warn("Audio yaratish xatosi:", e);
    }
  }

  // 2. Agar audioBase64 bo'lmasa -> Brauzer sintez fallback
  speakBrowserFallback(text, mannequinSlug);
}

function speakBrowserFallback(text, mannequinSlug) {
  if (!window.speechSynthesis) return;

  const cleanText = (text || '').replace(/\*[^*]+\*/g, '').trim();
  if (!cleanText) return;

  const utterance = new SpeechSynthesisUtterance(cleanText);

  switch (mannequinSlug) {
    case 'bobo':
      utterance.pitch = 0.7;
      utterance.rate = 0.85;
      break;
    case 'homilador':
      utterance.pitch = 1.05;
      utterance.rate = 0.95;
      break;
    case 'bola':
      utterance.pitch = 1.45;
      utterance.rate = 1.1;
      break;
    default:
      utterance.pitch = 1.0;
      utterance.rate = 1.0;
  }

  const voices = window.speechSynthesis.getVoices();
  const uzVoice = voices.find(v => v.lang.startsWith('uz') || v.lang.startsWith('tr') || v.lang.startsWith('ru'));
  if (uzVoice) {
    utterance.voice = uzVoice;
  }

  window.speechSynthesis.speak(utterance);
}

// Eski importlar uchun backward compatibility
export const speakText = (text, mannequinSlug) => playAudioResponse(null, text, mannequinSlug);

