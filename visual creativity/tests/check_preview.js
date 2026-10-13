/* Synthetic DOM/canvas scheduling only; not browser visual QA. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'preview.html'),'utf8'),scripts=[...html.matchAll(/<script nonce="lya-design">([\s\S]*?)<\/script>/g)].map(m=>m[1]);assert.equal(scripts.length,2);
const ids={},events={},raf=new Map(),draws=[];let next=0,now=0,observer;
const defaults={interaction:'listening',task:'none',energy:'.4',appearance:'navy',mode:'reference',angle:'0'};
function element(id){return ids[id]??={value:defaults[id]||'',checked:['effects'].includes(id),hidden:id==='rotate-controls',textContent:'',style:{},listeners:{},classList:{toggle(){}},append(o){if(!this.value)this.value=o.value},setAttribute(){},addEventListener(n,f){(this.listeners[n]??=[]).push(f)},fire(n){for(const f of this.listeners[n]||[])f({})}}}
const noop=()=>{},ctx={save:noop,restore:noop,setTransform:noop,clearRect:noop,translate:noop,setLineDash:noop,beginPath:noop,arc:noop,fill:noop,moveTo:noop,lineTo:noop,stroke:noop,closePath:noop,drawImage:(...args)=>draws.push(args.slice(1))};
const canvas=element('view');canvas.getContext=()=>ctx;canvas.getBoundingClientRect=()=>({width:500,height:600});
const document={hidden:false,getElementById:element,createElement:()=>({}),addEventListener:(n,f)=>events[n]=f};
const pref={matches:false,addEventListener:noop},context=vm.createContext({document,window:{addEventListener:(n,f)=>events[n]=f},devicePixelRatio:3,matchMedia:()=>pref,performance:{now:()=>now},Image:class{constructor(){this.width=1199;this.height=1312}set src(v){assert.ok(v.startsWith('data:image/png;base64,'));this.onload()}},ResizeObserver:class{constructor(f){observer=f}observe(){observer()}},requestAnimationFrame:f=>{raf.set(++next,f);return next},cancelAnimationFrame:i=>raf.delete(i),console});
for(const s of scripts)vm.runInContext(s,context);
let checked=0;
const input=(id,value)=>{element(id).value=value;element(id).fire('input')};
const frame=()=>{now+=40;const copy=[...raf];raf.clear();for(const [,f] of copy)f(now)};
assert.equal(canvas.width,1000);assert.equal(canvas.height,1200);checked++;
assert.equal(raf.size,1);frame();assert.equal(raf.size,1);checked++;
const first=JSON.stringify(draws.at(-1));
for(const phase of ['idle','standby','speaking','paused','voice_off','offline','uncertain']){input('interaction',phase);assert.equal(JSON.stringify(draws.at(-1)),first);if(['idle','standby','paused','voice_off','offline','uncertain'].includes(phase))assert.equal(raf.size,0)}checked++;
input('task','coding');assert.equal(element('interaction').value,'idle');assert.match(element('status').textContent,/Coding/);assert.equal(raf.size,1);checked++;
input('interaction','speaking');assert.equal(context.LyaEffects.resolve(JSON.parse(fs.readFileSync(path.join(root,'states.json'))),'speaking','coding').effect,'waves');checked++;
element('motion').checked=true;element('motion').fire('input');assert.equal(raf.size,0);checked++;
element('motion').checked=false;element('motion').fire('input');assert.equal(raf.size,1);document.hidden=true;events.visibilitychange();assert.equal(raf.size,0);document.hidden=false;events.visibilitychange();assert.equal(raf.size,1);checked++;
input('task','approval');assert.equal(raf.size,0);assert.match(element('status').textContent,/approval/);checked++;
input('mode','geometry');assert.equal(element('rotate-controls').hidden,false);element('spin').checked=true;element('spin').fire('input');assert.equal(raf.size,1);frame();checked++;
element('motion').checked=true;element('motion').fire('input');assert.equal(raf.size,0);checked++;
element('reset').fire('click');assert.equal(element('mode').value,'reference');assert.equal(element('task').value,'none');assert.equal(element('interaction').value,'listening');assert.equal(element('rotate-controls').hidden,true);checked++;
events.pagehide();assert.equal(raf.size,0);events.pageshow();assert.equal(raf.size,1);checked++;
assert.ok(!/fetch\(|getUserMedia|localStorage|indexedDB|serviceWorker|https?:\/\//.test(scripts.join('\n')));assert.ok(html.includes("connect-src 'none'"));checked++;
const result={success:true,synthetic_preview_checks:checked,real_browser:false,real_audio:false,network_calls:false};fs.writeFileSync(path.join(root,'tests/preview-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
