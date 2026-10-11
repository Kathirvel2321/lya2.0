"""Render synthetic phone states only; no app session, microphone or network calls."""
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
page = re.sub(r'<script nonce="__NONCE__">[\s\S]*?</script>', '', page)
page = page.replace('<link rel="manifest" href="/manifest.webmanifest">', '')
page = page.replace('<section id="auth">', '<section id="auth" hidden>')
page = page.replace('<section id="chat" hidden>', '<section id="chat">')
page = page.replace('<button id="lock" hidden>', '<button id="lock">')
page = page.replace('Your private connection.', 'Synthetic preview · Listening.')
page = page.replace('LYA will listen automatically after sign-in and answer after you pause.', 'Synthetic preview · automatic listening.')
page = page.replace('<p id="question"></p>', '<p id="question">Can we continue the LYA project?</p>')
page = page.replace('<div id="answer" role="log" aria-live="polite"></div>',
                    '<div id="answer" role="log" aria-live="polite">Right here with you. '
                    'This is a synthetic layout preview, with no microphone, sign-in or saved personal information.</div>')

# An iframe supplies an exact CSS phone viewport even when headless Windows
# applies its minimum outer-window size. All iframe contents are inline/local.
checks = []
with tempfile.TemporaryDirectory(prefix='lya-layout-') as temporary:
    for width in (320, 390, 768):
        for state in ('locked', 'listening', 'thinking', 'speaking'):
            content = page.replace('data-state="locked"', f'data-state="{state}"')
            long_reply = state == 'speaking'
            if long_reply:
                content = content.replace('Right here with you. This is a synthetic layout preview, with no microphone, sign-in or saved personal information.', 'SyntheticLongWord'*500)
            if state == 'locked':
                content = content.replace('<section id="auth" hidden>', '<section id="auth">')
                content = content.replace('<section id="chat">', '<section id="chat" hidden>')
            frame = f'<iframe id="phone" style="width:{width}px;height:844px;border:0" srcdoc="{html.escape(content, quote=True)}"></iframe>'
            probe = '''<script>
window.onload=()=>{const d=document.getElementById('phone').contentDocument,w=d.defaultView;
const visible=id=>d.getElementById(id).getBoundingClientRect().width>0;
const panel=d.querySelector('.panel');
const result={viewport:w.innerWidth,scroll:d.documentElement.scrollWidth,
 voiceFirst:d.getElementById('hearing').textContent.includes('automatic'),
 panel:d.querySelector('.panel').getBoundingClientRect().width,
 auth:visible('auth'),chat:visible('chat'),state:d.body.dataset.state,
 diamond:w.getComputedStyle(d.querySelector('.diamond')).display,
 thought:w.getComputedStyle(d.querySelector('.thought')).display,
 wave:w.getComputedStyle(d.querySelector('.wave')).display,
 statusBottom:d.getElementById('status').getBoundingClientRect().bottom};
const out=document.createElement('pre');out.id='result';out.hidden=true;out.textContent=JSON.stringify(result);document.body.append(out)};
</script>'''
            wrapper = '<!doctype html><meta charset="utf-8"><body style="margin:0;background:#091016">'+frame+probe
            fixture = HERE/'preview.html'
            fixture.write_text(wrapper, encoding='utf-8')
            args = [str(CHROME), '--headless', '--disable-gpu', '--no-first-run',
                    '--no-default-browser-check', '--hide-scrollbars', '--force-device-scale-factor=1',
                    f'--user-data-dir={temporary}', f'--window-size={max(500,width)},844',
                    '--virtual-time-budget=1500']
            run = subprocess.run(args+['--dump-dom',fixture.as_uri()], capture_output=True, timeout=20)
            match = re.search(r'<pre id="result"[^>]*>([^<]+)</pre>',run.stdout.decode('utf-8'))
            assert run.returncode == 0 and match, 'Synthetic renderer did not return layout metrics.'
            result = json.loads(html.unescape(match[1]))
            assert result['viewport'] == width, result
            assert result['scroll'] <= width, result
            assert result['statusBottom'] <= 844, result
            assert result['voiceFirst'], result
            result['long_voice_reply'] = long_reply
            assert result['auth'] == (state == 'locked') and result['chat'] == (state != 'locked'), result
            assert (result['thought'] != 'none') == (state == 'thinking'), result
            assert (result['wave'] != 'none') == (state == 'speaking'), result
            if state in ('thinking','speaking'):
                assert result['diamond'] == 'none', result
            checks.append(result)
            if width == 390 and state == 'listening':
                subprocess.run(args+[f'--screenshot={HERE/"phone-preview.png"}',fixture.as_uri()],
                               capture_output=True, check=True, timeout=20)
    # Leave a useful synthetic preview rather than the last loop's tablet fixture.
    preview = page.replace('data-state="locked"','data-state="listening"')
    (HERE/'preview.html').write_text(preview,encoding='utf-8')

result = dict(success=True, rendered_states=len(checks),checks=checks,
              real_phone=False,real_session=False,real_audio=False,provider_call=False)
(HERE/'layout-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(success=True,rendered_states=len(checks))))
