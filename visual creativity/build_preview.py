"""Bundle local sources into an offline standalone HTML. Standard library only."""
import base64,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
    data=json.loads((HERE/'states.json').read_text());mesh=json.loads((HERE/'model/candidate.json').read_text())
    sprite=base64.b64encode((HERE/data['body']['asset']).read_bytes()).decode()
    renders=[HERE/'model/rendered-glass'/f'glass-{angle:03d}.png' for angle in range(0,360,45)]
    assert all(p.is_file() for p in renders),'Render the glass turnaround before bundling'
    frames=['data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() for p in renders]
    s=(HERE/'preview.template.html').read_text(encoding='utf-8')
    for key,value in {'__GLASS_FRAMES__':json.dumps(frames),'__CONFIG__':json.dumps(data),'__MESH__':json.dumps(mesh),'__SPRITE__':sprite,'__EFFECTS__':(HERE/'effects.js').read_text(encoding='utf-8')}.items():
        assert s.count(key)==1,key;s=s.replace(key,value)
    (HERE/'preview.html').write_text(s,encoding='utf-8')
    print(json.dumps({'preview_bytes':len(s.encode()),'offline':True,'body_asset':data['body']['asset']}))
if __name__=='__main__':main()
