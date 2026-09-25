"""One-time GLB artwork bake; never imported by the desktop runtime.

Handles this project's untextured triangle GLB. Lighting approximates its metallic
and emissive materials; transmission/refraction are not physically simulated.
Requires the existing Qt/OpenGL and NumPy packages, no browser or network.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import (QGuiApplication, QOpenGLContext, QSurfaceFormat,
                          QOffscreenSurface, QMatrix4x4, QVector3D)
from PySide6.QtOpenGL import (QOpenGLBuffer, QOpenGLFramebufferObject,
                             QOpenGLFramebufferObjectFormat, QOpenGLShader,
                             QOpenGLShaderProgram, QOpenGLVertexArrayObject)

VERTEX = '''#version 330 core
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
uniform mat4 mvp;
uniform mat4 model;
out vec3 worldPosition;
out vec3 worldNormal;
void main() {
    worldPosition = (model * vec4(position,1)).xyz;
    worldNormal = mat3(transpose(inverse(model))) * normal;
    gl_Position = mvp * vec4(position,1);
}'''

FRAGMENT = '''#version 330 core
in vec3 worldPosition;
in vec3 worldNormal;
uniform vec3 baseColor;
uniform vec3 emission;
uniform float metal;
uniform float opacity;
out vec4 color;
void main() {
    vec3 n = normalize(worldNormal);
    vec3 v = normalize(vec3(0,0,10)-worldPosition);
    if (dot(n,v)<0) n=-n;
    vec3 r = reflect(-v,n);
    float key = max(dot(n,normalize(vec3(-2,3,4))),0);
    float rim = pow(1-max(dot(n,v),0),3);
    vec3 env = vec3(.08,.11,.15);
    env += vec3(2.8,2.9,3) * pow(max(dot(r,normalize(vec3(-2,3,4))),0),18);
    env += vec3(1.8,2,2.2) * pow(max(dot(r,normalize(vec3(3,1,3))),0),34);
    env += vec3(.02,.7,.85) * pow(max(dot(r,normalize(vec3(-3,0,1))),0),16);
    env += vec3(1,.3,.04) * pow(max(dot(r,normalize(vec3(3,-1,1))),0),22);
    vec3 reflectance = mix(vec3(.12),max(baseColor,vec3(.12)),metal);
    vec3 lit = baseColor*(.5+key*1.5) + env*reflectance + rim*vec3(.12,.2,.23) + emission*.7;
    color = vec4(pow(lit/(1+lit),vec3(1.0/2.2)),opacity);
}'''


def load_meshes(path):
    raw = path.read_bytes()
    if len(raw)>16_000_000 or len(raw)<28:
        raise ValueError('Unexpected GLB size')
    magic, version, length = struct.unpack_from('<4sII',raw)
    if (magic,version,length)!=(b'glTF',2,len(raw)):
        raise ValueError('Invalid GLB header')
    size, kind = struct.unpack_from('<II',raw,12)
    if kind!=0x4E4F534A:
        raise ValueError('Missing JSON chunk')
    doc=json.loads(raw[20:20+size]);offset=20+size
    bin_size,kind=struct.unpack_from('<II',raw,offset)
    if kind!=0x004E4942 or offset+8+bin_size>len(raw):
        raise ValueError('Missing binary chunk')
    binary=raw[offset+8:offset+8+bin_size]
    if doc.get('images') or doc.get('animations') or doc.get('extensionsRequired') or any('uri' in b for b in doc['buffers']):
        raise ValueError('This bake accepts only embedded, untextured static meshes')

    def vectors(index):
        a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']]
        if a['componentType']!=5126 or a['type']!='VEC3' or a.get('sparse') or view.get('byteStride',12)!=12:
            raise ValueError('Unsupported accessor')
        start=view.get('byteOffset',0)+a.get('byteOffset',0)
        end=start+a['count']*12
        if not 0<=start<end<=len(binary) or a['count']>600_000:
            raise ValueError('Accessor outside buffer')
        result=np.frombuffer(binary[start:end],dtype='<f4').reshape(-1,3)
        if not np.isfinite(result).all():
            raise ValueError('Nonfinite vertices')
        return result

    meshes=[]
    def visit(index, parent, ancestry=()):
        if index in ancestry or len(ancestry)>32:
            raise ValueError('Invalid node hierarchy')
        node=doc['nodes'][index]
        if any(k in node for k in ('translation','rotation','scale')):
            raise ValueError('Only matrix node transforms are supported by this asset bake')
        transform=parent @ np.array(node.get('matrix',np.eye(4).flatten()),dtype=float).reshape(4,4).T
        if 'mesh' in node:
            for p in doc['meshes'][node['mesh']]['primitives']:
                if p.get('mode',4)!=4 or 'indices' in p:
                    raise ValueError('Expected flat triangle primitives')
                pos=vectors(p['attributes']['POSITION']);norm=vectors(p['attributes']['NORMAL'])
                if len(pos)!=len(norm) or len(pos)%3:
                    raise ValueError('Invalid triangle data')
                pos=(np.column_stack((pos,np.ones(len(pos)))) @ transform.T)[:,:3]
                norm=norm @ np.linalg.inv(transform[:3,:3])
                norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-8)
                meshes.append((np.column_stack((pos,norm)).astype('f4'),doc['materials'][p['material']]))
        for child in node.get('children',[]):
            visit(child,transform,(*ancestry,index))
    for node in doc['scenes'][doc.get('scene',0)]['nodes']:
        visit(node,np.eye(4))
    if not meshes or sum(len(m[0]) for m in meshes)>600_000:
        raise ValueError('Mesh budget exceeded')
    return meshes,hashlib.sha256(raw).hexdigest()


def bake(source, output, angle=0):
    meshes,digest=load_meshes(source)
    app=QGuiApplication.instance() or QGuiApplication([])
    fmt=QSurfaceFormat();fmt.setVersion(3,3);fmt.setProfile(QSurfaceFormat.CoreProfile)
    surface=QOffscreenSurface();surface.setFormat(fmt);surface.create()
    context=QOpenGLContext();context.setFormat(fmt)
    if not context.create() or not context.makeCurrent(surface):
        raise RuntimeError('No offscreen OpenGL context; keep original artwork')
    program=QOpenGLShaderProgram()
    for kind,code in [(QOpenGLShader.Vertex,VERTEX),(QOpenGLShader.Fragment,FRAGMENT)]:
        if not program.addShaderFromSourceCode(kind,code):
            raise RuntimeError(program.log())
    if not program.link() or not program.bind():
        raise RuntimeError(program.log())
    vao=QOpenGLVertexArrayObject();vao.create();vao.bind()
    buffer=QOpenGLBuffer();buffer.create();buffer.bind()
    program.enableAttributeArray(0);program.enableAttributeArray(1)
    program.setAttributeBuffer(0,0x1406,0,3,24);program.setAttributeBuffer(1,0x1406,12,3,24)
    ffmt=QOpenGLFramebufferObjectFormat();ffmt.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
    ffmt.setSamples(4)
    target=QOpenGLFramebufferObject(768,1088,ffmt)
    if not target.isValid():
        raise RuntimeError('Invalid render target')
    target.bind();gl=context.functions();gl.glViewport(0,0,768,1088)
    program.bind()
    gl.glEnable(0x0B71);gl.glClearColor(0,0,0,0);gl.glClear(0x4000|0x0100)
    projection=QMatrix4x4();projection.ortho(-2.05,2.05,-2.9,2.9,.1,30)
    view=QMatrix4x4();view.lookAt(QVector3D(0,0,10),QVector3D(0,.05,0),QVector3D(0,1,0))
    model=QMatrix4x4()
    model.rotate(angle, 0, 1, 0)
    program.setUniformValue('model',model);program.setUniformValue('mvp',projection*view*model)
    # A small alpha approximation exposes the authored energy geometry beneath
    # the glass. This is deliberately not a physical refraction implementation.
    ordered=sorted(meshes,key=lambda mesh: 'KHR_materials_transmission' in mesh[1].get('extensions',{}))
    for vertices,material in ordered:
        data=vertices.tobytes();buffer.allocate(data,len(data))
        pbr=material.get('pbrMetallicRoughness',{})
        emission=np.array(material.get('emissiveFactor',[0,0,0]))*material.get('extensions',{}).get('KHR_materials_emissive_strength',{}).get('emissiveStrength',1)
        program.setUniformValue('baseColor',QVector3D(*pbr.get('baseColorFactor',[1,1,1,1])[:3]))
        program.setUniformValue('emission',QVector3D(*emission.tolist()))
        gl.glUniform1f(program.uniformLocation('metal'),float(pbr.get('metallicFactor',1)))
        transmission=material.get('extensions',{}).get('KHR_materials_transmission',{}).get('transmissionFactor',0)
        if transmission:
            gl.glEnable(0x0BE2);gl.glBlendFuncSeparate(0x0302,0x0303,1,0x0303);gl.glDepthMask(False)
        gl.glUniform1f(program.uniformLocation('opacity'),float(1-transmission))
        gl.glDrawArrays(0x0004,0,len(vertices))
        gl.glDepthMask(True);gl.glDisable(0x0BE2)
    gl.glFinish()
    image=target.toImage().scaled(288,408,Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
    if sum(image.pixelColor(x,y).alpha()>0 for x in range(0,288,8) for y in range(0,408,8)) < 100:
        raise RuntimeError('Empty or clipped bake; keep original artwork')
    output.parent.mkdir(parents=True,exist_ok=True)
    if not image.save(str(output)):
        raise RuntimeError('Could not save artwork')
    report={'source_sha256':digest,'triangles':sum(len(v)//3 for v,m in meshes),'materials':len(meshes),
            'output_pixels':[288,408],'runtime_3d_renderer':False,'shading':'approximate metallic/emissive; no physical refraction'}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    buffer.destroy();vao.destroy();program.release();target.release()
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();bake(args.source,args.output)
