"""Pure presentation data. These colours never classify risk or grant access."""
import json
import math
import re
from pathlib import Path

TAU = math.tau
ATTENTION = {'approval', 'high_risk', 'blocked', 'error'}
SUPPRESS = {'paused', 'voice_off', 'offline', 'cancelled', 'uncertain'}
ACTIVE_TASKS = {'coding', 'helping', 'building', 'learning', 'research', 'files', 'success'}
CONFIG_PATH = Path(__file__).resolve().parent.parent / 'visual creativity' / 'states.json'


def load_config(path=CONFIG_PATH):
    if path.stat().st_size > 32_000:
        raise ValueError('Visual configuration too large')
    config = json.loads(path.read_text(encoding='utf-8'))
    # Asset path is fixed in the adapter, never accepted from this document.
    if config['body']['geometry_changes'] is not False:
        raise ValueError('LYA body must remain fixed')
    for group in ('interaction', 'tasks'):
        for name, value in config[group].items():
            if name != 'none' and not re.fullmatch(r'#[0-9a-fA-F]{6}', value['color']):
                raise ValueError('Invalid visual colour')
    return config


def requested_task(text):
    """Optional request accent, not a claim that a tool ran or a task is safe."""
    words = set(re.findall(r'[a-z]+', text[:64000].casefold()))
    for task, terms in (
        ('coding', {'code', 'coding', 'debug', 'python', 'javascript', 'typescript'}),
        ('building', {'build', 'building', 'create', 'implement'}),
        ('learning', {'learn', 'learning', 'teach', 'explain'}),
        ('research', {'research', 'search', 'sources'}),
        ('files', {'file', 'files', 'document', 'documents'}),
        ('helping', {'help', 'helping'}),
    ):
        if words & terms:
            return task
    return 'none'


def resolve(config, interaction, task):
    phase, work = config['interaction'][interaction], config['tasks'][task]
    attention, suppress = task in ATTENTION, interaction in SUPPRESS
    voice = interaction in {'listening', 'hearing', 'thinking', 'speaking'}
    use_task = task != 'none' and (attention or (not suppress and not voice))
    return dict(interaction=interaction, task=task, phase=phase, work=work,
                color=work['color'] if use_task or (not suppress and task != 'none') else phase['color'],
                effect=work['effect'] if use_task else phase['effect'],
                moving=False if attention or suppress else task in ACTIVE_TASKS if use_task else phase['motion'],
                label=work['label'] if attention else phase['label'] + (' · ' + work['label'] if task != 'none' else ''),
                authority=False)


def should_animate(frame, visible, enabled, reduced):
    return bool(visible and enabled and not reduced and frame['animate'])


