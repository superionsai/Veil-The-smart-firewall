const $ = (id) => document.getElementById(id);
const state = { presets: {}, customPolicy: null, captureStream: null, ws: null, busy: false, pendingBitmap: null, timer: null, policyId: 'external' };
const titles = {
  live: ['Live Shield', 'Share a protected Veil preview instead of your raw application window.'],
  files: ['File Sanitizer', 'Burn privacy masks into screenshots, images and PDFs before sharing.'],
  paste: ['Quick Paste', 'Remove secrets and semantic-sensitive text before copying it elsewhere.'],
  policy: ['Policy Studio', 'Compile plain-English privacy intent into inspectable local rules.'],
  diagnostics: ['Diagnostics', 'Prove what is local, what was skipped and where inference time is spent.']
};

function toast(message, error=false){ const el=$('toast'); el.textContent=message; el.className='toast show'+(error?' error':''); clearTimeout(el._t); el._t=setTimeout(()=>el.className='toast',2600); }
function currentPolicy(){ return state.customPolicy && $('globalPolicy').value==='custom' ? state.customPolicy : state.presets[$('globalPolicy').value] || state.presets.external; }
function esc(s){ return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function init(){
  const [cfg, health] = await Promise.all([fetch('/api/config').then(r=>r.json()), fetch('/api/health').then(r=>r.json())]);
  cfg.presets.forEach(p=>state.presets[p.id]=p);
  fillPolicySelects();
  updateHealth(health);
  bindNavigation(); bindLive(); bindFiles(); bindPaste(); bindPolicy(); bindDiagnostics();
  refreshDiagnostics();
}

function fillPolicySelects(){
  const opts=Object.values(state.presets).map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
  $('globalPolicy').innerHTML=opts; $('globalPolicy').value='external'; $('policyBase').innerHTML=opts; $('policyBase').value='external';
  $('globalPolicy').addEventListener('change',()=>{ state.policyId=$('globalPolicy').value; sendPolicyToLive(); });
}
function ensureCustomOption(){ if(!$('globalPolicy').querySelector('option[value="custom"]')) $('globalPolicy').insertAdjacentHTML('beforeend','<option value="custom">Custom Policy</option>'); }
function updateHealth(h){
  const sem=h.semantic||{}; const local=sem.name?.startsWith('geniex');
  $('localStatus').textContent = local ? `GenieX local · ${sem.name}` : `Local fallback · ${sem.name||'heuristic'}`;
  $('diagSemantic').textContent=sem.name||'—'; $('diagModel').textContent=sem.model||'No generative model loaded'; $('diagOcr').textContent=h.ocr?.name||'—';
  $('environmentDump').textContent=JSON.stringify(h,null,2);
}
function bindNavigation(){ document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>{ document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active')); btn.classList.add('active'); document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active')); const tab=btn.dataset.tab; $(`tab-${tab}`).classList.add('active'); $('pageTitle').textContent=titles[tab][0]; $('pageSubtitle').textContent=titles[tab][1]; if(tab==='diagnostics') refreshDiagnostics(); })); }

function bindLive(){ $('startCapture').onclick=startCapture; $('stopCapture').onclick=stopCapture; }
async function startCapture(){
  try{
    const stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:4,max:8}},audio:false,preferCurrentTab:false});
    state.captureStream=stream; $('sourceVideo').srcObject=stream; await $('sourceVideo').play();
    stream.getVideoTracks()[0].addEventListener('ended', stopCapture);
    $('emptyPreview').classList.add('hidden'); $('startCapture').disabled=true; $('stopCapture').disabled=false;
    connectLiveSocket();
  }catch(e){ toast(e.message||'Capture cancelled',true); }
}
function connectLiveSocket(){
  const proto=location.protocol==='https:'?'wss':'ws';
  state.ws=new WebSocket(`${proto}://${location.host}/ws/live?policy=${encodeURIComponent($('globalPolicy').value==='custom'?'external':$('globalPolicy').value)}`);
  state.ws.onopen=()=>sendPolicyToLive();
  state.ws.onmessage=async(ev)=>{
    const msg=JSON.parse(ev.data);
    if(msg.type==='ready'){ scheduleCapture(80); return; }
    if(msg.type==='frame'){ try{ await renderProtectedFrame(msg); }catch(e){ toast(e.message||'Protected render failed',true); }finally{ state.busy=false; scheduleCapture(50); } }
    if(msg.type==='error'){ state.busy=false; toast(msg.message,true); scheduleCapture(500); }
  };
  state.ws.onclose=()=>{state.busy=false;};
}
function sendPolicyToLive(){ if(state.ws?.readyState===WebSocket.OPEN){ const p=currentPolicy(); state.ws.send(JSON.stringify({type:'policy',policy:p})); } }
function scheduleCapture(delay){ clearTimeout(state.timer); if(state.captureStream) state.timer=setTimeout(captureAndSend,delay); }
async function captureAndSend(){
  if(!state.captureStream || state.busy || !state.ws || state.ws.readyState!==WebSocket.OPEN){ scheduleCapture(150); return; }
  const v=$('sourceVideo'); if(!v.videoWidth){ scheduleCapture(150); return; }
  const temp=document.createElement('canvas'); temp.width=v.videoWidth; temp.height=v.videoHeight; temp.getContext('2d',{alpha:false}).drawImage(v,0,0);
  const blob=await new Promise(res=>temp.toBlob(res,'image/jpeg',0.82)); if(!blob){ scheduleCapture(200); return; }
  if(state.pendingBitmap) try{state.pendingBitmap.close();}catch{}
  state.pendingBitmap=await createImageBitmap(blob); state.busy=true; state.ws.send(await blob.arrayBuffer());
}
async function browserQrRegions(bitmap){
  const policy=currentPolicy();
  const action=policy?.actions?.QR_CODE||'ALLOW';
  if(!policy?.mask_qr || action==='ALLOW' || !('BarcodeDetector' in window)) return [];
  try{
    const detector=new BarcodeDetector({formats:['qr_code']});
    const codes=await detector.detect(bitmap);
    return codes.map(code=>{
      const b=code.boundingBox;
      return {
        category:'QR_CODE', confidence:0.99, action,
        source:'browser:BarcodeDetector',
        reason:'QR code may encode private data or authentication material',
        box:{x:b.x/bitmap.width,y:b.y/bitmap.height,w:b.width/bitmap.width,h:b.height/bitmap.height}
      };
    });
  }catch(_e){ return []; }
}

