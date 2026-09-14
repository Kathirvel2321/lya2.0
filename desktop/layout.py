"""Pure geometry and presentation choices. Palettes are never authentication."""
from dataclasses import dataclass

PERSON_COLORS = {"guest": "#b8d5df", "admin": "#ffc26b", "family": "#bca7ff", "friend": "#78d7ad"}
TASK_COLORS = {"idle": None, "listening": "#68e5f2", "thinking": "#b69bff", "files": "#6dceff",
               "success": "#77e0b2", "approval": "#ffc26b", "error": "#ff879b"}


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    width: int
    height: int


def place_panel(orb, screen, preferred=(480, 510), gap=12):
    """Use the available monitor area, including negative monitor coordinates."""
    margin = 12
    w = max(1, min(preferred[0], screen.width - margin * 2))
    h = max(1, min(preferred[1], screen.height - margin * 2))
    left, right = screen.x + margin, screen.x + screen.width - margin
    top, bottom = screen.y + margin, screen.y + screen.height - margin
    if orb.x - gap - w >= left:
        x = orb.x - gap - w
    elif orb.x + orb.width + gap + w <= right:
        x = orb.x + orb.width + gap
    else:
        x = orb.x + orb.width // 2 - w // 2
    y = orb.y + orb.height - h
    if not (orb.x - gap - w >= left or orb.x + orb.width + gap + w <= right):
        y = orb.y - h - gap
    return Box(max(left, min(x, right - w)), max(top, min(y, bottom - h)), w, h)


def accent(person, task):
    return TASK_COLORS.get(task) or PERSON_COLORS.get(person, PERSON_COLORS["guest"])
