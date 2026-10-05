"""Grounded, deliberately narrow answers from local camera detections."""
import re

from vision.scan import CLASSES

LABELS = {name.replace('_', ' ') for name in CLASSES}
ALIASES = {'phone': 'cell phone', 'mobile': 'cell phone', 'mobile phone': 'cell phone',
           'sofa': 'couch', 'monitor': 'tv', 'computer': 'laptop', 'people': 'person'}
PERSON_VIEW = re.compile(r'\b(?:see|look at) me\b')


def question_text(question):
    text = ' '.join(question.casefold().split())
    text = re.sub(r'\b(?:lya|liya)\b[, ]*', '', text).removeprefix('hey ').strip(' ,.!?')
    return re.sub(r"^what['’]s\b", 'what is', text)


def camera_control(question):
    """Recognize a direct camera request, not a mention, negation or settings page."""
    match = re.match(r'^(?:please )?(?:(?:can|could|would|will) you )?(?:please )?'
                     r'(open|start|turn on|close|stop|turn off) (?:the |my )?camera'
                     r'(?=$|[,.!?;]| (?:and|so|to|now|please)\b)', question_text(question))
    if match:
        return 'open' if match[1] in ('open', 'start', 'turn on') else 'close'
    return None


def reference_kind(question):
    text = question_text(question)
    if re.fullmatch(r'(?:can you (?:tell me|identify) |tell me )?(?:what|which)(?: object)? (?:am i|i am) pointing (?:at|to)', text):
        return 'pointing'
    if text in ('what am i holding', 'what is in my hand', 'what object am i holding'):
        return 'holding'
    if text in ('what is this', 'what is that', 'what is this object', 'what is that object',
                'what object is this', 'what object is that', 'identify this object',
                'can you identify this object', 'can you tell me what this is'):
        return 'this'
    if text in ('what object is near me', 'what is the object near me', 'what objects are near me'):
        return 'nearby'
    return None


def is_visual_question(question, camera_active=False):
    text = question_text(question)
    control = camera_control(question)
    if control == 'close':
        return False
    if PERSON_VIEW.search(text) and (control == 'open' or re.match(
            r'^(?:please )?(?:(?:can|could|would|do) you )?(?:see|look at) me\b', text)):
        return True
    kind = reference_kind(question)
    if kind:
        # Bare "this" needs an existing view; it must not activate a camera while
        # the owner may be asking about something in text or a project document.
        return camera_active or kind != 'this' or 'object' in text
    if text.rstrip('?! .') in ('what do you see', 'do you see anything', 'is anyone there'):
        return True
    cue = any(phrase in text for phrase in ('can you see', 'do you see', 'where is my',
                                            'find my', 'in front of you', 'in the camera'))
    subject = any(re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', text)
                  for label in LABELS | set(ALIASES) | {'pen', 'pencil', 'anyone', 'someone', 'suspicious'})
    return cue and subject


def answer_scene(question, scene, fresh=True):
    if not scene or not fresh:
        return 'I need a current camera view. Start live view and ask again.'
    if not scene.get('ready', True):
        return 'I can see the live feed. Object analysis is still catching up; ask again in a moment.'
    text = question_text(question)
    if not text:
        return 'Ask what I can see, whether someone is present, or where a visible object is.'
    faces = len(scene.get('faces', []))
    objects = scene.get('objects', [])
    kind = reference_kind(question)
    if kind:
        from vision.hands import referenced_object
        item, clarification = referenced_object(scene, kind)
        if item is None:
            return clarification
        context = ('Along your pointing direction' if kind == 'pointing' else
                   'Near your hand' if kind == 'holding' else 'In the camera view')
        return f"{context}, I see a possible {item['label']}."
    people = max(faces, sum(item['label'] == 'person' for item in objects))
    if any(word in text for word in ('suspicious', 'dangerous', 'intruder', 'stranger')):
        presence = f'I can see {people} person(s).' if people else 'I cannot confirm a person in this view.'
        return presence + ' I cannot judge identity or intent from appearance. Check the scene yourself if safety matters.'
    if PERSON_VIEW.search(text) or any(word in text for word in ('anyone', 'somebody', 'someone', 'person', 'people', 'human', 'face')):
        return f'I can see {people} person(s) in the current view. I cannot identify or authorize them.' if people else \
               'I cannot confirm a person in the current view. Someone may be outside the frame.'
    matches = []
    for label in sorted(LABELS | set(ALIASES), key=len, reverse=True):
        if re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', text):
            matches.append(ALIASES.get(label, label))
    if matches:
        target = matches[0]
        found = [item for item in objects if item['label'] == target]
        if not found:
            return f'I do not detect a {target} in the current view. It may be outside the frame or too small.'
        item = max(found, key=lambda entry: entry['confidence'])
        x1, y1, x2, y2 = item['box']
        center_x = (x1 + x2) / 2 / scene['width']
        center_y = (y1 + y2) / 2 / scene['height']
        side = 'left' if center_x < 0.36 else 'right' if center_x > 0.64 else 'middle'
        height = 'top' if center_y < 0.33 else 'bottom' if center_y > 0.67 else 'center'
        return f'I see a possible {target} near the {height} {side} of the camera view.'
    if 'pen' in text or 'pencil' in text:
        return 'I cannot reliably find a pen yet. The current small detector has no pen class, so I will not guess.'
    labels = [item['label'] for item in objects[:5]]
    return ('I can see ' + ', '.join(labels) + '. Identity is unknown.') if labels else \
           'I do not confidently identify an object in the current view. Try more light or a closer angle.'