async function renderProtectedFrame(msg){
  const bitmap=state.pendingBitmap; if(!bitmap) return;
  // QR detection happens against the held ImageBitmap before any raw pixels are
  // painted into the visible protected canvas. This preserves fail-closed output.
  const localQr=await browserQrRegions(bitmap);
  const canvas=$('protectedCanvas'), ctx=canvas.getContext('2d');
  canvas.width=bitmap.width; canvas.height=bitmap.height; ctx.filter='none'; ctx.drawImage(bitmap,0,0);
  const regs=[...(msg.regions||[]), ...localQr];
  regs.forEach(r=>{
    const b=r.box, x=b.x*canvas.width, y=b.y*canvas.height, w=b.w*canvas.width, h=b.h*canvas.height;
    if(r.action==='ALLOW') return;
    if(r.action==='WARN'){ ctx.strokeStyle='#ffbe55';ctx.lineWidth=Math.max(2,canvas.width/600);ctx.strokeRect(x,y,w,h);return; }
    if(r.action==='BLUR'){
      ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.filter='blur(16px)';ctx.drawImage(bitmap,x,y,w,h,x,y,w,h);ctx.restore();ctx.filter='none';
    }else{
      ctx.fillStyle='#101216';ctx.fillRect(x,y,w,h); if(w>80&&h>18){ctx.fillStyle='#e8edf1';ctx.font=`${Math.max(10,canvas.width/100)}px system-ui`;ctx.fillText(`[${r.category.replaceAll('_',' ')}]`,x+5,y+Math.min(h-4,16));}
    }
  });
  $('liveRegions').textContent=regs.filter(r=>r.action!=='WARN'&&r.action!=='ALLOW').length; $('liveLatency').textContent=Math.round(msg.metrics?.total_ms||0); $('liveChanged').textContent=`${Math.round((msg.metrics?.changed_fraction||0)*100)}%`;
  renderRegionList($('regionList'),regs);
  try{bitmap.close();}catch{} state.pendingBitmap=null;
}
function stopCapture(){ clearTimeout(state.timer); state.captureStream?.getTracks().forEach(t=>t.stop()); state.captureStream=null; state.ws?.close(); state.ws=null; state.busy=false; if(state.pendingBitmap)try{state.pendingBitmap.close();}catch{} state.pendingBitmap=null; $('startCapture').disabled=false; $('stopCapture').disabled=true; $('emptyPreview').classList.remove('hidden'); const c=$('protectedCanvas'); c.getContext('2d').clearRect(0,0,c.width,c.height); }

function renderRegionList(target, regs){ if(!regs?.length){target.innerHTML='<div class="muted-box">No privacy risks detected in the current output.</div>';return;} target.innerHTML=regs.slice(0,40).map(r=>`<div class="region-item"><div class="region-top"><span class="category">${esc(r.category)}</span><span class="confidence">${Math.round((r.confidence||0)*100)}% · ${esc(r.action)}</span></div><p>${esc(r.reason||'Detected privacy-sensitive region')}</p><div class="source">${esc(r.source)}</div></div>`).join(''); }

