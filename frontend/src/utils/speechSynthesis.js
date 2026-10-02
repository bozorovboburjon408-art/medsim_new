/**
 * Browser Speech Synthesis Helper
 * Matnni planshet/telefon/kompyuter dinamikidan ovoz chiqarib o'qib beradi.
 */

export function speakText(text, mannequinSlug = 'homilador') {
  if (!window.speechSynthesis) {
    console.warn("SpeechSynthesis brauzerda qo'llab-quvvatlanmaydi");
    return;
  }

  // To'xtatish (agar avvalgi ovoz gapirayotgan bo'lsa)
  window.speechSynthesis.cancel();

  // Matndagi belgilarni tozalash (masalan *kulish*, *yig'lash*)
  const cleanText = text.replace(/\*[^*]+\*/g, '').trim();
  if (!cleanText) return;

  const utterance = new SpeechSynthesisUtterance(cleanText);

  // Qahramon ovozini sozlash
  switch (mannequinSlug) {
    case 'bobo':
      utterance.pitch = 0.7; // Qariya, past tembr
      utterance.rate = 0.85; // Sekin, og'ir gapirish
      break;
    case 'homilador':
      utterance.pitch = 1.1; // Ayol ovozi, mayin
      utterance.rate = 0.95;
      break;
    case 'bola':
      utterance.pitch = 1.5; // Bola ovozi, ingichka
      utterance.rate = 1.1;
      break;
    case 'chaqaloq':
      // Chaqaloq faqat tovush chiqaradi, sintez shart emas
      return;
    default:
      utterance.pitch = 1.0;
      utterance.rate = 1.0;
  }

  // O'zbek yoki yaqin tillar (mavjud bo'lsa)
  const voices = window.speechSynthesis.getVoices();
  const uzVoice = voices.find(v => v.lang.startsWith('uz') || v.lang.startsWith('tr') || v.lang.startsWith('ru'));
  if (uzVoice) {
    utterance.voice = uzVoice;
  }

  window.speechSynthesis.speak(utterance);
}
