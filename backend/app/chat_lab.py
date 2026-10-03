"""Web Chat Simulator: kompyuter yoki telefon brauzerida bemorlar bilan to'liq ovozli suhbat,
Gemini/Edge provayderlarini almashtirish va baholashni sinash sahifasi."""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from .config import settings
from .patients import PATIENTS

router = APIRouter()

HTML_PAGE = r"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MedSim Web Simulyatori</title>
<style>
  :root {
    --primary: #0f766e;
    --primary-light: #ccfbf1;
    --surface: #ffffff;
    --bg: #f8fafc;
    --text: #0f172a;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --user-bubble: #0f766e;
    --patient-bubble: #ffffff;
    --accent: #d97706;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 16px;
    display: flex;
    justify-content: center;
  }
  .app-container {
    width: 100%;
    max-width: 900px;
    display: flex;
    flex-direction: column;
    height: 94vh;
    background: var(--surface);
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    overflow: hidden;
    border: 1px solid var(--border);
  }
  header {
    padding: 14px 20px;
    background: #ffffff;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }
  .title-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .title-group h1 {
    font-size: 20px;
    margin: 0;
    color: var(--primary);
  }
  .badge {
    background: #dcfce7;
    color: #15803d;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 999px;
  }
  .controls-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  select, button {
    font-family: inherit;
    font-size: 14px;
    border-radius: 10px;
    padding: 8px 12px;
    border: 1px solid var(--border);
  }
  select {
    background: #f8fafc;
    color: var(--text);
    font-weight: 500;
  }
  button.btn-primary {
    background: var(--primary);
    color: white;
    border: none;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }
  button.btn-primary:hover {
    background: #115e59;
  }
  button.btn-secondary {
    background: #f1f5f9;
    color: var(--text);
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .chat-body {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: #f8fafc;
  }
  .msg {
    max-width: 75%;
    display: flex;
    flex-direction: column;
    animation: fadeIn 0.2s ease;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .msg.user {
    align-self: flex-end;
  }
  .msg.assistant {
    align-self: flex-start;
  }
  .sender-name {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 4px;
    font-weight: 500;
  }
  .bubble {
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .msg.user .bubble {
    background: var(--user-bubble);
    color: white;
    border-bottom-right-radius: 4px;
  }
  .msg.assistant .bubble {
    background: var(--patient-bubble);
    color: var(--text);
    border-bottom-left-radius: 4px;
    border: 1px solid var(--border);
  }
  .bubble-footer {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    font-size: 11px;
    color: var(--text-muted);
  }
  .play-icon-btn {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    font-size: 14px;
    color: var(--primary);
  }
  .input-panel {
    padding: 14px 20px;
    background: #ffffff;
    border-top: 1px solid var(--border);
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .input-panel input {
    flex: 1;
    padding: 12px 16px;
    font-size: 15px;
    border: 1px solid var(--border);
    border-radius: 12px;
    outline: none;
    background: #f8fafc;
  }
  .input-panel input:focus {
    border-color: var(--primary);
    background: #fff;
  }
  .btn-mic {
    background: #fee2e2;
    color: #ef4444;
    border: none;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.15s, background 0.2s;
  }
  .btn-mic.listening {
    background: #ef4444;
    color: white;
    transform: scale(1.1);
    animation: pulse 1s infinite alternate;
  }
  @keyframes pulse {
    from { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
    to { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  }
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 100;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }
  .modal-overlay.open {
    display: flex;
  }
  .modal-content {
    background: white;
    border-radius: 18px;
    max-width: 600px;
    width: 100%;
    max-height: 85vh;
    overflow-y: auto;
    padding: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
  }
  .score-badge {
    font-size: 32px;
    font-weight: bold;
    color: var(--primary);
  }
  .stage-row {
    background: #f8fafc;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    border: 1px solid var(--border);
  }
  .stage-title {
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    font-size: 14px;
  }
</style>
</head>
<body>

<div class="app-container">
  <header>
    <div class="title-group">
      <h1>MedSim Simulyatori</h1>
      <span class="badge" id="backendStatus">● Onlayn</span>
    </div>
    <div class="controls-bar">
      <select id="patientSelect">
        <option value="buvi">👵 Salomat buvi (75 yosh)</option>
        <option value="bobo">👴 Hikmatilla ota (78 yosh)</option>
        <option value="homilador">🤰 Nilufar opa (33 yosh)</option>
        <option value="bola">👦 Jasurbek (5 yosh)</option>
      </select>
      <select id="ttsSelect">
        <option value="edge" selected>🔊 Edge TTS (Tavsiya - Bepul)</option>
        <option value="gemini">✨ Gemini Audio (Pullik API)</option>
        <option value="elevenlabs">🎙 ElevenLabs (Realistik)</option>
      </select>
      <button class="btn-secondary" id="evalBtn" title="Hamshira ishini baholash">📋 Baholash</button>
      <button class="btn-secondary" id="clearBtn" title="Suhbatni tozalash">↻ Yangi</button>
    </div>
  </header>

  <div class="chat-body" id="chatBox">
    <div class="msg assistant">
      <div class="sender-name">Simulyator</div>
      <div class="bubble">
        Assalomu alaykum! Bemorni va ovozni tanlang. Pastdagi mikrofondan gapiring yoki matn yozib <b>Enter</b> bosing. Bemorning ovozli javobi to'g'ridan-to'g'ri yangraydi.
      </div>
    </div>
  </div>

  <div class="input-panel">
    <button class="btn-mic" id="micBtn" title="Gapirish uchun bosing">🎤</button>
    <input type="text" id="userInput" placeholder="Hamshira gapini yozing yoki mikrofondan gapiring..." autocomplete="off">
    <button class="btn-primary" id="sendBtn">Yuborish</button>
  </div>
</div>

<!-- Baholash modali -->
<div class="modal-overlay" id="evalModal">
  <div class="modal-content">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <h2 style="margin:0; font-size:20px; color:var(--primary);">Patronaj Baholash Natijalari</h2>
      <button class="btn-secondary" id="closeEvalBtn" style="padding:4px 10px;">✕</button>
    </div>
    <div id="evalBody">Yuklanmoqda…</div>
  </div>
</div>

<script>
  const token = new URLSearchParams(location.search).get('token') || '';
  const chatBox = document.getElementById('chatBox');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const micBtn = document.getElementById('micBtn');
  const patientSelect = document.getElementById('patientSelect');
  const ttsSelect = document.getElementById('ttsSelect');
  const clearBtn = document.getElementById('clearBtn');
  const evalBtn = document.getElementById('evalBtn');
  const evalModal = document.getElementById('evalModal');
  const closeEvalBtn = document.getElementById('closeEvalBtn');
  const evalBody = document.getElementById('evalBody');

  let history = [];
  const audioQueue = [];
  let isPlaying = false;

  function appendMessage(role, text, stats = null, audioB64 = null, fmt = 'wav') {
    const isUser = role === 'user';
    const patientName = patientSelect.options[patientSelect.selectedIndex].text.split(' ')[1] || 'Bemor';
    const sender = isUser ? 'Siz (hamshira)' : patientName;

    const div = document.createElement('div');
    div.className = `msg ${role}`;
    
    let html = `<div class="sender-name">${sender}</div><div class="bubble">${text}</div>`;
    if (stats || audioB64) {
      html += `<div class="bubble-footer">`;
      if (audioB64) {
        html += `<button class="play-icon-btn" onclick="playAudioDirect('${audioB64}', '${fmt}')">▶ Qayta tinglash</button>`;
      }
      if (stats) {
        html += `<span>· ${stats}</span>`;
      }
      html += `</div>`;
    }
    div.innerHTML = html;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  function queueAudio(audioB64, fmt) {
    const mime = (fmt && fmt.toLowerCase().includes('mp3')) ? 'audio/mpeg' : 'audio/wav';
    const audio = new Audio(`data:${mime};base64,` + audioB64);
    audioQueue.push(audio);
    if (!isPlaying) playNextAudio();
  }

  function playNextAudio() {
    if (audioQueue.length === 0) {
      isPlaying = false;
      return;
    }
    isPlaying = true;
    const audio = audioQueue.shift();
    audio.onended = () => playNextAudio();
    audio.onerror = () => playNextAudio();
    audio.play().catch(() => playNextAudio());
  }

  window.playAudioDirect = function(audioB64, fmt) {
    const mime = (fmt && fmt.toLowerCase().includes('mp3')) ? 'audio/mpeg' : 'audio/wav';
    const a = new Audio(`data:${mime};base64,` + audioB64);
    a.play().catch(e => console.warn("Audio play xatosi:", e));
  };

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    userInput.value = '';

    history.push({ role: 'user', content: text });
    appendMessage('user', text);

    sendBtn.disabled = true;
    const patientId = patientSelect.value;
    const tts = ttsSelect.value;

    try {
      const resp = await fetch('/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientId,
          history: history,
          tts: tts
        })
      });

      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(err || "Server xatosi");
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let replyParts = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          const seg = JSON.parse(line);
          if (seg.error) throw new Error(seg.error);
          if (seg.text) {
            replyParts.push(seg.text);
            const stats = `AI: ${seg.llm_ms}ms · Ovoz: ${seg.tts_ms}ms (${seg.tts || tts})`;
            appendMessage('assistant', seg.text, stats, seg.audio_b64, seg.fmt);
            if (seg.audio_b64) queueAudio(seg.audio_b64, seg.fmt);
          }
        }
      }

      if (replyParts.length > 0) {
        history.push({ role: 'assistant', content: replyParts.join(' ') });
      }
    } catch (e) {
      appendMessage('assistant', 'Xato: ' + e.message);
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.onclick = sendMessage;
  userInput.onkeydown = (e) => { if (e.key === 'Enter') sendMessage(); };

  clearBtn.onclick = () => {
    history = [];
    audioQueue.length = 0;
    chatBox.innerHTML = `
      <div class="msg assistant">
        <div class="sender-name">Simulyator</div>
        <div class="bubble">Yangi suhbat boshlandi. Hamshira sifatida bemorga murojaat qiling.</div>
      </div>
    `;
  };

  // Brauzer Speech-to-Text (O'zbekcha)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    const rec = new SpeechRecognition();
    rec.lang = 'uz-UZ';
    rec.continuous = false;
    rec.interimResults = false;

    let isRec = false;
    micBtn.onclick = () => {
      if (isRec) { rec.stop(); return; }
      try { rec.start(); } catch (_) {}
    };

    rec.onstart = () => { isRec = true; micBtn.classList.add('listening'); };
    rec.onend = () => { isRec = false; micBtn.classList.remove('listening'); };
    rec.onresult = (e) => {
      const spoken = e.results[0][0].transcript;
      if (spoken) {
        userInput.value = spoken;
        sendMessage();
      }
    };
    rec.onerror = () => { isRec = false; micBtn.classList.remove('listening'); };
  } else {
    micBtn.style.display = 'none';
  }

  // Baholash
  evalBtn.onclick = async () => {
    if (history.length === 0) {
      alert("Avval bemor bilan biroz suhbatlashing!");
      return;
    }
    evalModal.classList.add('open');
    evalBody.innerHTML = '<div style="text-align:center; padding:30px;">AI patronaj muloqotingizni baholamoqda… (5-15 soniya)</div>';

    try {
      const resp = await fetch('/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: patientSelect.value,
          history: history
        })
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();

      let h = `
        <div style="text-align:center; margin-bottom:20px;">
          <div class="score-badge">${data.total} / 100</div>
          <div style="color:var(--text-muted); font-size:14px;">Umumiy ball</div>
        </div>
        <p><b>Xulosa:</b> ${data.summary || 'Izoh berilmagan'}</p>
        <h4 style="margin:14px 0 8px;">Bosqichlar bo'yicha:</h4>
      `;
      (data.stages || []).forEach(s => {
        h += `
          <div class="stage-row">
            <div class="stage-title"><span>${s.name}</span> <span>${s.score} / ${s.max}</span></div>
            ${s.done && s.done.length ? `<div style="color:#15803d; font-size:12px; margin-top:4px;">✓ Bajarildi: ${s.done.join(', ')}</div>` : ''}
            ${s.missed && s.missed.length ? `<div style="color:#b91c1c; font-size:12px; margin-top:2px;">✗ Qoldirildi: ${s.missed.join(', ')}</div>` : ''}
          </div>
        `;
      });
      if (data.strengths && data.strengths.length) {
        h += `<h4 style="margin:14px 0 6px; color:#15803d;">Yutuqlar:</h4><ul>${data.strengths.map(x => `<li>${x}</li>`).join('')}</ul>`;
      }
      if (data.advice && data.advice.length) {
        h += `<h4 style="margin:14px 0 6px; color:#d97706;">Tavsiyalar:</h4><ul>${data.advice.map(x => `<li>${x}</li>`).join('')}</ul>`;
      }
      evalBody.innerHTML = h;
    } catch (e) {
      evalBody.innerHTML = `<div style="color:red;">Baholashda xato: ${e.message}</div>`;
    }
  };

  closeEvalBtn.onclick = () => evalModal.classList.remove('open');
</script>
</body>
</html>
"""


@router.get("/chat_lab", response_class=HTMLResponse)
@router.get("/simulator", response_class=HTMLResponse)
@router.get("/test", response_class=HTMLResponse)
async def chat_lab(token: str = ""):
    """Web Chat Simulyatori sahifasi."""
    if settings.debug_token and token and token != settings.debug_token:
        raise HTTPException(403, "Ruxsat yo'q")
    return HTML_PAGE
