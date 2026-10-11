// Synthetic DOM/media/network only. No browser, microphone, key or provider access.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('cloud/mobile.html','utf8').match(/<script nonce="__NONCE__">([\s\S]*?)<\/script>/)[1];
async function main(){
 const elements={},events={},calls=[],timers=new Map();let next=0,stopped=0,signed=0,spoken=[],live=true,rec=null;
 const el=id=>elements[id]??=( {hidden:id==='chat',disabled:false,checked:false,textContent:'',value:'',focus(){this.focused=true}} );
 const session={verified:true,expires_in:850,owner_verified:false,owner_expires_in:0,scope:'public_chat',voice_available:true};
 let delayedMic=null,delayTranscript=null;
 class Context {async resume(){} async close(){} async decodeAudioData(){return {duration:1}}}
 class Recorder {static isTypeSupported(){return true}constructor(){this.state='inactive';this.mimeType='audio/mp4';rec=this}start(){this.state='recording'}stop(){this.state='inactive';queueMicrotask(()=>{this.ondataavailable({data:new Blob(['fake'])});this.onstop()})}}
 const context=vm.createContext({document:{getElementById:el,body:{dataset:{}},hidden:false,addEventListener:(n,f)=>events[n]=f},
  location:{hash:'',pathname:'/'},history:{replaceState(){}},window:{isSecureContext:true,MediaRecorder:Recorder,AudioContext:Context,OfflineAudioContext:true,speechSynthesis:{speaking:false,cancel(){this.speaking=false},getVoices(){return []},speak(u){spoken.push(u.text);this.speaking=true;u.onstart?.()}}},
  navigator:{credentials:{async get(){signed++;return {id:'fake',rawId:new Uint8Array(1),response:{clientDataJSON:new Uint8Array(1),authenticatorData:new Uint8Array(1),signature:new Uint8Array(1)},getClientExtensionResults(){return {}}}}},mediaDevices:{async getUserMedia(){if(delayedMic)await delayedMic;return {getTracks:()=>[{stop:()=>stopped++}]}}}},
  AudioContext:Context,MediaRecorder:Recorder,OfflineAudioContext:class {createBufferSource(){return {connect(){},start(){}}}async startRendering(){return {getChannelData:()=>new Float32Array(16000)}}},
  SpeechSynthesisUtterance:class {constructor(text){this.text=text}},crypto:{randomUUID:()=> '12345678-1234-1234-1234-123456789abc'},
  AbortController,Uint8Array,Float32Array,ArrayBuffer,DataView,Blob,atob,btoa,queueMicrotask,
  setTimeout:(f,t)=>{timers.set(++next,{f,t});return next},clearTimeout:id=>timers.delete(id),
  fetch:async(path,options)=>{calls.push([path,options]);if(path==='/transcribe'&&delayTranscript)await delayTranscript;
   let body=path==='/session'?session:path==='/chat'?{text:'Synthetic spoken reply'}:path==='/transcribe'?{text:'A synthetic question'}:path==='/auth/begin'?{ticket:'fake',phase:'get',publicKey:{challenge:'YQ',allowCredentials:[]}}:{};
   return {ok:live||path!=='/session',json:async()=>body}}
 });context.window.navigator=context.navigator;context.speechSynthesis=context.window.speechSynthesis;
 vm.runInContext(source,context);const flush=async()=>{for(let i=0;i<15;i++)await new Promise(setImmediate)};await flush();
 assert.equal(el('chat').hidden,false);assert.equal(signed,0);assert.equal(el('talk').disabled,true);
 assert.ok([...timers.values()].some(x=>x.t===850000));
 assert.equal(vm.runInContext("ownerPhrase('LYA, owner mode')",context),true);
 assert.equal(vm.runInContext("ownerPhrase('do not verify owner')",context),false);
 const wav=vm.runInContext('wav(new Float32Array([-1,0,1]))',context),view=new DataView(wav);
 assert.equal(wav.byteLength,50);assert.equal(view.getUint32(24,true),16000);assert.equal(view.getInt16(44,true),-32768);assert.equal(view.getInt16(48,true),32767);
 el('text').value='LYA, owner mode';await el('composer').onsubmit({preventDefault(){}});
 assert.equal(signed,0);assert.ok(el('owner').focused);assert.equal(calls.filter(x=>x[0]==='/chat').length,0);
 await el('owner').onclick();assert.equal(signed,1);assert.equal(calls.find(x=>x[0]==='/auth/begin')[1].body,'{"mode":"owner"}');
 el('spoken').checked=true;el('text').value='A public question';await el('composer').onsubmit({preventDefault(){}});
 assert.equal(el('answer').textContent,'Synthetic spoken reply');assert.deepEqual(spoken,['Synthetic spoken reply']);await el('stop').onclick();assert.equal(context.speechSynthesis.speaking,false);
 el('consent').checked=true;el('consent').onchange();await el('talk').onclick();assert.equal(el('talk').textContent,'Finish');await el('talk').onclick();await flush();
 assert.ok(stopped>0);assert.equal(el('text').value,'A synthetic question');assert.equal(calls.filter(x=>x[0]==='/chat').length,1);assert.equal(calls.find(x=>x[0]==='/transcribe')[1].body.byteLength,32044);
 let release;delayedMic=new Promise(resolve=>release=resolve);const opening=el('talk').onclick();await flush();await el('stop').onclick();const before=stopped;release();await opening;await flush();assert.ok(stopped>before);assert.equal(el('talk').textContent,'Talk');delayedMic=null;
 let complete;delayTranscript=new Promise(resolve=>complete=resolve);await el('talk').onclick();await el('talk').onclick();await flush();await el('stop').onclick();el('text').value='';complete();await flush();assert.equal(el('text').value,'');assert.ok(calls.some(x=>x[0]==='/stop'));delayTranscript=null;
 await el('talk').onclick();context.document.hidden=true;events.visibilitychange();await flush();assert.equal(rec.state,'inactive');assert.equal(el('text').value,'');
 live=false;context.document.hidden=false;events.visibilitychange();await flush();assert.equal(el('chat').hidden,true);assert.equal(el('auth').hidden,false);
 assert.ok(!/localStorage|indexedDB|serviceWorker/.test(source));
 console.log(JSON.stringify({success:true,synthetic_client_checks:12,real_audio:false,provider_call:false}));
}
main().catch(e=>{console.error(e);process.exitCode=1});
