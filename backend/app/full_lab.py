"""To'liq zanjirni bitta sahifada sinash: mikrofon -> Gemini matn -> Gemini javob -> Gemini ovoz (oqim)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from .config import settings
from .patients import PATIENTS

router = APIRouter()

PAGE = r"""<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MedSim: to'liq sinov</title><style>
body{font-family:system-ui,sans-serif;background:#f3f7f6;margin:0;padding:16px;color:#0f172a}
h1{color:#0f766e;font-size:22px}.card{background:#fff;border-radius:18px;padding:16px;margin:14px 0;box-shadow:0 1px 4px #0002}
label{display:block;margin:10px 0 2px;font-size:14px;color:#475569}select{font-size:15px;padding:6px;width:100%;box-sizing:border-box}
button{background:#b91c1c;color:#fff;border:0;border-radius:12px;padding:18px 28px;font-size:18px;margin-top:10px}button.n{background:#334155;font-size:15px;padding:10px 16px}
.bar{height:10px;background:#e4eceb;border-radius:6px;margin-top:10px}.bar i{display:block;height:10px;width:0;background:#15803d;border-radius:6px}
.m{font-size:13px;color:#475569;margin:6px 0}.n1{color:#0f766e;font-weight:600}.n2{color:#7c3aed;font-weight:600}.row{margin:6px 0;font-size:16px}</style></head><body>
<h1>To'liq sinov: mikrofon &rarr; Gemini &rarr; ovoz</h1>
<div class="card">
<label>Bemor</label><select id="p">__PATIENTS__</select>
<label>Ovoz</label><select id="e"><option value="eleven">ElevenLabs ovozi (asosiy; xato bo'lsa Edge)</option><option value="gemini">Gemini ovozi (oqim, xato bo'lsa Edge)</option><option value="edge_only">Edge ovozi</option></select>
<label>Ovozdan matn</label><select id="se"><option value="gemini">Gemini</option><option value="eleven">ElevenLabs Scribe</option></select>
<label>Gemini matn modeli (faqat Gemini uchun)</label><select id="sm"><option value="">Avto (flash, keyin flash-lite)</option><option>gemini-2.5-flash</option><option>gemini-2.5-flash-lite</option><option>gemini-2.5-pro</option></select>
<label>Gemini TTS modeli</label><select id="gm"><option>gemini-2.5-flash-tts</option><option>gemini-2.5-pro-tts</option><option>gemini-2.5-flash-preview-tts</option><option>gemini-2.5-pro-preview-tts</option></select>
<label>Gemini ovozi</label><select id="gv"></select>
<label>ElevenLabs: ovoz ID, model, yozuv</label><input id="ev" style="width:100%;padding:6px;box-sizing:border-box" placeholder="ovoz ID (bo'sh = standart)">
<select id="em"><option>eleven_multilingual_v2</option><option>eleven_v3</option><option>eleven_flash_v2_5</option><option>eleven_turbo_v2_5</option></select>
<select id="es"><option value="lat">Lotin</option><option value="cyr">Kirill</option></select>
<label>Ovoz balandligi, tembr (1.00 = o'zgarishsiz; bola uchun 1.15–1.4): <span id="spv">1.00</span>x</label><input id="sp" type="range" min="80" max="170" value="100" style="width:100%">
<label>Gapirish tezligi (ElevenLabs; 1.00 = oddiy, sekinroq uchun 0.8): <span id="tpv">1.00</span>x</label><input id="tp" type="range" min="70" max="120" value="100" style="width:100%">
<label>Ifodalilik (0 = juda ifodali, 100 = barqaror): <span id="stv">40</span></label><input id="st2" type="range" min="0" max="100" value="40" style="width:100%">
<button id="b">🎤 Bosib turing va gapiring</button><div class="bar"><i id="lv"></i></div>
<div class="m" id="st">Tayyor.</div><div class="m" id="tm"></div>
<button class="n" id="rs">Yangi suhbat</button></div>
<div class="card"><b>Suhbat</b><div id="log"></div></div>
<script>
const token=new URLSearchParams(location.search).get('token')||'';const $=id=>document.getElementById(id);
const VOICES=__VOICES__,DEF=__DEF__,EVD=__EVD__,SP=__SP__,EMD=__EMD__,TP=__TP__;
$('gv').innerHTML=VOICES.map(v=>'<option>'+v+'</option>').join('');
const setSp=()=>{const q=SP[$('p').value]||{};const v=($('e').value==='eleven'?q.eleven:q.gemini)||1;$('sp').value=Math.round(v*100);$('spv').textContent=v.toFixed(2);const t=TP[$('p').value]||{tempo:1,stab:0.4};$('tp').value=Math.round(t.tempo*100);$('tpv').textContent=t.tempo.toFixed(2);$('st2').value=Math.round(t.stab*100);$('stv').textContent=$('st2').value;};
$('sp').oninput=()=>{$('spv').textContent=($('sp').value/100).toFixed(2);};$('tp').oninput=()=>{$('tpv').textContent=($('tp').value/100).toFixed(2);};$('st2').oninput=()=>{$('stv').textContent=$('st2').value;};$('e').onchange=setSp;
const setV=()=>{$('gv').value=DEF[$('p').value]||'Kore';$('ev').value=EVD[$('p').value]||'';$('em').value=EMD[$('p').value]||'eleven_multilingual_v2';setSp();};setV();$('p').onchange=()=>{setV();hist=[];$('log').innerHTML='';};
let hist=[],ctx=null,stream=null,proc=null,chunks=[],rec=false,ac=null,next=0,chain=Promise.resolve();
function wav(f32,rate){const n=f32.length,b=new ArrayBuffer(44+n*2),v=new DataView(b);const w=(o,s)=>{for(let i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));};
 w(0,'RIFF');v.setUint32(4,36+n*2,true);w(8,'WAVE');w(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,rate,true);v.setUint32(28,rate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);w(36,'data');v.setUint32(40,n*2,true);
 for(let i=0;i<n;i++){const s=Math.max(-1,Math.min(1,f32[i]));v.setInt16(44+i*2,s<0?s*0x8000:s*0x7fff,true);}return new Blob([b],{type:'audio/wav'});}
function down(f,from,to){if(from===to)return f;const r=from/to,n=Math.floor(f.length/r),o=new Float32Array(n);for(let i=0;i<n;i++){const a=Math.floor(i*r),e=Math.min(f.length,Math.floor((i+1)*r));let s=0;for(let j=a;j<e;j++)s+=f[j];o[i]=s/Math.max(1,e-a);}return o;}
const b64=s=>{const bin=atob(s),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return u;};
function addRow(who,text,cls){const d=document.createElement('div');d.className='row';d.innerHTML='<span class="'+cls+'">'+who+':</span> ';const t=document.createElement('span');t.textContent=text;d.appendChild(t);$('log').appendChild(d);return t;}
function play(u8,rate){const n=u8.length>>1,dv=new DataView(u8.buffer,u8.byteOffset,n*2),f=new Float32Array(n);for(let i=0;i<n;i++)f[i]=dv.getInt16(i*2,true)/32768;
 const buf=ac.createBuffer(1,n,rate);buf.copyToChannel(f,0);const s=ac.createBufferSource();s.buffer=buf;s.connect(ac.destination);if(next<ac.currentTime)next=ac.currentTime+0.03;s.start(next);next+=buf.duration;}
let ready=false,ring=[],ringLen=0;
async function initMic(){if(ready)return;stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
 ctx=new (window.AudioContext||window.webkitAudioContext)();const src=ctx.createMediaStreamSource(stream);proc=ctx.createScriptProcessor(4096,1,1);
 proc.onaudioprocess=e=>{const d=new Float32Array(e.inputBuffer.getChannelData(0));let m=0;for(const x of d)m=Math.max(m,Math.abs(x));$('lv').style.width=Math.min(100,m*140)+'%';
  if(rec){chunks.push(d);}else{ring.push(d);ringLen+=d.length;while(ring.length>1&&ringLen-ring[0].length>ctx.sampleRate*0.7){ringLen-=ring.shift().length;}}};
 src.connect(proc);proc.connect(ctx.destination);ready=true;}
async function start(){if(rec)return;if(!ac)ac=new (window.AudioContext||window.webkitAudioContext)();ac.resume();
 try{await initMic();}catch(e){$('st').textContent='Mikrofon ruxsati yo\u2018q: '+e;return;}
 if(ctx.state==='suspended')ctx.resume();chunks=ring.slice();ring=[];ringLen=0;rec=true;$('st').textContent='Yozilyapti... gapirib bo\u2018lgach qo\u2018yib yuboring';}
async function stop(){if(!rec)return;await new Promise(r=>setTimeout(r,350));rec=false;const T0=performance.now()-350,rate=ctx.sampleRate;$('lv').style.width='0';
 let n=0;for(const c of chunks)n+=c.length;if(n<rate*0.3){$('st').textContent='Juda qisqa, qaytadan urining';return;}
 let sq=0;for(const c of chunks)for(let i=0;i<c.length;i+=8)sq+=c[i]*c[i];if(Math.sqrt(sq/(n/8))<0.004){$('st').textContent='Ovoz juda past eshitildi (mikrofonni tekshiring), qaytadan urining';return;}
 const all=new Float32Array(n);let p=0;for(const c of chunks){all.set(c,p);p+=c.length;}
 const sec=()=>((performance.now()-T0)/1000).toFixed(1);const tm={};
 try{$('st').textContent='1/3 Gapingiz matnga aylantirilyapti...';
  const r1=await fetch('/transcribe?engine='+$('se').value+($('sm').value?'&model='+encodeURIComponent($('sm').value):''),{method:'POST',headers:{'Content-Type':'audio/wav'},body:wav(down(all,rate,16000),16000)});
  const t1=await r1.text();if(!r1.ok)throw new Error('Ovozdan matn: HTTP '+r1.status+' '+t1.slice(0,200));
  const text=JSON.parse(t1).text.trim();tm.stt=sec();if(!text){$('st').textContent='Nutq topilmadi, qaytadan urining';return;}
  addRow('Siz',text,'n1');hist.push({role:'user',content:text});
  $('st').textContent='2/3 Bemor o‘ylayapti...';
  const body={patient_id:$('p').value,history:hist,tts:$('e').value,tts_model:$('e').value==='eleven'?$('em').value:$('gm').value,gemini_voice:$('gv').value,eleven_voice:$('ev').value.trim()||null,eleven_script:$('es').value,voice_speed:($('e').value==='edge_only')?null:$('sp').value/100,eleven_tempo:$('tp').value/100,eleven_stability:$('st2').value/100};
  const r2=await fetch('/chat_stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!r2.ok)throw new Error('Javob: HTTP '+r2.status+' '+(await r2.text()).slice(0,200));
  const rd=r2.body.getReader(),dec=new TextDecoder();let buf='',full='',tgt=null,first=null,segs=[];
  const handle=async j=>{if(j.error)throw new Error(j.error);
   if(j.text){if(!tgt)tgt=addRow('Bemor','','n2');full+=(full?' ':'')+j.text;tgt.textContent=full;}
   if(j.pcm_b64){play(b64(j.pcm_b64),j.rate||24000);}
   else if(j.audio_b64){const u=b64(j.audio_b64);const ab=await ac.decodeAudioData(u.buffer.slice(u.byteOffset,u.byteOffset+u.byteLength));const s=ac.createBufferSource();s.buffer=ab;s.connect(ac.destination);if(next<ac.currentTime)next=ac.currentTime+0.03;s.start(next);next+=ab.duration;}
   if(first===null){first=sec();$('st').textContent='3/3 Bemor gapiryapti...';}
   if(j.text)segs.push('gap '+(segs.length+1)+': AI '+j.llm_ms+' ms, birinchi ovoz bo\u2018lagi '+j.tts_ms+' ms ('+j.tts+')');};
  for(;;){const {done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});let i;
   while((i=buf.indexOf('\n'))>=0){const line=buf.slice(0,i).trim();buf=buf.slice(i+1);if(line)await handle(JSON.parse(line));}}
  if(buf.trim())await handle(JSON.parse(buf));
  hist.push({role:'assistant',content:full});
  $('st').textContent='Tayyor.';$('tm').textContent='Mikrofon qo‘yib yuborilgandan: matn tayyor '+tm.stt+' s, BIRINCHI TOVUSH '+first+' s, hammasi '+sec()+' s | '+segs.join(' | ');
 }catch(e){$('st').textContent='Xato: '+e;}}
const b=$('b');['mousedown','touchstart'].forEach(e=>b.addEventListener(e,ev=>{ev.preventDefault();start();}));
['mouseup','mouseleave','touchend','touchcancel'].forEach(e=>b.addEventListener(e,ev=>{ev.preventDefault();stop();}));
initMic().catch(()=>{});
$('rs').onclick=()=>{hist=[];$('log').innerHTML='';$('tm').textContent='';$('st').textContent='Yangi suhbat.';};
</script></body></html>"""


@router.get("/full_lab", response_class=HTMLResponse)
async def full_lab(token: str = ""):
    import json

    from .eleven import DEFAULT_MODEL as DEFAULT_MODEL_ELEVEN
    from .eleven import DEFAULT_VOICE as DEFAULT_VOICE_ELEVEN
    from .tts import GEMINI_DEFAULT_VOICE, GEMINI_VOICES
    if not settings.debug_token.strip() or token.strip() != settings.debug_token.strip():
        raise HTTPException(403, "Ruxsat yo'q")
    opts = "".join(f'<option value="{pid}">{p.title}</option>' for pid, p in PATIENTS.items())
    return (PAGE.replace("__PATIENTS__", opts).replace("__VOICES__", json.dumps(GEMINI_VOICES))
            .replace("__DEF__", json.dumps(GEMINI_DEFAULT_VOICE)).replace("__EVD__", json.dumps(DEFAULT_VOICE_ELEVEN))
            .replace("__TP__", json.dumps({k: {"tempo": p.eleven_tempo, "stab": p.eleven_stability} for k, p in PATIENTS.items()})).replace("__EMD__", json.dumps(DEFAULT_MODEL_ELEVEN)).replace("__SP__", json.dumps({k: {"gemini": p.gemini_speed, "eleven": p.eleven_speed} for k, p in PATIENTS.items()})))
