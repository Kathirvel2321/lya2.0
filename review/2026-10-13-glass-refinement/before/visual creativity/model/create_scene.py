"""Blender 4+ authoring entry. Scene/render not executed in the cloud environment.

blender --background --python create_scene.py
Add -- --render for a front PNG; -- --turnaround for eight consistent PNGs.
"""
import json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build_model import make_model
spec=json.loads((HERE/'body-spec.json').read_text());objects=make_model(spec)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=768;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.15,.19,.25,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
materials=[]
for name in ('glass','spine','core'):
    source=spec['material'][name];m=bpy.data.materials.new(name);m.use_nodes=True;node=m.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value=source['baseColorFactor'];node.inputs['Metallic'].default_value=source.get('metallicFactor',0)
    node.inputs['Roughness'].default_value=source.get('roughnessFactor',.06)
    if 'transmissionFactor' in source:
        node.inputs['Transmission Weight'].default_value=source['transmissionFactor'];node.inputs['IOR'].default_value=source['ior']
        absorb=m.node_tree.nodes.new('ShaderNodeVolumeAbsorption');absorb.inputs['Color'].default_value=(*source['attenuationColor'],1);absorb.inputs['Density'].default_value=1/source['attenuationDistance'];m.node_tree.links.new(absorb.outputs['Volume'],m.node_tree.nodes['Material Output'].inputs['Volume'])
    if 'emissiveFactor' in source:
        node.inputs['Emission Color'].default_value=(*source['emissiveFactor'],1);node.inputs['Emission Strength'].default_value=5
    materials.append(m)
root=bpy.data.objects.new('LYA_fixed_body',None);scene.collection.objects.link(root);root['status']=spec['status']
for obj in objects:
    mesh=bpy.data.meshes.new(obj['name']);mesh.from_pydata([(x,-z,y) for x,y,z in obj['vertices']],[],obj['faces']);mesh.update()
    entity=bpy.data.objects.new(obj['name'],mesh);scene.collection.objects.link(entity);entity.parent=root;entity.data.materials.append(materials[obj['material']])
    for face in entity.data.polygons:face.use_smooth=False
bpy.ops.object.camera_add(location=(0,-6,.13));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,.05))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=2.75;scene.camera=camera
for name,location,power,size,color in [('key',(-3,-4,4),650,4,(.8,.93,1)),('edge',(3,1,2),900,3,(.35,.75,1)),('fill',(-2,2,0),400,3,(.45,.65,1))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    entity=bpy.data.objects.new(name,data);scene.collection.objects.link(entity);entity.location=location;entity.rotation_euler=(-entity.location).to_track_quat('-Z','Y').to_euler()
scene.use_nodes=True;nodes=scene.node_tree.nodes;nodes.clear();layers=nodes.new('CompositorNodeRLayers');glare=nodes.new('CompositorNodeGlare');glare.glare_type='FOG_GLOW';glare.quality='HIGH';glare.threshold=2.5;glare.mix=-.92
output=nodes.new('CompositorNodeComposite');scene.node_tree.links.new(layers.outputs['Image'],glare.inputs['Image']);scene.node_tree.links.new(glare.outputs['Image'],output.inputs['Image'])
out=HERE/'rendered';out.mkdir(exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(out/'lya-body-candidate.blend'))
if '--turnaround' in args:
    for angle in range(0,360,45):
        root.rotation_euler.z=math.radians(angle);scene.render.filepath=str(out/f'candidate-{angle:03d}.png');bpy.ops.render.render(write_still=True)
elif '--render' in args:
    scene.render.filepath=str(out/'candidate-front.png');bpy.ops.render.render(write_still=True)