def frame(config, interaction, task, time, energy=.35, reduced=False):
    """Same normalized commands as visual creativity/effects.js; Qt is separate."""
    if not math.isfinite(time) or not math.isfinite(energy):
        raise ValueError('Invalid frame input')
    state = resolve(config, interaction, task)
    t = 0 if reduced or not state['moving'] else max(0, time)
    e, commands = max(0, min(1, energy)), []

    def path(points, alpha=.6, width=1.2, glow=4, layer='back', dash=()):
        commands.append(dict(kind='path', points=points, alpha=alpha, width=width,
                             glow=glow, layer=layer, dash=list(dash), color=state['color']))

    def point(x, y, r=.006, alpha=.9, layer='front'):
        commands.append(dict(kind='dot', x=x, y=y, r=r, alpha=alpha, layer=layer, color=state['color']))

    def orbit(rx, ry, angle, start, end, alpha=.6, width=1.2, glow=4, dash=()):
        current, layer = [], None
        for i in range(81):
            a = start + (end - start) * i / 80
            c, s, x, y = math.cos(angle), math.sin(angle), rx * math.cos(a), ry * math.sin(a)
            next_layer = 'front' if math.sin(a) >= 0 else 'back'
            p = [x * c - y * s, x * s + y * c]
            if layer and next_layer != layer:
                path(current, alpha, width, glow, layer, dash)
                current = [current[-1]]
            layer = next_layer
            current.append(p)
        if len(current) > 1:
            path(current, alpha, width, glow, layer, dash)

    lead, effect = t * .8, state['effect']
    if effect == 'aura':
        orbit(.30, .35, -.25, 0, TAU, .1, .8, 8)
    elif effect == 'quiet':
        orbit(.35, .26, 0, -1, -.35, .18, .8, 0)
    elif effect == 'orbit':
        orbit(.43, .15, -.28, 0, TAU, .32, 1, 3)
        orbit(.45, .16, -.28, lead, lead + 1.05, .95, 1.6, 6)
        orbit(.47, .17, -.28, lead - .3, lead + .7, .15, .7, 2)
    elif effect == 'ticks':
        orbit(.43, .17, .16, 0, TAU, .4, 1, 3)
        for i in range(3):
            a = lead + i * .45
            point(.43 * math.cos(a), .17 * math.sin(a), .0045, .9, 'front' if math.sin(a) > 0 else 'back')
    elif effect == 'weave':
        for strand in range(2):
            path([[.43 * math.sin(i * TAU / 100), .18 * math.sin(2 * i * TAU / 100 + strand * .45)]
                  for i in range(101)], .34, 1, 3, 'front' if strand else 'back')
        point(.43 * math.sin(lead), .18 * math.sin(2 * lead), .005, .95)
    elif effect == 'waves':
        for side in (-1, 1):
            for k in range(3):
                path([[side * (.25 + .24 * i / 50), math.sin(i / 50 * TAU * 1.3 - t * 2.4 + k * .4) *
                       (.016 + .045 * e) * math.sin(math.pi * i / 50) + (k - 1) * .037] for i in range(51)],
                     .85 if k == 1 else .22, 1.5 if k == 1 else .8, 4, 'front')
    elif effect == 'crescents':
        for side in (-1, 1):
            orbit(.36, .28, side * .18, 1.8 if side < 0 else -1.3, 4.4 if side < 0 else 1.3, .65, 1.25, 4)
            orbit(.39, .30, side * .18, 2 if side < 0 else -1.1, 4.2 if side < 0 else 1.1, .16, .7, 2)
        a = 2.8 + math.sin(lead) * .65
        point(.36 * math.cos(a), .28 * math.sin(a), .004, .65, 'back')
    elif effect == 'brackets':
        for side in (-1, 1):
            orbit(.34, .25, 0, 2.3 if side < 0 else -.85, 4 if side < 0 else .85, .42, 1, 0)
    elif effect == 'dashed':
        orbit(.35, .29, 0, .2, TAU - .8, .25, .8, 0, (5, 10))
    elif effect == 'broken':
        for start in (.1, math.pi + .1):
            orbit(.36, .28, .12, start, start + 1.7, .58, 1, 2)
    elif effect == 'code':
        path([[-.43, -.22], [-.54, -.1], [.40, .10], [.48, .20], [.33, .25]], .45, 1, 3, 'back')
        path([[-.43, -.22], [-.54, -.1], [-.24, -.04]], .85, 1.4, 4, 'front')
        for i in range(3):
            x, y = .27 + i * .028, .16
            path([[x, y], [x + .017, y], [x + .017, y + .016], [x, y + .016], [x, y]], .7, .8, 1, 'front')
        u = t * .16 % 1
        point(-.54 + u * .94, -.1 + u * .2, .004, .7, 'back')
    elif effect == 'progress':
        for i in range(7):
            orbit(.37, .29, -.25, i * TAU / 7 + .05, i * TAU / 7 + .56,
                  .9 if i == math.floor(t) % 7 else .24, 1.25, 3)
    elif effect == 'rise':
        for side in (-1, 1):
            for k in range(2):
                path([[side * (.26 + .12 * math.sin(i / 50 * math.pi)), .32 - i / 50 * .58]
                      for i in range(51)], .16 if k else .65, .7 if k else 1.25, 3, 'back')
        u = t * .20 % 1
        for side in (-1, 1):
            point(side * (.26 + .12 * math.sin(u * math.pi)), .32 - u * .58, .004, math.sin(u * math.pi) * .7, 'back')
    elif effect == 'frames':
        for k in range(2):
            x, y = .35 + k * .045, .22 + k * .025
            path([[-x, -y], [-x, -y + .22]], .22 if k else .65, 1, 2, 'back')
            path([[-x, -y], [-x + .18, -y]], .22 if k else .65, 1, 2, 'back')
            path([[x, y], [x, y - .22], [x - .18, y]], .22 if k else .65, 1, 2, 'back')
        point(.35, .22 - (t * .18 % 1) * .22, .004, .65, 'back')
    elif effect == 'boundary':
        for radius in (.34, .38):
            orbit(radius, .27, -.15, .25, 2.6, .42, 1, 2)
            orbit(radius, .27, -.15, 3.5, 5.7, .42, 1, 2)
    elif effect == 'approval':
        orbit(.41, .17, -.2, .35, TAU - .85, .7, 1.25, 3)
        point(.41 * math.cos(.35), .17 * math.sin(.35), .006, .85)
    elif effect == 'caution':
        for i in range(3):
            orbit(.38, .28, -.12, i * TAU / 3 + .16, i * TAU / 3 + 1.5, .76, 1.5, 3)
    elif effect == 'complete':
        orbit(.40, .16, -.23, 0, TAU, .65, 1.25, 3)
        orbit(.42, .17, -.23, lead, lead + .8, .88, 1.5, 4)
    else:
        raise ValueError('Unknown effect')
    return dict(state=state, commands=commands,
                body=dict(asset=config['body']['asset'], pose=config['body']['pose'], scale=1, rotation=0, tint=None),
                animate=not reduced and state['moving'])
