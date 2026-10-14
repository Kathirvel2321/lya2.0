"""Geometry and GLB invariants; no Blender, credentials or runtime data."""
from collections import Counter
import hashlib,json,math,struct,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'model'))
from build_model import make_model,normal,write_glb
spec=json.loads((root/'model/body-spec.json').read_text());objects=make_model(spec)
for obj in objects:
    edges=Counter();directed=Counter();v=obj['vertices'];assert all(all(math.isfinite(x) for x in p) for p in v)
    for face in obj['faces']:
        assert len(set(face))==3 and all(0<=i<len(v) for i in face);normal(*(v[i] for i in face))
        for a,b in zip(face,face[1:]+face[:1]):
            edges[tuple(sorted((a,b)))]+=1;directed[(a,b)]+=1
    assert all(count==2 for count in edges.values()),obj['name']
    assert all(count==1 and directed[(b,a)]==1 for (a,b),count in directed.items()),obj['name']
    volume=0
    for a,b,c in obj['faces']:
        a,b,c=[v[i] for i in (a,b,c)];cross=[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]];volume+=sum(a[i]*cross[i] for i in range(3))/6
    assert volume>0,obj['name']
    assert len(v)-len(edges)+len(obj['faces'])==2,obj['name']
p=root/'model/lya-body-candidate.glb';raw=p.read_bytes();magic,version,length=struct.unpack_from('<III',raw);assert magic==0x46546c67 and version==2 and length==len(raw)
size,kind=struct.unpack_from('<I4s',raw,12);assert kind==b'JSON';doc=json.loads(raw[20:20+size]);offset=20+size;binsize,kind=struct.unpack_from('<I4s',raw,offset);assert kind==b'BIN\0';binary=raw[offset+8:];assert binsize==len(binary)
for view in doc['bufferViews']:assert view['byteOffset']%4==0 and view['byteOffset']+view['byteLength']<=len(binary)
for accessor in doc['accessors']:
    view=doc['bufferViews'][accessor['bufferView']];assert view['byteLength']==accessor['count']*12
    assert accessor['componentType']==5126 and accessor['type']=='VEC3'
assert len(doc['nodes'])==len(objects)==7 and len(doc['meshes'])==7 and 'animations' not in doc
for m in doc['materials'][:2]:
    assert m['alphaMode']=='OPAQUE' and m['pbrMetallicRoughness']['metallicFactor']==0
    assert m['extensions']['KHR_materials_transmission']['transmissionFactor']>0
assert doc['extras']['no_shape_animation'] is True
assert spec['material']['glass']['transmissionFactor']>=.9
assert 1.4 <= spec['material']['glass']['ior'] <= 1.6
assert spec['material']['glass']['roughnessFactor'] < .05
assert sum(len(o['faces']) for o in objects)>2000
# Rebuild determinism without writing over the reviewed artifact.
import tempfile
with tempfile.TemporaryDirectory() as d:
    rebuilt=Path(d)/'candidate.glb';write_glb(objects,spec,rebuilt);assert rebuilt.read_bytes()==raw
result={'success':True,'closed_meshes':len(objects),'triangles':sum(len(o['faces']) for o in objects),'glb_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'visual_match_approved':False,'rendering_checked_by_this_test':False}
(root/'tests/model-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
