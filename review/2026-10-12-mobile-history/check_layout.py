"""Run the real client against in-page fake replies; no sensors or network."""
import html
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CHROME = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
page = (ROOT/'cloud/mobile.html').read_text(encoding='utf-8')
client = re.search(r'<script nonce="__NONCE__">([\s\S]*?)</script>', page)[1]
assert 'localStorage' not in client and 'innerHTML' not in client
assert page.count('nonce="__NONCE__"') == 2
ids = re.findall(r'\bid="([^"]+)"', page)
assert len(ids) == len(set(ids))
assert set(re.findall(r"\$\('([^']+)'\)", client)) <= set(ids)
stub = '''
// srcdoc has no app URL to normalize; production URL handling is unchanged.
history.replaceState=()=>{};
window.fetch=async(path,options)=>{
 const request=JSON.parse(options.body);
 const body=path==='/session'?{voice_available:false,expires_in:3600}:
 path==='/chat'?{text:'Synthetic preview reply. '+(request.text==='A long answer'?'LongWord'.repeat(180):'No microphone, account or model is connected.')}:
 ['/stop','/logout'].includes(path)?{}:null;
 if(!body)throw Error('Preview blocks external requests');
 return {ok:true,status:200,json:async()=>body};
};
'''
demo = '''
window.previewReady=(async()=>{
 await restore(false);
 await submitQuestion('Can we keep recent messages?',false);
 await submitQuestion('Can I correct my last question?',false);
 await submitQuestion('A long answer',false);
 $('chat').scrollTop=0;
 $('owner').disabled=true;$('owner').onclick=null;$('sign').disabled=true;$('sign').onclick=null;
 status.textContent='Preview only. Tap your question to edit and resend.';
})();
'''
preview = page.replace('<link rel="manifest" href="/manifest.webmanifest">','')
preview = preview.replace('<script nonce="__NONCE__">','<script nonce="__NONCE__">'+stub).replace('</script>',demo+'</script>')
(HERE/'preview.html').write_text(preview, encoding='utf-8')
(HERE/'client.js').write_text(client, encoding='utf-8')
subprocess.run(['node','--check',str(HERE/'client.js')], check=True, capture_output=True)
checks = []
with tempfile.TemporaryDirectory(dir=HERE,prefix='.browser-',ignore_cleanup_errors=True) as temporary:
    for width, height in [(320,568),(390,844),(768,1024),(390,420)]:
        for state in ('history','editing','locked'):
            probe = '''
window.onload=async()=>{
 const frame=document.getElementById('phone'),w=frame.contentWindow,d=frame.contentDocument;
 try{
 if(!w.previewReady)throw Error('Client preview did not initialize');await w.previewReady;
 const el=id=>d.getElementById(id);
 if(STATE==='editing'){
  el('question').click();
  if(el('text').value!=='A long answer'||d.activeElement!==el('text'))throw Error('Edit did not prefill/focus');
  el('text').value='Corrected question';
  el('composer').dispatchEvent(new w.Event('submit',{cancelable:true}));
  await Promise.resolve();await Promise.resolve();await Promise.resolve();
  if(el('question').textContent!=='Corrected question'||el('recent').children.length!==3)throw Error('Correction not resent');
  el('question').click();
 }
 if(STATE==='locked')el('lock').click();
 const visible=id=>el(id).getBoundingClientRect().width>0;
 const box=el('text').getBoundingClientRect();
 const result={viewport:w.innerWidth,height:w.innerHeight,scroll:d.documentElement.scrollWidth,state:STATE,
  recent:el('recent').children.length,auth:visible('auth'),chat:visible('chat'),
  composerBottom:box.bottom,questionButton:el('question').tagName,
  chatOverflow:el('chat').scrollHeight>el('chat').clientHeight};
 const out=document.createElement('pre');out.id='result';out.hidden=true;out.textContent=JSON.stringify(result);document.body.append(out);
 }catch(e){document.body.textContent='LAYOUT ERROR '+e.message}
};
'''.replace('STATE',json.dumps(state))
            fixture = HERE/'layout.html'
            fixture.write_text('<!doctype html><meta charset="utf-8"><body style="margin:0;background:#091016">'
                +f'<iframe id="phone" style="width:{width}px;height:{height}px;border:0" srcdoc="{html.escape(preview,quote=True)}"></iframe>'
                +'<script>'+probe+'</script>', encoding='utf-8')
            args=[str(CHROME),'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
                '--disable-background-networking','--disable-component-update','--disable-sync',
                '--hide-scrollbars','--force-device-scale-factor=1',f'--user-data-dir={temporary}',
                f'--window-size={max(500,width)},{height}','--virtual-time-budget=2000']
            run=subprocess.run(args+['--dump-dom',fixture.as_uri()],capture_output=True,timeout=25)
            match=re.search(r'<pre id="result"[^>]*>([^<]+)</pre>',run.stdout.decode('utf-8'))
            assert run.returncode==0 and match, 'Renderer did not return metrics: '+str(run.returncode)+' '+run.stderr.decode('utf-8',errors='replace')[-400:]+' '+run.stdout.decode('utf-8')[-400:]
            result=json.loads(html.unescape(match[1]))
            assert result['viewport']==width and result['scroll']<=width, result
            assert result['auth']==(state=='locked') and result['chat']==(state!='locked'),result
            assert result['recent']=={'history':2,'editing':3,'locked':0}[state],result
            assert result['composerBottom']<=height or state=='locked',result
            assert result['questionButton']=='BUTTON',result
            if state!='locked':assert result['chatOverflow'],result
            checks.append(result)
            if width==390 and height==844 and state=='history':
                subprocess.run(args+[f'--screenshot={HERE/"phone-preview.png"}',fixture.as_uri()],capture_output=True,check=True,timeout=25)
    fixture.unlink()
result=dict(success=True,rendered_states=len(checks),checks=checks,real_phone=False,real_audio=False,provider_call=False)
(HERE/'layout-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(success=True,rendered_states=len(checks))))
