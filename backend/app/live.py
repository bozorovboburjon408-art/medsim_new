"""Gemini Live sinov laboratoriyasi: brauzer mikrofoni -> bizning server -> Gemini Live (ovozdan-ovozga).
Faqat DEBUG_TOKEN bilan ochiladi. API kaliti brauzerga berilmaydi, server vositachi (proxy) bo'ladi."""
import asyncio
import json
import logging

import httpx
from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types

from .config import settings
from .patients import PATIENTS

log = logging.getLogger("uvicorn.error")
router = APIRouter()

VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe", "Enceladus",
    "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia",
    "Sadaltager", "Sulafat",
]
DEFAULT_VOICE = {"buvi": "Gacrux", "homilador": "Kore", "bola": "Leda"}
STYLE = {
    "buvi": "Speak slowly, in a weak, gentle, warm, slightly tired elderly woman's voice.",
    "homilador": "Speak in a warm, slightly tired adult woman's voice at a calm pace.",
    "bola": "Speak in a high, small, cute, slightly whiny 5-year-old child's voice, in very short childlike sentences.",
}
LIVE_RULES = (
    "\n\nOVOZLI SUHBAT: faqat o'zbek tilida gapir. Butun suhbat davomida aynan bir xil ovoz, ohang va tezlikda gapir. "
    "Faqat bemor rolida, juda qisqa (1-2 gap) javob ber. Hech qachon 'Bemor:' deb yozma va o'zingni AI deb aytma. "
    "Senariyda yo'q ma'lumotni o'zingdan to'qima: bilmasang 'bilmayman' de. Medsestra gapi tushunarsiz bo'lsa, qisqa qilib qaytadan so'ra. "
)
VOCAB = ["assalomu alaykum", "qandli diabet", "qon bosimi", "shifokor", "dori", "ukol", "homilador", "bosh og'rig'i",
         "qand", "insulin", "temperatura", "tomir urishi", "ahvolingiz qanday", "yurak", "oyoq", "qorin"]
MAX_SESSION_S = 600


class _Wrap:
    def __init__(self, cm, session):
        self.cm, self.session = cm, session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *a):
        return await self.cm.__aexit__(*a)


def _check(token: str):
    if not settings.debug_token or token != settings.debug_token:
        raise HTTPException(403, "Ruxsat yo'q")


@router.get("/live_models")
async def live_models(token: str = ""):
    """Kalitingiz bilan Live (bidiGenerateContent) qo'llab-quvvatlaydigan model ID'lari."""
    _check(token)
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                        headers={"x-goog-api-key": settings.gemini_api_key})
    if r.status_code >= 400:
        raise HTTPException(502, f"Gemini {r.status_code}: {r.text[:200]}")
    out = []
    for m in r.json().get("models", []):
        methods = m.get("supportedGenerationMethods", [])
        name = m["name"].removeprefix("models/")
        if "bidiGenerateContent" in methods or "live" in name or "native-audio" in name:
            out.append(name)
    return out


def build_config(patient_id: str, voice: str, ptt: int, hints: bool = True) -> types.LiveConnectConfig:
    p = PATIENTS[patient_id]
    voice = voice if voice in VOICES else DEFAULT_VOICE.get(patient_id, "Kore")
    system = p.system_prompt() + LIVE_RULES + STYLE.get(patient_id, "")
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
        system_instruction=system,
        input_audio_transcription=(types.AudioTranscriptionConfig(language_codes=["uz-UZ"], custom_vocabulary=VOCAB)
                                   if hints else types.AudioTranscriptionConfig()),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=(
                types.AutomaticActivityDetection(disabled=True) if ptt == 2 else types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    silence_duration_ms=600))),
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
    )


