/* Local documentation renderer. Does not load LYA or any runtime/private store. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { chromium } = require('C:/Users/kathirvel/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const here = __dirname;
const renderer = process.env.LYA_MERMAID_RENDERER || path.join(process.env.TEMP, 'lya-architecture-mermaid-11.12.0.min.js');
const diagrams = [
  ['01-whole-system','Whole system','Ten responsibility areas, one logical assistant. Target integrations are proposed, even when they connect existing components.'],
  ['02-answer-sequence','Answer flow','The path from identity and recall to an eligible model, supported answer and cancellation. Streaming is a proposal to qualify.'],
  ['03-memory-lifecycle','Memory lifecycle','An explicit save becomes a committed revision. Derived indexes lag safely; forgetting must reach caches, objects and recovery.'],
  ['04-data-model','Data schema','Conceptual records and relationships. Scope constraints and indexes are described in the architecture contract; this is not migration SQL.'],
  ['05-platform-trust','Platforms & trust','Which machine processes each class of information. Shared personal records require trust in the Oracle service and host.'],
  ['06-recovery','Recovery','A backup is useful only with recoverable keys and a tested restore. Missing deletion history blocks automatic recovery.'],
  ['07-model-routing','Model routing','Use direct answers where possible. Personal context cannot fall back to public inference. Every new model must pass evaluation.'],
  ['08-fast-workflow','Fast workflow','Proposed short reply path, atomic writes and independent background exports. Optional LAYA and Jev experiments are evaluated in the final roadmap.']
];
function estimate(records, kib, dimensions, generations) {
  if (![records,kib,dimensions,generations].every(Number.isFinite) || records < 0 || kib <= 0 || dimensions < 0 || generations < 1) throw Error('Invalid capacity inputs');
  const bytesPerRecord = kib * 1024 * 2 + dimensions * 4 * 2;
  return { bytesPerRecord, primaryGiB: records * bytesPerRecord / 2**30,
    backupGiB: records * bytesPerRecord * generations / 2**30,
    recordsIn20GiB: Math.floor(20 * 2**30 / bytesPerRecord) };
}
assert.equal(estimate(100000,8,384,11).bytesPerRecord,19456);
assert.equal(estimate(0,8,384,11).primaryGiB,0);
assert.equal(estimate(100000,8,0,1).primaryGiB,100000*16384/2**30);
assert.throws(() => estimate(-1,8,384,11));
assert.throws(() => estimate(1,8,384,0));
const esc = s => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
async function main() {
  const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1500,height:1100},deviceScaleFactor:1});
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    const errors=[];
    page.on('pageerror', err => errors.push(err.message));
    await page.setContent('<html><body style="margin:0;background:#0b1322"></body></html>');
    await page.addScriptTag({path:renderer});
    await page.evaluate(() => mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',
      themeVariables:{fontFamily:'Arial',fontSize:'15px',primaryColor:'#243c65',primaryTextColor:'#eaf1ff',primaryBorderColor:'#6ca4ff',lineColor:'#91a5c4',secondaryColor:'#142338',tertiaryColor:'#142338',clusterBkg:'#101e31',clusterBorder:'#355171',titleColor:'#eaf1ff',edgeLabelBackground:'#162840',textColor:'#eaf1ff'},
      flowchart:{htmlLabels:false,curve:'basis',nodeSpacing:28,rankSpacing:48,useMaxWidth:false},
      sequence:{useMaxWidth:false},er:{useMaxWidth:false}}));
    const rendered=[];
    for (const [id,title,description] of diagrams) {
      const source=fs.readFileSync(path.join(here,id+'.mmd'),'utf8');
      const svg=await page.evaluate(async ({id,source}) => (await mermaid.render('d'+id.replaceAll('-',''),source)).svg,{id,source});
      assert(svg.includes('<svg') && !svg.includes('Syntax error'),'Mermaid rendering failed');
      fs.writeFileSync(path.join(here,id+'.svg'),svg);
      const viewBox=svg.match(/viewBox="([^"]+)"/)[1].split(/\s+/).map(Number);
      assert(viewBox[2]>0 && viewBox[3]>0);
      rendered.push({id,title,description,svg,width:viewBox[2],height:viewBox[3]});
    }
    const dataJSON=JSON.stringify(rendered).replaceAll('<','\\u003c');
    const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LYA architecture atlas</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080f1c;color:#edf3ff;font:15px/1.6 Arial,sans-serif}main{max-width:1560px;margin:auto;padding:38px 42px 60px}a{color:#9bc7ff}button,input{font:inherit}button{cursor:pointer;border:1px solid #334969;color:#d7e5fa;background:#122138;border-radius:8px;padding:9px 15px}button:hover,button[aria-pressed=true]{background:#264d7a;border-color:#7abaff}button:focus-visible,input:focus-visible,a:focus-visible{outline:3px solid #f2bf5d;outline-offset:3px}.eyebrow{color:#82baff;font-weight:bold;letter-spacing:2px;font-size:12px}h1{font-size:38px;line-height:1.2;margin:12px 0}h2{font-size:23px;margin:0 0 8px}p{max-width:1000px;color:#b7c6dd;margin:8px 0 18px}.pill{display:inline-block;background:#4b3515;color:#ffcf7e;border-radius:30px;padding:4px 12px;font-size:12px}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}.stat,.capacity{border:1px solid #263d5a;background:#101c2e;border-radius:12px;padding:18px}.stat strong{display:block;font-size:24px}.stat span{font-size:12px;color:#a0b3cd}.tabs{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}.tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}.legend{margin-left:auto;font-size:12px;color:#b7c6dd}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 5px 0 12px}.viewport{height:680px;border:1px solid #304765;border-radius:12px;overflow:auto;background:#0b1322;padding:22px}.viewport svg{display:block;max-width:none!important}.detail{min-height:50px}.capacity{margin-top:30px}.inputs{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.inputs label{display:block;font-size:13px;color:#b7c6dd}input{width:100%;color:#eef5ff;background:#081321;border:1px solid #385477;padding:9px;border-radius:6px;margin-top:5px}.results{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:20px 0 5px}.results strong{font-size:27px;display:block;color:#9dccff}.results span{color:#b7c6dd;font-size:13px}.note{font-size:12px;max-width:1200px}.links{display:flex;flex-wrap:wrap;gap:20px;margin:22px 0}footer{border-top:1px solid #233b58;margin-top:28px;padding-top:18px;color:#8ca2c0;font-size:12px}@media(max-width:700px){main{padding:24px 16px}.summary,.inputs,.results{grid-template-columns:repeat(2,1fr)}h1{font-size:29px}.viewport{height:530px}.legend{margin-left:0}}
</style><main>
<div class="eyebrow">LYA / SYSTEM ARCHITECTURE / 11 OCT 2026</div><h1>One assistant. A system built to remember.</h1><p>Explore the full brain, storage, platforms, model routing and recovery design. The diagrams describe the proposed destination and the components we retain.</p><span class="pill">Research and design prototype · no runtime migration</span>
<div class="summary"><div class="stat"><strong>8 views</strong><span>System, flow, schema, trust and recovery</span></div><div class="stat"><strong>23.41 GiB</strong><span>Observed Oracle RAM · billing unverified</span></div><div class="stat"><strong>1.81 GiB</strong><span>Illustrative 100k-record primary storage</span></div><div class="stat"><strong>1 authority</strong><span>Shared memories · separate local private vault</span></div></div>
<nav class="links" aria-label="Detailed documents"><a href="FINAL-ROADMAP.md">Final platform & build order</a><a href="PLATFORM-STORAGE.md">Storage platforms</a><a href="RESEARCH.md">Research & decisions</a><a href="ARCHITECTURE.md">Full contract</a><a href="CAPACITY.md">Capacity & targets</a><a href="IMPLEMENTATION.md">Implementation gates</a></nav>
<nav class="tabs" id="tabs" aria-label="Architecture views">${diagrams.map((d,i)=>`<button type="button" data-view="${i}" aria-pressed="${i===0}">${esc(d[1])}</button>`).join('')}</nav>
<h2 id="title"></h2><p id="description" class="detail"></p>
<div class="tools"><button type="button" id="fit">Fit whole diagram</button><button type="button" id="readable">Readable size</button><button type="button" id="minus" aria-label="Zoom out">−</button><button type="button" id="plus" aria-label="Zoom in">+</button><output id="zoom" aria-live="polite"></output><a id="svgLink">Open SVG</a><span class="legend"><i class="dot" style="background:#38b997"></i>Existing<i class="dot" style="background:#6ca4ff"></i>Proposed<i class="dot" style="background:#e8b558"></i>Qualification gate</span></div>
<div class="viewport" id="viewport" tabindex="0" aria-label="Scrollable architecture diagram"><div id="diagram"></div></div>
<section class="capacity"><h2>How much can we remember?</h2><p>Change the assumptions. These are storage estimates, not measured database speed or guaranteed capacity.</p>
<div class="inputs"><label>Selected records<input id="records" type="number" min="0" max="100000000" step="10000" value="100000"></label><label>Average record + metadata (KiB)<input id="kib" type="number" min="0.1" max="1024" step="0.1" value="8"></label><label>Vector dimensions (0 = none)<input id="dims" type="number" min="0" max="16000" step="1" value="384"></label><label>Full backup generations<input id="generations" type="number" min="1" max="100" step="1" value="11"></label></div>
<div class="results" aria-live="polite"><div><strong id="primary"></strong><span>Primary including index allowance</span></div><div><strong id="backups"></strong><span>Conservative independent backup space</span></div><div><strong id="count"></strong><span>Records within illustrative 20 GiB DB budget</span></div></div>
<p class="note" id="calcNote">Assumes 2× text/metadata and 2× raw float32 vector bytes for index/layout allowance. Excludes attachments, models, WAL, logs, temporary work and backup staging. Real index/history overhead can be higher. Compression and deduplication are not assumed.</p></section>
<footer>Oracle personal-memory placement is still pending. Existing private laptop data stays local. No new database/model was installed. Read the linked contract for authorization, deletion and failure behavior.</footer></main>
<script>
const diagrams=${dataJSON};
const estimate=${estimate.toString()};
let selected=0,scale=1;
const $=id=>document.getElementById(id);
function zoom(value){scale=Math.min(2.5,Math.max(.05,value));const d=diagrams[selected];const svg=$('diagram').querySelector('svg');svg.style.width=(d.width*scale)+'px';svg.style.height=(d.height*scale)+'px';$('zoom').textContent=Math.round(scale*100)+'%';}
function fit(){const d=diagrams[selected];zoom(Math.min(($('viewport').clientWidth-50)/d.width,($('viewport').clientHeight-50)/d.height));}
function show(index){selected=index;const d=diagrams[index];$('title').textContent=d.title;$('description').textContent=d.description;$('diagram').innerHTML=d.svg;$('svgLink').href=d.id+'.svg';document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',Number(b.dataset.view)===index));fit();$('viewport').scrollTo(0,0);}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>show(Number(b.dataset.view))));$('fit').onclick=fit;$('readable').onclick=()=>zoom(1);$('plus').onclick=()=>zoom(scale*1.25);$('minus').onclick=()=>zoom(scale/1.25);
function calculate(){const ids=['records','kib','dims','generations'];if(ids.some(id=>!$(id).validity.valid||$(id).value==='')){$('primary').textContent='Check inputs';$('backups').textContent='—';$('count').textContent='—';return;}const e=estimate(...ids.map(id=>Number($(id).value)));$('primary').textContent=e.primaryGiB.toFixed(2)+' GiB';$('backups').textContent=e.backupGiB.toFixed(2)+' GiB';$('count').textContent=e.recordsIn20GiB.toLocaleString();}
['records','kib','dims','generations'].forEach(id=>$(id).addEventListener('input',calculate));show(0);calculate();
</script></html>`;
    fs.writeFileSync(path.join(here,'index.html'),html);
    await page.setContent(html,{waitUntil:'load'});
    const checks=[];
    for(let i=0;i<rendered.length;i++){
      await page.locator(`[data-view="${i}"]`).click();
      assert.equal(await page.locator('#diagram svg').count(),1);
      assert.equal(await page.locator('#title').textContent(),rendered[i].title);
      checks.push({diagram:rendered[i].id,svg_rendered:true,width:rendered[i].width,height:rendered[i].height});
    }
    await page.locator('[data-view="0"]').click();
    await page.locator('#plus').click();
    await page.locator('#fit').click();
    assert.equal(await page.locator('#primary').textContent(),'1.81 GiB');
    await page.locator('#records').fill('1000000');
    assert.equal(await page.locator('#primary').textContent(),'18.12 GiB');
    await page.locator('#records').fill('-1');
    assert.equal(await page.locator('#primary').textContent(),'Check inputs');
    await page.locator('#records').fill('100000');
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
    assert.equal(overflow,false);
    await page.screenshot({path:path.join(here,'atlas-preview.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.locator('#fit').click();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await page.screenshot({path:path.join(here,'atlas-phone-preview.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    const result={date:'2026-10-11',mermaid_version:'11.12.0',renderer_sha256:crypto.createHash('sha256').update(fs.readFileSync(renderer)).digest('hex'),diagrams:checks,calculator_assertions:5,browser_checks:{tabs:rendered.length,zoom_fit:true,capacity_100k_and_1m:true,invalid_input:true,desktop_no_horizontal_overflow:true,phone_no_horizontal_overflow:true,page_errors:errors},network_requests_blocked:true,runtime_system_tested:false};
    fs.writeFileSync(path.join(here,'validation.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  } finally {await browser.close();}
}
main().catch(err=>{console.error(err);process.exitCode=1;});
