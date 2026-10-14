"""Deterministic editable geometry candidate; not an approved glass likeness.

Standard library only. Produces GLB 2.0 with actual closed 3D volumes and PBR
transmission/volume/IOR materials. No reference image is modified.
"""
import json,math,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent

def closed_sail(outline,ridge,thickness):
    n=len(outline)
    vertices=[list(p) for p in outline]+[[p[0],p[1],p[2]-thickness] for p in outline]
    vertices += [list(ridge),[ridge[0],ridge[1],ridge[2]-thickness-.13]]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [[2*n,i,j],[2*n+1,n+j,n+i],[i,n+i,n+j],[i,n+j,j]]
    return vertices,faces

def spine(sections,sides=8):
    vertices=[];faces=[]
    for index,(x,y,z,rx,rz) in enumerate(sections):
        before=sections[max(0,index-1)];after=sections[min(len(sections)-1,index+1)]
        tx,ty=after[0]-before[0],after[1]-before[1];length=math.hypot(tx,ty)
        ux,uy=ty/length,-tx/length
        for i in range(sides):
            a=i*math.tau/sides;vertices.append([x+ux*rx*math.cos(a),y+uy*rx*math.cos(a),z+rz*math.sin(a)])
    for ring in range(len(sections)-1):
        for i in range(sides):
            a=ring*sides+i;b=ring*sides+(i+1)%sides;c=b+sides;d=a+sides
            faces += [[a,b,c],[a,c,d]]
    for start,reverse in ((0,True),((len(sections)-1)*sides,False)):
        centre=len(vertices);p=sections[0 if reverse else -1];vertices.append(list(p[:3]))
        for i in range(sides):
            a=start+i;b=start+(i+1)%sides;faces.append([centre,b,a] if reverse else [centre,a,b])
    return vertices,faces

def normal(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    length=math.sqrt(sum(x*x for x in n))
    if length<1e-12:raise ValueError('Degenerate face')
    return [x/length for x in n]

def core(spec):
    x,y,z=spec['center'];a,b,c=spec['radii']
    v=[[x+a,y,z],[x-a,y,z],[x,y+b,z],[x,y-b,z],[x,y,z+c],[x,y,z-c]]
    f=[[2,0,4],[2,4,1],[2,1,5],[2,5,0],[3,4,0],[3,1,4],[3,5,1],[3,0,5]]
    return v,f

def make_model(spec):
    objects=[]
    v,f=spine(spec['spine_sections']);objects.append({'name':'backbone','vertices':v,'faces':f,'material':1})
    for sail in spec['sails']:
        v,f=closed_sail(sail['outline'],sail['ridge'],sail['thickness']);objects.append({'name':sail['name'],'vertices':v,'faces':f,'material':0})
    v,f=core(spec['core']);objects.append({'name':'core','vertices':v,'faces':f,'material':2})
    for obj in objects:
        volume=0.0
        for face in obj['faces']:
            a,b,c=[obj['vertices'][i] for i in face]
            cross=[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]]
            volume+=sum(a[i]*cross[i] for i in range(3))/6
        if volume<0:obj['faces']=[list(reversed(face)) for face in obj['faces']]
    return objects

def material(name,m):
    result={'name':name,'doubleSided':True,'alphaMode':'OPAQUE','pbrMetallicRoughness':{k:m[k] for k in ('baseColorFactor','metallicFactor','roughnessFactor') if k in m}}
    if 'emissiveFactor' in m:result['emissiveFactor']=m['emissiveFactor']
    if 'transmissionFactor' in m:result['extensions']={
        'KHR_materials_transmission':{'transmissionFactor':m['transmissionFactor']},
        'KHR_materials_ior':{'ior':m['ior']},
        'KHR_materials_volume':{'thicknessFactor':m['thicknessFactor'],'attenuationColor':m['attenuationColor'],'attenuationDistance':m['attenuationDistance']}}
    return result

def write_glb(objects,spec,path):
    binary=bytearray();views=[];accessors=[];meshes=[]
    def attribute(values,typ,components):
        while len(binary)%4:binary.extend(b'\0')
        offset=len(binary);data=struct.pack('<'+'f'*len(values),*values);binary.extend(data)
        views.append({'buffer':0,'byteOffset':offset,'byteLength':len(data),'target':34962})
        rows=[values[i:i+components] for i in range(0,len(values),components)]
        accessors.append({'bufferView':len(views)-1,'componentType':5126,'count':len(rows),'type':typ,
                          'min':[min(r[i] for r in rows) for i in range(components)],'max':[max(r[i] for r in rows) for i in range(components)]})
        return len(accessors)-1
    for obj in objects:
        positions=[];normals=[]
        for face in obj['faces']:
            a,b,c=[obj['vertices'][i] for i in face];n=normal(a,b,c)
            for p in (a,b,c):positions.extend(p);normals.extend(n)
        pos=attribute(positions,'VEC3',3);norm=attribute(normals,'VEC3',3)
        meshes.append({'name':obj['name'],'primitives':[{'attributes':{'POSITION':pos,'NORMAL':norm},'material':obj['material'],'mode':4}]})
    doc={'asset':{'version':'2.0','generator':'LYA visual creativity geometry candidate'},'scene':0,'scenes':[{'nodes':list(range(len(meshes)))}],
         'nodes':[{'name':o['name'],'mesh':i} for i,o in enumerate(objects)],'meshes':meshes,'materials':[material(k,spec['material'][k]) for k in ('glass','spine','core')],
         'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors,
         'extensionsUsed':['KHR_materials_transmission','KHR_materials_volume','KHR_materials_ior'],
         'extras':{'status':spec['status'],'reference_pose':spec['reference_pose'],'no_shape_animation':True}}
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);binary+=b'\0'*((-len(binary))%4)
    length=12+8+len(encoded)+8+len(binary)
    path.write_bytes(struct.pack('<III',0x46546c67,2,length)+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
    return doc

def main():
    spec=json.loads((HERE/'body-spec.json').read_text());objects=make_model(spec)
    (HERE/'candidate.json').write_text(json.dumps({'status':spec['status'],'objects':objects},separators=(',',':'))+'\n')
    write_glb(objects,spec,HERE/'lya-body-candidate.glb')
    result={'objects':len(objects),'triangles':sum(len(o['faces']) for o in objects),'vertices':sum(len(o['vertices']) for o in objects),'bytes':(HERE/'lya-body-candidate.glb').stat().st_size,'status':spec['status']}
    (HERE/'geometry-stats.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
