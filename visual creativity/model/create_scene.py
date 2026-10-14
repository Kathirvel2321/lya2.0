"""Create and render the isolated glass study with portable Blender 4.5.

blender --background --factory-startup --python create_scene.py -- --render
Use --quick for a draft, --turnaround for eight views, --transparent for cutouts.
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_model import make_model

spec = json.loads((HERE / 'body-spec.json').read_text())
objects = make_model(spec)
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24 if '--quick' in args else 64 if '--turnaround' in args else 96
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 16
scene.cycles.transmission_bounces = 12
scene.cycles.transparent_max_bounces = 12
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 384 if '--quick' in args else 512 if '--turnaround' in args else 768
scene.render.resolution_y = 512 if '--quick' in args else 640 if '--turnaround' in args else 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = '--transparent' in args
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.world.use_nodes = True
world = scene.world.node_tree.nodes['Background']
world.inputs['Color'].default_value = (.26, .28, .30, 1)
world.inputs['Strength'].default_value = .65
materials = []
for name in ('glass', 'spine', 'core'):
    source = spec['material'][name]
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    node = nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = source['baseColorFactor']
    node.inputs['Metallic'].default_value = source.get('metallicFactor', 0)
    node.inputs['Roughness'].default_value = source.get('roughnessFactor', .04)
    node.inputs['Coat Weight'].default_value = .25
    node.inputs['Coat Roughness'].default_value = .02
    if 'transmissionFactor' in source:
        node.inputs['Transmission Weight'].default_value = source['transmissionFactor']
        node.inputs['IOR'].default_value = source['ior']
        absorb = nodes.new('ShaderNodeVolumeAbsorption')
        absorb.inputs['Color'].default_value = (*source['attenuationColor'], 1)
        absorb.inputs['Density'].default_value = 1 / source['attenuationDistance']
        material.node_tree.links.new(absorb.outputs['Volume'], nodes['Material Output'].inputs['Volume'])
    if 'emissiveFactor' in source:
        node.inputs['Emission Color'].default_value = (*source['emissiveFactor'], 1)
        node.inputs['Emission Strength'].default_value = 9
    materials.append(material)

root = bpy.data.objects.new('LYA_fixed_glass_body', None)
scene.collection.objects.link(root)
root['status'] = spec['status']
for obj in objects:
    mesh = bpy.data.meshes.new(obj['name'])
    mesh.from_pydata([(x, -z, y) for x, y, z in obj['vertices']], [], obj['faces'])
    mesh.update()
    entity = bpy.data.objects.new(obj['name'], mesh)
    scene.collection.objects.link(entity)
    entity.parent = root
    mesh.materials.append(materials[obj['material']])
    for face in mesh.polygons:
        face.use_smooth = False
    # Tiny polished edges catch a softbox without rounding away the reference folds.
    bevel = entity.modifiers.new('polished edges', 'BEVEL')
    bevel.width = .002
    bevel.segments = 2
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = .12

bpy.ops.object.camera_add(location=(0, -6, .06))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, .06)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 2.85
scene.camera = camera
for name, location, power, width, height, color in (
    ('white vertical reflection', (-2, -3, 1.6), 260, .45, 4, (.82, .93, 1)),
    ('cyan rim', (2.5, .7, 1.2), 500, .35, 3.5, (.35, .75, 1)),
    ('white top edge', (.2, -1.5, 3.5), 250, 2.8, .16, (1, 1, 1)),
    ('soft blue fill', (-2, 1.8, -.4), 300, 2, 3, (.48, .70, 1)),
    ('narrow front streak', (1.2, -3, -.2), 90, .12, 3, (.75, .90, 1)),
):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = power
    light.shape = 'RECTANGLE'
    light.size = width
    light.size_y = height
    light.color = color
    entity = bpy.data.objects.new(name, light)
    scene.collection.objects.link(entity)
    entity.location = location
    entity.rotation_euler = (-entity.location).to_track_quat('-Z', 'Y').to_euler()

scene.use_nodes = True
nodes = scene.node_tree.nodes
nodes.clear()
layers = nodes.new('CompositorNodeRLayers')
glow = nodes.new('CompositorNodeGlare')
glow.glare_type = 'FOG_GLOW'
glow.quality = 'HIGH'
glow.inputs['Threshold'].default_value = 2.5
glow.inputs['Strength'].default_value = .06
output = nodes.new('CompositorNodeComposite')
scene.node_tree.links.new(layers.outputs['Image'], glow.inputs['Image'])
scene.node_tree.links.new(glow.outputs['Image'], output.inputs['Image'])
out = HERE / 'rendered-glass'
out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'lya-glass-study.blend'))
if '--turnaround' in args:
    for angle in range(0, 360, 45):
        root.rotation_euler.z = math.radians(angle)
        scene.render.filepath = str(out / f'glass-{angle:03d}.png')
        bpy.ops.render.render(write_still=True)
elif '--render' in args or '--quick' in args:
    scene.render.filepath = str(out / ('glass-front-draft.png' if '--quick' in args else 'glass-front.png'))
    bpy.ops.render.render(write_still=True)
