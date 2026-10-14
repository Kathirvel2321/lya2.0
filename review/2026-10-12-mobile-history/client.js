
'use strict';
let invite=location.hash.slice(1);history.replaceState(null,'',location.pathname);
const $=id=>document.getElementById(id),status=$('status');
function clearConversation(){$('recent').replaceChildren();$('question').textContent='';$('answer').textContent='';$('text').value='';$('chat').scrollTop=0}
function archiveExchange(){if(!$('question').textContent||!$('answer').textContent)return;
 const exchange=document.createElement('article');for(const [name,text] of [['question',$('question').textContent],['answer',$('answer').textContent]]){const line=document.createElement('p');line.className='earlier-'+name;line.textContent=text;exchange.append(line)}
 $('recent').append(exchange);while($('recent').children.length>11)$('recent').firstElementChild.remove()}
let pending=null,request=null,generation=0,sessionTimer=null,ownerTimer=null,requestId=null;
let available=false,stream=null,recorder=null,audioContext=null,recordTimer=null,vadTimer=null;
let conversation=false,opening=false,playerContext=null,playerSource=null,lastAudio=null,typing=false;
let resumeAfterTyping=false,backgroundResume=false,rearmTimer=null,authenticating=false;
const dec=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
const enc=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function state(value,message){document.body.dataset.state=value;if(message)status.textContent=message;controls()}
async function api(path,data,signal){const r=await fetch(path,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal});const body=await r.json();if(!r.ok){const e=Error(body.error||'Connection unavailable.');e.status=r.status;throw e}return body}
function silence(){if(playerSource){playerSource.onended=null;try{playerSource.stop()}catch(_){}playerSource.disconnect();playerSource=null}}
function stopCapture(){clearTimeout(rearmTimer);clearInterval(vadTimer);vadTimer=null;clearTimeout(recordTimer);stream?.getTracks().forEach(t=>t.stop());stream=null;if(recorder?.state==='recording')recorder.stop();recorder=null;if(audioContext&&audioContext!==playerContext)audioContext.close().catch(()=>{});audioContext=null;opening=false}
function controls(){const live=!$('auth').hidden; $('presence').disabled=live||!available||authenticating;
 $('presence').setAttribute('aria-label',conversation||request||playerSource?'Pause LYA conversation':'Resume LYA voice conversation');
 $('presence').setAttribute('aria-pressed',String(conversation));$('owner').disabled=authenticating;$('question').disabled=live||authenticating}
// Invalidate callbacks before releasing media; a cancelled permission prompt may finish late.
function cancelTurn(){const id=requestId;generation++;request?.abort();request=null;requestId=null;stopCapture();silence();lastAudio=null;
 if(id)api('/stop',{id}).catch(()=>{});return generation}
function locked(){conversation=false;typing=false;resumeAfterTyping=false;backgroundResume=false;authenticating=false;cancelTurn();playerContext?.close().catch(()=>{});playerContext=null;clearTimeout(sessionTimer);clearTimeout(ownerTimer);pending=null;available=false;
 $('auth').hidden=false;$('chat').hidden=true;$('session').hidden=true;$('composer').hidden=true;clearConversation();$('sign').disabled=false;$('sign').textContent=invite?'Pair with phone passkey':'Sign in with passkey';state('locked')}
function connected(s,auto=true){$('auth').hidden=true;$('chat').hidden=false;$('session').hidden=false;$('composer').hidden=false;
 available=s.voice_available&&!!navigator.mediaDevices?.getUserMedia&&!!window.MediaRecorder&&!!window.AudioContext&&!!window.OfflineAudioContext;
 $('identity').textContent=s.owner_verified?'Owner verified. Private actions still need separate approval.':'Public conversation. Private memory and device actions are not connected.';
 clearTimeout(sessionTimer);sessionTimer=setTimeout(()=>{locked();status.textContent='Session expired. Sign in again.'},s.expires_in*1000);
 clearTimeout(ownerTimer);if(s.owner_verified)ownerTimer=setTimeout(()=>{$('identity').textContent='Owner verification expired. Public conversation.'},s.owner_expires_in*1000);
 state('ready',available?'I’m here.':'Type below to talk with me. Voice is unavailable.');if(auto&&available&&!typing&&!document.hidden)beginConversation()}