function bindFiles(){
  $('fileInput').onchange=()=>{ $('sanitizeFile').disabled=!$('fileInput').files.length; if($('fileInput').files[0]) $('fileProgress').textContent=`Selected: ${$('fileInput').files[0].name}`; };
  ['dragenter','dragover'].forEach(e=>$('dropzone').addEventListener(e,ev=>{ev.preventDefault();$('dropzone').style.borderColor='#8cf5c8';}));
  ['dragleave','drop'].forEach(e=>$('dropzone').addEventListener(e,ev=>{ev.preventDefault();$('dropzone').style.borderColor='';}));
  $('dropzone').addEventListener('drop',ev=>{const f=ev.dataTransfer.files?.[0]; if(f){ const dt=new DataTransfer();dt.items.add(f);$('fileInput').files=dt.files;$('sanitizeFile').disabled=false;$('fileProgress').textContent=`Selected: ${f.name}`; }});
  $('sanitizeFile').onclick=sanitizeFile;
}
async function sanitizeFile(){
  const file=$('fileInput').files[0]; if(!file)return; $('sanitizeFile').disabled=true;$('fileProgress').textContent='Processing locally…';
  const fd=new FormData();fd.append('file',file);const p=currentPolicy();fd.append('policy',p?.id?.startsWith('custom')?'external':p.id); if($('globalPolicy').value==='custom')fd.append('policy_json',JSON.stringify(p));
  try{const r=await fetch('/api/sanitize/file',{method:'POST',body:fd});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Failed'); $('fileSummary').textContent=`${data.count} privacy region${data.count===1?'':'s'} found.`; $('downloadFile').href=data.download_url;$('downloadFile').classList.remove('hidden');$('downloadFile').download=data.output_name; $('filePreview').innerHTML=(data.preview_url||data.preview_data_url)?`<img src="${data.preview_url||data.preview_data_url}" alt="Protected preview">`:`<div class="empty-state compact"><div class="shield">✓</div><h3>Protected PDF ready</h3><p>${esc(data.note||'Download the sanitized copy.')}</p></div>`; renderRegionList($('fileDetections'),data.detections||[]);$('fileProgress').textContent='Done. Original upload was processed in memory.';toast('Protected copy generated');}catch(e){toast(e.message,true);$('fileProgress').textContent='';}finally{$('sanitizeFile').disabled=false;}
}

function bindPaste(){ $('sanitizeText').onclick=sanitizeText; $('copySafe').onclick=async()=>{await navigator.clipboard.writeText($('pasteOutput').value);toast('Protected text copied');}; }
async function sanitizeText(){ const text=$('pasteInput').value;if(!text.trim()){toast('Paste some text first',true);return;} const p=currentPolicy(); const body={text,policy:p?.id?.startsWith('custom')?'external':p.id,custom_policy:$('globalPolicy').value==='custom'?p:null}; const r=await fetch('/api/sanitize/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();if(!r.ok){toast(data.detail||'Failed',true);return;}$('pasteOutput').value=data.sanitized_text;$('pasteDetections').innerHTML=(data.detections||[]).map(d=>`<span class="tag">${esc(d.category)} · ${esc(d.source)}</span>`).join('')||'<span class="tag">No risks found</span>'; }

function bindPolicy(){ $('compilePolicy').onclick=compilePolicy; $('clearCustomPolicy').onclick=()=>{state.customPolicy=null;$('globalPolicy').value='external';$('compiledPolicy').textContent='Custom policy cleared.';sendPolicyToLive();}; }
async function compilePolicy(){ const text=$('policyText').value.trim();if(!text)return; $('compilePolicy').disabled=true;try{const r=await fetch('/api/policy/compile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,base_policy:$('policyBase').value})});const data=await r.json();if(!r.ok)throw new Error(data.detail||'Compile failed');state.customPolicy=data;ensureCustomOption();$('globalPolicy').value='custom';$('compiledPolicy').textContent=JSON.stringify(data,null,2);sendPolicyToLive();toast('Custom policy active');}catch(e){toast(e.message,true);}finally{$('compilePolicy').disabled=false;} }

function bindDiagnostics(){ $('refreshDiag').onclick=refreshDiagnostics;$('clearAudit').onclick=async()=>{await fetch('/api/audit',{method:'DELETE'});refreshDiagnostics();toast('Audit log cleared');}; }
async function refreshDiagnostics(){
  try{const [h,m,a]=await Promise.all([fetch('/api/health').then(r=>r.json()),fetch('/api/metrics').then(r=>r.json()),fetch('/api/audit/recent?limit=30').then(r=>r.json())]);updateHealth(h);$('diagLatency').textContent=m.runtime.frames?`${m.runtime.avg_total_ms} ms`:'—';$('diagSkip').textContent=m.runtime.frames?`${Math.round(m.runtime.skip_rate*100)}%`:'—';$('diagEvents').textContent=m.audit.events??0;$('diagCalls').textContent=m.semantic.provider_calls??0; const events=a.events||[];$('auditList').innerHTML=events.length?events.map(e=>`<div class="region-item"><div class="region-top"><span class="category">${esc(e.category)}</span><span class="confidence">${new Date(e.ts*1000).toLocaleTimeString()}</span></div><p>${esc(e.action)} · ${esc(e.source)}</p><div class="source">hash ${esc((e.text_hash||'visual').slice(0,16))}…</div></div>`).join(''):'<div class="muted-box">No audit events yet.</div>';}catch(e){console.error(e);}
}

init().catch(e=>{console.error(e);toast(`Startup failed: ${e.message}`,true);});