@router.websocket("/live_ws")
async def live_ws(ws: WebSocket, token: str = "", patient: str = "buvi", model: str = "", voice: str = "", ptt: int = 1):
    await ws.accept()
    if not settings.debug_token or token != settings.debug_token or patient not in PATIENTS or not model:
        await ws.send_json({"type": "error", "message": "Ruxsat yo'q yoki model/bemor noto'g'ri"})
        await ws.close()
        return
    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        cm = client.aio.live.connect(model=model, config=build_config(patient, voice, ptt))
        try:
            session = await cm.__aenter__()
        except Exception as e:
            log.warning("live: til sozlamalari rad etildi (%s), ularsiz qayta ulanyapman", e)
            await ws.send_json({"type": "note", "message": "Til sozlamalari qabul qilinmadi, ularsiz ulandi"})
            cm = client.aio.live.connect(model=model, config=build_config(patient, voice, ptt, hints=False))
            session = await cm.__aenter__()
        async with _Wrap(cm, session):
            await ws.send_json({"type": "ready"})
            stats = {"in_audio_bytes": 0, "out_audio_bytes": 0, "events": {}}

            def count(name: str):
                stats["events"][name] = stats["events"].get(name, 0) + 1

            async def from_browser():
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        return
                    if msg.get("bytes"):
                        stats["in_audio_bytes"] += len(msg["bytes"])
                        await session.send_realtime_input(audio=types.Blob(data=msg["bytes"], mime_type="audio/pcm;rate=16000"))
                    elif msg.get("text"):
                        ev = json.loads(msg["text"])
                        t = ev.get("type")
                        if t == "start" and ptt == 2:
                            await session.send_realtime_input(activity_start=types.ActivityStart())
                        elif t == "end" and ptt == 2:
                            await session.send_realtime_input(activity_end=types.ActivityEnd())
                        elif t == "flush":  # mikrofon o'chirildi: keshdagi ovozni ishlashga yuborish
                            await session.send_realtime_input(audio_stream_end=True)
                        elif t == "text" and ev.get("text"):  # diagnostika: mikrofonsiz, matn bilan
                            await session.send_realtime_input(text=str(ev["text"])[:500])
                        elif t == "close":
                            return

            async def to_browser():
                while True:
                    got = False
                    async for m in session.receive():
                        got = True
                        if m.setup_complete:
                            count("setup")
                            await ws.send_json({"type": "setup"})
                        sc = m.server_content
                        if sc:
                            if sc.model_turn:
                                for part in sc.model_turn.parts or []:
                                    if part.inline_data and part.inline_data.data:
                                        stats["out_audio_bytes"] += len(part.inline_data.data)
                                        count("audio")
                                        await ws.send_bytes(part.inline_data.data)
                                    elif getattr(part, "text", None) and not getattr(part, "thought", False):
                                        count("text")
                                        await ws.send_json({"type": "out", "text": part.text})
                            if sc.input_transcription and sc.input_transcription.text:
                                count("in_transcript")
                                await ws.send_json({"type": "in", "text": sc.input_transcription.text})
                            if sc.output_transcription and sc.output_transcription.text:
                                await ws.send_json({"type": "out", "text": sc.output_transcription.text})
                            if sc.interrupted:
                                await ws.send_json({"type": "interrupted"})
                            if sc.turn_complete:
                                count("turn_complete")
                                await ws.send_json({"type": "turn_complete"})
                        um = m.usage_metadata
                        if um:
                            def by_modality(items):
                                return {str(getattr(getattr(x, "modality", None), "name", getattr(x, "modality", "?"))):
                                        getattr(x, "token_count", 0) for x in (items or [])}
                            await ws.send_json({"type": "usage", "prompt": um.prompt_token_count, "response": um.response_token_count,
                                                "thoughts": um.thoughts_token_count, "total": um.total_token_count,
                                                "cached": um.cached_content_token_count,
                                                "prompt_by": by_modality(um.prompt_tokens_details),
                                                "response_by": by_modality(um.response_tokens_details)})
                        if m.go_away:
                            await ws.send_json({"type": "go_away"})
                    if not got:
                        await asyncio.sleep(0.1)

            async def reporter():  # har 2 soniyada hisobot: brauzerda ham, Render loglarida ham ko'rinadi
                while True:
                    await asyncio.sleep(2)
                    await ws.send_json({"type": "stats", **stats})
                    log.info("live %s/%s stats=%s", patient, model, stats)

            tasks = [asyncio.create_task(from_browser()), asyncio.create_task(to_browser()), asyncio.create_task(reporter())]
            done, pending = await asyncio.wait(tasks, timeout=MAX_SESSION_S, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            for t in done:
                if t.exception():
                    raise t.exception()
            if not done:
                await ws.send_json({"type": "error", "message": "Sessiya vaqti tugadi (10 daqiqa)"})
    except Exception as e:
        log.warning("live_ws xatosi: %s", e)
        try:
            await ws.send_json({"type": "error", "message": f"{type(e).__name__}: {e}"[:400]})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


LAB_HTML = r"""<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MedSim Live laboratoriyasi</title><style>
body{font-family:system-ui,sans-serif;background:#f3f7f6;margin:0;padding:16px;color:#0f172a;max-width:760px}
h1{color:#0f766e;font-size:22px}.card{background:#fff;border-radius:18px;padding:16px;margin:12px 0;box-shadow:0 1px 4px #0002}
label{display:block;margin:8px 0 2px;font-size:14px;color:#475569}select{width:100%;font-size:15px;padding:6px;box-sizing:border-box}
button{background:#0f766e;color:#fff;border:0;border-radius:12px;padding:14px 22px;font-size:17px;margin:8px 6px 0 0}
button:disabled{background:#94a3b8}#talk{background:#b91c1c;user-select:none;touch-action:none}
#log{min-height:140px;white-space:pre-wrap;line-height:1.5}.n{color:#0f766e;font-weight:600}.p{color:#7c3aed;font-weight:600}
code{background:#e4eceb;padding:2px 6px;border-radius:6px}.s{color:#475569;font-size:14px}
</style></head><body>
<h1>Live laboratoriyasi (Gemini ovozdan-ovozga)</h1>
<div class="card">
 <label>Bemor</label><select id="patient"><option value="buvi">Salomat buvi</option><option value="homilador">Nilufar (homilador)</option><option value="bola">Jasurbek (bola)</option></select>
 <label>Live modeli (ro'yxat serverdan olinadi)</label><select id="model"><option value="">yuklanmoqda…</option></select>
 <label>Gemini ovozi</label><select id="voice"></select>
 <label>Gapirish rejimi</label><select id="mode"><option value="1">Tugmani bosib turib gapirish (tavsiya)</option><option value="0">Avtomatik (o'zi eshitadi, quloqchin kerak)</option><option value="2">Qo'lda signal (tajribaviy)</option></select>
 <button id="conn">Ulanish</button><button id="stop" disabled>To'xtatish</button>
 <p class="s" id="status">Ulanmagan</p>
</div>
<div class="card"><button id="talk" disabled>🎤 Bosib turing va gapiring</button>
 <div style="background:#e4eceb;border-radius:8px;height:10px;margin-top:10px"><div id="lvl" style="background:#15803d;height:10px;width:0%;border-radius:8px"></div></div>
 <p class="s">Mikrofon darajasi (gapirganda yashil chiziq o'sishi kerak)</p>
 <p class="s" id="lat"></p><p class="s" id="usage"></p><p class="s" id="diag"></p>
 <label>Mikrofonsiz sinov: matn yozib yuboring (javob ovozda chiqsa, model va ovoz ishlayapti)</label>
 <input id="txt" style="width:100%;padding:8px;font-size:15px;box-sizing:border-box" value="Assalomu alaykum buvi, ahvollaringiz qanday?">
 <button id="sendtxt" disabled>Matnni yuborish</button></div>
<div class="card"><b>Suhbat</b><div id="log"></div></div>
<script>
const token=new URLSearchParams(location.search).get('token')||'';
const $=id=>document.getElementById(id);
const VOICES=__VOICES__, DEFAULTS=__DEFAULTS__;
$('voice').innerHTML=VOICES.map(v=>`<option>${v}</option>`).join('');
const setVoice=()=>{$('voice').value=DEFAULTS[$('patient').value]||'Kore';};setVoice();$('patient').onchange=setVoice;
fetch('/live_models?token='+encodeURIComponent(token)).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
 .then(l=>{$('model').innerHTML=l.map(m=>`<option>${m}</option>`).join('');const i=l.findIndex(m=>m.includes('3.8')&&m.includes('live'));if(i>=0)$('model').selectedIndex=i;})
 .catch(e=>{$('model').innerHTML='<option value="">model roʻyxati yuklanmadi: '+e+'</option>';});
let ws=null,mic=null,actx=null,node=null,pctx=null,nextT=0,sending=false,tEnd=0,waitFirst=false,srcs=[],cur=null;
let rbuf=[],pos=0,bytesSent=0,bytesRecv=0,srvStats='';
const status=t=>$('status').textContent=t;
function line(cls,t){cur=document.createElement('div');cur.innerHTML=`<span class="${cls==='n'?'n':'p'}">${cls==='n'?'Hamshira':'Bemor'}:</span> <span class="t"></span>`;$('log').appendChild(cur);cur.dataset.k=cls;}
function addText(cls,t){if(!cur||cur.dataset.k!==cls)line(cls);cur.querySelector('.t').textContent+=t;}
function playPcm(buf){
 const i16=new Int16Array(buf),f=new Float32Array(i16.length);for(let i=0;i<i16.length;i++)f[i]=i16[i]/32768;
 const ab=pctx.createBuffer(1,f.length,24000);ab.copyToChannel(f,0);
 const s=pctx.createBufferSource();s.buffer=ab;s.connect(pctx.destination);
 const t=Math.max(pctx.currentTime+0.02,nextT);s.start(t);nextT=t+ab.duration;srcs.push(s);s.onended=()=>{srcs=srcs.filter(x=>x!==s);};
 if(waitFirst){waitFirst=false;$('lat').textContent='Birinchi ovozgacha: '+((performance.now()-tEnd)/1000).toFixed(1)+' s (tugmani qo’yib yuborganingizdan)';}
}
function stopPlay(){srcs.forEach(s=>{try{s.stop();}catch(e){}});srcs=[];nextT=0;}
function diag(){$('diag').textContent='Yuborilgan ovoz: '+(bytesSent/1024).toFixed(0)+' KB · Qabul qilingan ovoz: '+(bytesRecv/1024).toFixed(0)+' KB'+srvStats;}
function sendPcm(f32,rate){
 let sum=0;for(const v of f32)sum+=v*v;$('lvl').style.width=Math.min(100,Math.sqrt(sum/f32.length)*600)+'%';
 for(const v of f32)rbuf.push(v);
 const ratio=rate/16000,out=[];
 while(pos+1<rbuf.length){const i=Math.floor(pos),fr=pos-i;out.push(rbuf[i]*(1-fr)+rbuf[i+1]*fr);pos+=ratio;}
 const drop=Math.floor(pos);rbuf=rbuf.slice(drop);pos-=drop;
 if(out.length&&ws&&ws.readyState===1&&sending){const i16=new Int16Array(out.length);for(let i=0;i<out.length;i++)i16[i]=Math.max(-1,Math.min(1,out[i]))*32767;ws.send(i16.buffer);bytesSent+=i16.buffer.byteLength;diag();}
}
const WORKLET='class Cap extends AudioWorkletProcessor{process(inputs){const c=inputs[0][0];if(c)this.port.postMessage(c.slice(0));return true;}}registerProcessor("cap",Cap);';
async function connect(){
 $('conn').disabled=true;status('Ulanilmoqda…');
 try{
  pctx=new AudioContext({sampleRate:24000});
  mic=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}});
  actx=new AudioContext();await actx.resume();await pctx.resume();await actx.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET],{type:'application/javascript'})));
  node=new AudioWorkletNode(actx,'cap');node.port.onmessage=e=>sendPcm(e.data,actx.sampleRate);
  const src=actx.createMediaStreamSource(mic);const mute=actx.createGain();mute.gain.value=0;src.connect(node);node.connect(mute);mute.connect(actx.destination);
 }catch(e){status('Mikrofon xatosi: '+e);$('conn').disabled=false;return;}
 const mode=$('mode').value,ptt=mode!=='0';
 const u=(location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/live_ws?token='+encodeURIComponent(token)+'&patient='+$('patient').value+'&model='+encodeURIComponent($('model').value)+'&voice='+$('voice').value+'&ptt='+mode;
 ws=new WebSocket(u);ws.binaryType='arraybuffer';
 ws.onmessage=ev=>{
  if(typeof ev.data!=='string'){bytesRecv+=ev.data.byteLength;diag();playPcm(ev.data);return;}
  const m=JSON.parse(ev.data);
  if(m.type==='ready'){status('Ulandi. '+(ptt?'Tugmani bosib turib gapiring.':'Gapiravering.'));$('talk').disabled=!ptt;$('sendtxt').disabled=false;$('stop').disabled=false;if(!ptt){sending=true;}}
  else if(m.type==='setup'){status('Model sozlandi (setup). Gapiring.');}
  else if(m.type==='stats'){srvStats=' · Server: kirgan ovoz '+(m.in_audio_bytes/1024).toFixed(0)+' KB, hodisalar '+JSON.stringify(m.events);diag();}
  else if(m.type==='in')addText('n',m.text);
  else if(m.type==='out')addText('p',m.text);
  else if(m.type==='interrupted'){stopPlay();}
  else if(m.type==='turn_complete'){cur=null;}
  else if(m.type==='usage')$('usage').textContent='Tokenlar: kirish '+m.prompt+' · chiqish '+m.response+' · o’ylash '+(m.thoughts||0)+' · jami '+m.total+' · keshdan '+(m.cached||0)+' | kirish turlari '+JSON.stringify(m.prompt_by||{})+' | chiqish turlari '+JSON.stringify(m.response_by||{});
  else if(m.type==='error'){status('Xato: '+m.message);}
  else if(m.type==='note'){status(m.message);}
  else if(m.type==='go_away'){status('Server sessiyani yopmoqda');}
 };
 ws.onclose=()=>{status('Ulanish yopildi');$('talk').disabled=true;$('sendtxt').disabled=true;$('stop').disabled=true;$('conn').disabled=false;sending=false;};
 ws.onerror=()=>status('WebSocket xatosi');
}
function pttStart(e){e.preventDefault();if(!ws||ws.readyState!==1)return;stopPlay();sending=true;if($('mode').value==='2')ws.send(JSON.stringify({type:'start'}));$('talk').textContent='🔴 Gapiring… (qo’yib yuboring)';}
function pttEnd(e){e.preventDefault();if(!sending||!ws)return;sending=false;setTimeout(()=>{if($('mode').value==='2'){ws.send(JSON.stringify({type:'end'}));}else{ws.send(new Int16Array(12800).buffer);ws.send(JSON.stringify({type:'flush'}));}tEnd=performance.now();waitFirst=true;},150);$('talk').textContent='🎤 Bosib turing va gapiring';}
const tb=$('talk');['mousedown','touchstart'].forEach(n=>tb.addEventListener(n,pttStart));['mouseup','mouseleave','touchend','touchcancel'].forEach(n=>tb.addEventListener(n,pttEnd));
$('conn').onclick=connect;
$('sendtxt').onclick=()=>{if(!ws||ws.readyState!==1)return;stopPlay();addText('n',$('txt').value);cur=null;ws.send(JSON.stringify({type:'text',text:$('txt').value}));tEnd=performance.now();waitFirst=true;};
$('stop').onclick=()=>{if(ws){try{ws.send(JSON.stringify({type:'close'}));ws.close();}catch(e){}}stopPlay();if(mic)mic.getTracks().forEach(t=>t.stop());if(actx)actx.close();status('To’xtatildi');};
</script></body></html>"""


@router.get("/live_lab", response_class=HTMLResponse)
async def live_lab(token: str = ""):
    _check(token)
    return LAB_HTML.replace("__VOICES__", json.dumps(VOICES)).replace("__DEFAULTS__", json.dumps(DEFAULT_VOICE))