async function restore(auto=true){if(invite)return;const turn=generation;try{const s=await api('/session',{});if(turn===generation)connected(s,auto)}catch(_){if(turn===generation){locked();status.textContent='Sign in to your private connection.'}}}
async function ensurePlayer(){if(!playerContext||playerContext.state==='closed')playerContext=new AudioContext();const current=playerContext;let timer;try{await Promise.race([current.resume(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Tap the crystal once to enable voice, or type below.')),1500)})]);if(current.state!=='running')throw Error('Tap the crystal once to enable voice, or type below.')}finally{clearTimeout(timer)}}
async function authenticate(mode){if(authenticating)return;conversation=false;cancelTurn();const turn=generation;authenticating=true;$('sign').disabled=true;controls();
 // Start audio inside the sign-in gesture, before waiting for the passkey/network.
 const audio=window.AudioContext?ensurePlayer().catch(()=>{}):Promise.resolve();
 try{if(!window.isSecureContext||!navigator.credentials)throw Error('Use your configured private HTTPS address.');
 const x=pending||await api('/auth/begin',mode==='owner'?{mode:'owner'}:invite?{mode:'pair',token:invite}:{mode:'login'});pending=null;if(turn!==generation)return;
 const o=x.publicKey;o.challenge=dec(o.challenge);if(o.user)o.user.id=dec(o.user.id);
 for(const k of ['allowCredentials','excludeCredentials'])if(o[k])o[k]=o[k].map(c=>({...c,id:dec(c.id)}));if(invite)o.hints=['hybrid'];status.textContent='Waiting for your passkey.';
 const c=x.phase==='create'?await navigator.credentials.create({publicKey:o}):await navigator.credentials.get({publicKey:o});if(turn!==generation||!c)return;
 const r=c.response,b={id:c.id,rawId:enc(c.rawId),type:c.type,response:{clientDataJSON:enc(r.clientDataJSON)},clientExtensionResults:c.getClientExtensionResults()};
 if(x.phase==='create')b.response.attestationObject=enc(r.attestationObject);else Object.assign(b.response,{authenticatorData:enc(r.authenticatorData),signature:enc(r.signature),userHandle:r.userHandle?enc(r.userHandle):null});
 const done=await api('/auth/complete',{ticket:x.ticket,response:b});if(turn!==generation)return;
 if(done.confirm){pending=done;$('sign').textContent='Verify the new passkey';status.textContent='Verify once more to finish pairing.';return}
 invite='';await audio;if(turn!==generation)return;const s=await api('/session',{});if(turn===generation){authenticating=false;$('session').open=false;connected(s)}
 }catch(e){if(turn===generation){pending=null;status.textContent=e.name==='NotAllowedError'?'Passkey cancelled. Try again.':e.message}}
 finally{if(turn===generation){authenticating=false;$('sign').disabled=false;controls()}}}
$('sign').onclick=()=>authenticate('login');$('owner').onclick=()=>authenticate('owner');
function ownerPhrase(text){return /^(?:(?:hey\s+)?(?:lya|liya|laya)[,\s]+)?(?:owner mode|verify owner)[.!?]*$/i.test(text.trim())}
function ownerRequest(){conversation=false;cancelTurn();$('session').open=true;state('paused','Tap Verify owner in Connection to confirm with your passkey.');$('owner').focus()}
function stopPhrase(text){return /^(?:(?:hey\s+)?(?:lya|liya|laya)[,\s]+)?(?:stop|cancel|stop listening|pause)[.!?]*$/i.test(text.trim())}
function pause(message='Paused. Tap the crystal when you want to talk.'){conversation=false;resumeAfterTyping=false;cancelTurn();state('paused',message)}
async function playReply(audio,turn){await ensurePlayer();if(turn!==generation)return;const decoded=await playerContext.decodeAudioData(dec(audio).buffer);if(turn!==generation)return;
 silence();const source=playerContext.createBufferSource();playerSource=source;source.buffer=decoded;source.connect(playerContext.destination);
 source.onended=()=>{if(playerSource!==source)return;playerSource=null;source.disconnect();lastAudio=null;if(turn===generation){state('ready');queueListen(turn)}};source.start();state('speaking','I’m with you.')}
function queueListen(turn=generation){if(turn!==generation||!conversation||typing||document.hidden||$('auth').hidden===false||request||playerSource||opening||recorder)return;
 clearTimeout(rearmTimer);rearmTimer=setTimeout(()=>{if(turn===generation)startCapture()},250)}
async function submitQuestion(text,spoken=conversation){text=text.trim();if(!text||text.length>4000||request||authenticating)return;
 if(ownerPhrase(text)){ownerRequest();return}if(stopPhrase(text)){pause();return}
 cancelTurn();const turn=generation,id=crypto.randomUUID().replaceAll('-','');requestId=id;request=new AbortController();archiveExchange();$('question').textContent=text;$('answer').textContent='';$('chat').scrollTop=$('chat').scrollHeight;state('thinking','Thinking…');
 try{const body=await api('/chat',{id,text,spoken},request.signal);if(turn!==generation)return;const follow=$('chat').scrollHeight-$('chat').scrollTop-$('chat').clientHeight<80;$('answer').textContent=body.text;if(follow)$('chat').scrollTop=$('chat').scrollHeight;lastAudio=spoken?(body.audio||null):null;
 if(lastAudio)await playReply(lastAudio,turn);else state('ready',spoken?'My reply is above. I’m listening.':'You can keep typing.');
 }catch(e){if(turn===generation){if(e.status===401||e.status===403){locked();status.textContent='Sign in again to continue.';return}
 conversation=false;state('paused',e.name==='AbortError'?'Paused.':lastAudio?'Tap the crystal to hear my reply.':e.message+' Type below or tap the crystal to retry.')}}
 finally{if(turn===generation){request=null;requestId=null;controls();if(!playerSource)queueListen(turn)}}}
function wav(samples){const buffer=new ArrayBuffer(44+samples.length*2),v=new DataView(buffer),word=(offset,s)=>{for(let i=0;i<s.length;i++)v.setUint8(offset+i,s.charCodeAt(i))};word(0,'RIFF');v.setUint32(4,36+samples.length*2,true);word(8,'WAVE');word(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);word(36,'data');v.setUint32(40,samples.length*2,true);for(let i=0;i<samples.length;i++){const x=Math.max(-1,Math.min(1,samples[i]));v.setInt16(44+i*2,x<0?x*32768:x*32767,true)}return buffer}
// Acoustic pauses indicate turn boundaries, not meaning or speaker identity.
class TurnEnd {constructor(now){this.last=now;this.noise=.001;this.speech=0;this.gap=0;this.active=false;this.previous=now}
 feed(level,now){const dt=Math.min(200,Math.max(0,now-this.previous));this.previous=now;const gate=Math.max(.003,this.noise*2.5);
 if(level>gate){if(this.active&&now-this.last<1600)this.gap=Math.max(this.gap,now-this.last);this.active=true;this.speech+=dt;this.last=now}
 else this.noise=Math.max(.0002,this.noise*.97+level*.03);
 const pause=Math.max(this.speech>8000?2800:1800,Math.min(3600,this.gap*1.6+400));return this.speech>=240&&now-this.last>=pause?'end':null}}
async function beginConversation(){if(request||opening||recorder||conversation||!available||document.hidden||authenticating)return;
 typing=false;$('text').blur();resumeAfterTyping=false;const turn=generation;
 try{await ensurePlayer();if(turn!==generation||document.hidden)return;conversation=true;controls();if(lastAudio)await playReply(lastAudio,turn);else await startCapture()}
 catch(e){if(turn===generation){conversation=false;state('paused',e.message)}}}
async function startCapture(){if(request||opening||recorder||playerSource||!conversation||typing||!available||document.hidden||authenticating)return;
 const turn=++generation;opening=true;state('listening','Listening. Take your time.');let context=null,mic=null;
 try{context=playerContext;audioContext=context;await context.resume();if(context.state!=='running')throw Error('Tap the crystal once to enable voice.');
 if(turn!==generation)return;mic=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});if(turn!==generation||document.hidden){mic.getTracks().forEach(t=>t.stop());return}stream=mic;
 const mime=['audio/mp4','audio/webm;codecs=opus','audio/webm'].find(m=>MediaRecorder.isTypeSupported(m));const rec=new MediaRecorder(mic,mime?{mimeType:mime}:{});recorder=rec;opening=false;
 let chunks=[],size=0,send=false,limitReached=false;const end=new TurnEnd(performance.now()),input=context.createMediaStreamSource(mic),analyser=context.createAnalyser();analyser.fftSize=2048;input.connect(analyser);const values=new Float32Array(analyser.fftSize);
 const finish=()=>{if(rec.state!=='recording')return;clearInterval(vadTimer);clearTimeout(recordTimer);rec.stop();mic.getTracks().forEach(t=>t.stop());stream=null};
 rec.ondataavailable=e=>{if(turn!==generation)return;size+=e.data.size;if(size>6000000){chunks=[];pause('Recording too large. Try a shorter question or type below.');return}chunks.push(e.data)};
 rec.onerror=()=>{if(turn===generation)pause('Microphone interrupted. Tap the crystal to retry, or type below.')};
 rec.onstop=async()=>{input.disconnect();analyser.disconnect();mic.getTracks().forEach(t=>t.stop());if(turn!==generation){chunks=[];return}clearTimeout(recordTimer);clearInterval(vadTimer);vadTimer=null;recorder=null;stream=null;audioContext=null;
 if(!send){chunks=[];state('ready',limitReached?'That question was too long. Try a shorter one.':'Listening. Take your time.');queueListen(turn);return}
 state('thinking','I heard you…');let recognized=null;
 try{const blob=new Blob(chunks,{type:rec.mimeType});chunks=[];const decoded=await context.decodeAudioData(await blob.arrayBuffer());if(turn!==generation)return;
 if(decoded.duration<.1||decoded.duration>120.5)throw Error('Question exceeds the recording limit.');const frames=Math.min(120*16000,Math.floor(decoded.duration*16000));const offline=new OfflineAudioContext(1,frames,16000),source=offline.createBufferSource();source.buffer=decoded;source.connect(offline.destination);source.start();const pcm=await offline.startRendering();if(turn!==generation)return;
 const id=crypto.randomUUID().replaceAll('-','');requestId=id;request=new AbortController();const r=await fetch('/transcribe',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'audio/wav','X-LYA-Request':id},body:wav(pcm.getChannelData(0)),signal:request.signal});const body=await r.json();if(turn!==generation)return;
 if(!r.ok){const e=Error(body.error||'Phone hearing unavailable.');e.status=r.status;throw e}recognized=typeof body.text==='string'?body.text.trim():'';
 }catch(e){if(turn===generation){if(e.status===401||e.status===403){locked();status.textContent='Sign in again to continue.'}else{conversation=false;state('paused',e.message+' Type below or tap the crystal to retry.')}}}
 finally{if(turn===generation){request=null;requestId=null;controls();if(recognized&&conversation){if(stopPhrase(recognized))pause();else submitQuestion(recognized,true)}else if(conversation){state('ready','I didn’t catch that. I’m listening.');queueListen(turn)}}}};
 rec.start(250);state('listening','Listening. Take your time.');vadTimer=setInterval(()=>{if(turn!==generation)return;analyser.getFloatTimeDomainData(values);let sum=0;for(const v of values)sum+=v*v;if(end.feed(Math.sqrt(sum/values.length),performance.now())==='end'){send=true;finish()}},80);
 // Rotate bounded recordings without sending silence or losing voice mode.
 recordTimer=setTimeout(()=>{if(turn===generation){limitReached=end.active;finish()}},120000);
 }catch(e){if(turn===generation){conversation=false;stopCapture();state('paused',e.name==='NotAllowedError'?'Allow microphone access in Safari, then tap the crystal. You can type below.':e.message+' Type below or tap the crystal to retry.')}}}
$('presence').onclick=()=>{if(conversation||request||playerSource){pause();return}beginConversation()};
$('question').onclick=()=>{if(!$('auth').hidden||authenticating||!$('question').textContent)return;conversation=false;resumeAfterTyping=false;cancelTurn();typing=true;$('text').value=$('question').textContent;$('text').focus();state('typing','Correct your question. Press return to resend.')};
$('text').onfocus=()=>{if(typing)return;resumeAfterTyping=conversation;typing=true;conversation=false;cancelTurn();state('typing','Type naturally. Press return to send.')};
$('text').onblur=()=>{typing=false;if(resumeAfterTyping&&!$('text').value.trim()){resumeAfterTyping=false;conversation=true;queueListen()}};
$('composer').onsubmit=e=>{e.preventDefault();const text=$('text').value.trim();if(!text||text.length>4000)return;$('text').value='';submitQuestion(text,false)};
$('text').onkeydown=e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();$('composer').onsubmit(e)}};
$('lock').onclick=()=>{const done=api('/logout',{});locked();done.catch(()=>{});status.textContent='Locked.'};
document.addEventListener('visibilitychange',()=>{if(document.hidden){backgroundResume=conversation||resumeAfterTyping;conversation=false;cancelTurn();authenticating=false;pending=null;$('sign').disabled=false;playerContext?.close().catch(()=>{});playerContext=null;typing=false;resumeAfterTyping=false;$('text').blur();clearConversation();state($('auth').hidden?'paused':'locked','Paused while you’re away.')}else if(!authenticating&&!pending){const auto=backgroundResume;backgroundResume=false;restore(auto)}});
window.addEventListener('pagehide',()=>{backgroundResume=conversation||resumeAfterTyping;conversation=false;cancelTurn();authenticating=false;pending=null;$('sign').disabled=false;playerContext?.close().catch(()=>{});playerContext=null;clearConversation()});
window.addEventListener('pageshow',e=>{if(e.persisted){const auto=backgroundResume;backgroundResume=false;restore(auto)}});
locked();restore();
