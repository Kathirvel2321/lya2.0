"""Root-configured Linux service/control entry point. Never read laptop private stores."""
import json
import base64
import os
from pathlib import Path
import sys
import time

from cloud.mobile import AuthStore,Connection,PrivateHTTP
from cloud.ssh_session import exchange

CONFIG=Path('/etc/lya-connect.json')
STATE=Path('/var/lib/lya-connect/auth.sqlite')


def infer(messages,cancelled):
    packet=dict(messages=messages,task='general',sensitivity='public')
    body=json.dumps(packet,ensure_ascii=True)
    if len(body.encode())>65536:raise ValueError('Question context too large.')
    # Exact sudoers command; no shell, caller-selected executable or provider-key copy.
    command=['sudo','-n','-u','ubuntu','/usr/bin/python3','/home/ubuntu/lya/inference.py']
    result=exchange(command,body,cancelled,timeout=30,close_stdin=True)
    if result.returncode or len(result.stdout)>65536:raise ValueError('Inference unavailable.')
    answer=json.loads(result.stdout)
    if type(answer) is not dict or answer.get('error'):raise ValueError('Inference unavailable.')
    return answer.get('text')


def transcribe(audio,cancelled):
    command=['sudo','-n','-u','ubuntu','/opt/lya-connect/speech-venv/bin/python','-I','-u','/opt/lya-connect/speech.py']
    body=json.dumps({'audio':base64.b64encode(audio).decode('ascii')})
    result=exchange(command,body,cancelled,timeout=35)
    if result.returncode or len(result.stdout)>65536:raise ValueError('Phone speech unavailable.')
    answer=json.loads(result.stdout)
    if type(answer) is not dict or set(answer)!={'text'}:raise ValueError('Phone speech unavailable.')
    return answer['text']


def speak(text,cancelled):
    command=['/opt/lya-connect/tts-venv/bin/python','-I','/opt/lya-connect/reply.py']
    result=exchange(command,json.dumps({'text':text}),cancelled,timeout=25,close_stdin=True,output_limit=11000000)
    if result.returncode or len(result.stdout)>11000000:raise ValueError('LYA voice unavailable.')
    answer=json.loads(result.stdout)
    if type(answer) is not dict or set(answer)!={'audio'}:raise ValueError('LYA voice unavailable.')
    return answer['audio']


def configured_researcher(config, state=STATE):
    """Explicit evaluation profile only; no credentials or paid fallback."""
    setting=config.get('public_research')
    if setting is None or setting is False:
        return None
    if setting != 'keyless_evaluation':
        raise ValueError('Unknown public research configuration.')
    from cloud.public_search import YouSearchMCP
    from cloud.web_research import PublicResearcher, DailySearchQuota
    return PublicResearcher(YouSearchMCP(),DailySearchQuota(Path(state).with_name('research-usage.sqlite')))


def main():
    os.umask(0o077)
    operation=sys.argv[1] if len(sys.argv)==2 else 'serve' if len(sys.argv)==1 else None
    config=json.loads(CONFIG.read_text())
    store=AuthStore(STATE)
    if operation in ('invite','revoke'):
        packet=json.loads(sys.stdin.buffer.read(4097))
        if type(packet) is not dict or set(packet)!= {'binding'}:raise ValueError('Invalid control request.')
        result=store.control(operation,packet['binding'],time.time())
        if 'token' in result:result={'url':config['origin']+'/#'+result['token']}
        elif result.get('paired'):result={'url':config['origin']+'/','paired':True}
        print(json.dumps(result))
        return
    if operation!='serve':raise ValueError('Unknown operation.')
    app=Connection(config['origin'],store,infer,transcribe=transcribe if config.get('speech_enabled') is True else None,
                   speak=speak if config.get('reply_voice_enabled') is True else None,
                   researcher=configured_researcher(config))
    http=PrivateHTTP(('127.0.0.1',8766),app)
    try:http.serve_forever(poll_interval=.2)
    finally:http.server_close()


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('LYA connection operation failed; private details withheld.')
