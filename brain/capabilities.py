"""Commands exposed by the native brain. Matchers also drive its help text."""
from dataclasses import dataclass
import re
from security.policy import Session, allowed


@dataclass(frozen=True)
class Capability:
    example: str
    action: str | None = None
    exact: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()

    def matches(self, text: str) -> bool:
        return text in self.exact or any(text.startswith(prefix) for prefix in self.prefixes)


COMMANDS = {
    "help": Capability("what can you do", exact=("brain help", "help", "what can you do")),
    "time": Capability("what time is it / date", exact=
                       ("time", "what time is it", "date", "what date is it", "day")),
    "identity": Capability("who am i", exact=("who am i",)),
    "status": Capability("brain status", exact=("brain status",)),
    "privacy_on": Capability("private mode", exact=
                             ("private mode", "private mode on", "go private")),
    "privacy_off": Capability("public mode", exact=
                              ("public mode", "private mode off", "go public")),
    "privacy_status": Capability("privacy status", exact=("privacy status",)),
    "stop": Capability("stop / sleep", exact=("stop", "sleep", "cancel", "forget session")),
    "device_status": Capability("device status / battery status", "device_status", exact=
                                ("device status", "battery status", "memory usage", "disk space")),
    "volume": Capability("volume up / volume down / mute volume", "volume", exact=("volume", "mute"),
                         prefixes=("volume ",)),
    "note_save": Capability("remember short label = note (or session / long / until / permanent)",
                            "memory_write", prefixes=("remember ",)),
    "note_correct": Capability("correct label = replacement", "memory_write", prefixes=("correct ",)),
    "note_forget": Capability("forget label", "memory_forget", prefixes=("forget ",)),
    "note_recall": Capability("recall words / show memories / show graph", "memory_read", exact=
                              ("show memories", "show graph"), prefixes=("recall ",)),
    "note_link": Capability("link 1 depends_on 2", "memory_write", prefixes=("link ",)),
    "task_add": Capability("task add <what to do>", "tasks", prefixes=("task add ",)),
    "task_list": Capability("tasks / tasks all", "tasks", exact=("tasks", "tasks all", "show tasks")),
    "task_done": Capability("task done <number>", "tasks", prefixes=("task done ",)),
    "council": Capability("council: important question (local model required)", "council",
                          prefixes=("council:",)),
}


def volume_action(text: str) -> str | None:
    """Recognize a whole explicit request, never a quoted/negated mention."""
    text = " ".join(re.sub(r"[.,!?]", " ", text.casefold()).split())
    prefix = (r"(?:(?:hey )?(?:lya|laya|leya) )?"
              r"(?:(?:your|the|my) volume (?:is )?(?:so |too )?(?:low|down|high|loud) )?"
              r"(?:please )?(?:(?:can|could|would|will) you )?(?:please )?")
    noun = r"(?:(?:the|my|your|system|device|speaker) )?volume"
    suffix = r"(?: (?:on|in) (?:this|my|the) (?:device|computer|laptop))?(?: for me)?(?: please)?"
    directions = {
        "up": (rf"(?:turn |put |bring )?{noun} (?:up|high|higher|louder)",
               rf"(?:increase|raise) {noun}", rf"turn up {noun}",
               rf"(?:make|set) {noun} (?:high|higher|up|louder)"),
        "down": (rf"(?:turn |put |bring )?{noun} (?:down|low|lower|quieter)",
                 rf"(?:lower|decrease|reduce) {noun}", rf"turn down {noun}",
                 rf"(?:make|set) {noun} (?:low|lower|down|quieter)"),
        "mute": (rf"mute(?: {noun})?", rf"{noun} mute"),
    }
    for action, patterns in directions.items():
        if any(re.fullmatch(prefix + pattern + suffix, text) for pattern in patterns):
            return action
    return None


def matches(name: str, text: str) -> bool:
    return COMMANDS[name].matches(text)


def help_text(*, verified: bool, session: Session) -> str:
    available = [item.example for item in COMMANDS.values()
                 if item.action is None or verified and allowed(session, item.action, phone_approved=True)]
    lines = ["Connected brain commands:", *("• " + item for item in available)]
    if not verified:
        lines.append("Device readings and volume controls require a verified session; personal memory needs a verified admin and approval.")
    elif allowed(session, "memory_read", phone_approved=True):
        lines.append("Personal memory and council requests still require approval; model availability is checked when used.")
    lines.append("Model replies are not automatically saved as facts.")
    return "\n".join(lines)
