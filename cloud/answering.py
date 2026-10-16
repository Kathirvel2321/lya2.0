"""Shared answer guidance and bounded, volatile public conversation context.

No provider calls, inferred fact database, persistence, or authorization lives here.
Callers admit only successfully delivered public turns, after their own checks.
"""
import json
import re

MAX_EXCHANGES = 5  # Ten history messages + system + current user = gateway limit 12.
MAX_HISTORY_BYTES = 24000
MAX_REQUEST_BYTES = 60000  # Below inference.validate's 65536-byte ceiling.

GUIDANCE = """
ANSWER QUALITY:
Understand the current question using the recent conversation. Resolve phrases like
'the second one' from that context. A user's correction replaces only the specified
detail for that subject; keep other subjects and constraints separate. Prior assistant
answers can be wrong: never treat repetition or your own earlier guess as evidence.
If required context is missing, say what is unknown and ask one focused question.
Never guess a missing personal fact or silently invent an assignment, number or source.
Give a direct yes or no when supported, and explain any condition that changes it.
Distinguish supplied facts, your inference and your suggestion in natural language.
Do not agree just to please the user. Correct a false premise with a concrete reason;
do not argue merely to sound critical. For suggestions, use the user's actual goal,
constraints and situation, compare the strongest practical alternative when useful,
and explain the main tradeoff. Ask for a missing constraint if it changes the choice.
Use current reliable sources for changing facts; without them disclose the limitation.
Never invent browsing, execution, saved memory or guaranteed outcomes.
Match the user's language and requested detail. Start simple, explain unfamiliar terms,
and answer only the requested follow-up rather than repeating the whole earlier answer.
Recent chat contains at most five exchanges; earlier details may be missing. It is
temporary context, not durable memory, fresh evidence or permission.
These rules do not authorize any tool, private retrieval or external transmission.
""".strip()


def _size(messages):
    # Match the gateway's ensure_ascii=True accounting, including Tamil/emoji escapes.
    return len(json.dumps(messages).encode('utf-8'))


def bounded_history(history):
    """Copy a valid suffix of complete public exchanges; never truncate a statement."""
    if not isinstance(history, list) or len(history) % 2:
        return []
    for index, message in enumerate(history):
        if (type(message) is not dict or set(message) != {'role', 'content'}
                or message['role'] != ('user' if index % 2 == 0 else 'assistant')
                or type(message['content']) is not str or not message['content'].strip()):
            return []
    kept = [dict(message) for message in history[-2 * MAX_EXCHANGES:]]
    while kept and _size(kept) > MAX_HISTORY_BYTES:
        del kept[:2]
    return kept


def messages_for(system, history, text):
    """Retain the full current question and drop oldest whole pairs to fit transport."""
    if type(system) is not str or type(text) is not str or not text.strip():
        raise ValueError('A system prompt and current question are required.')
    head = [{'role': 'system', 'content': system + '\n\n' + GUIDANCE}]
    tail = [{'role': 'user', 'content': text}]
    kept = bounded_history(history)
    while kept and _size(head + kept + tail) > MAX_REQUEST_BYTES:
        del kept[:2]
    result = head + kept + tail
    if _size(result) > MAX_REQUEST_BYTES:
        raise ValueError('The question and evidence exceed the answer context budget.')
    return result


def completed_history(history, text, answer):
    """Return a new list; call only after successful session/cancellation validation."""
    if type(text) is not str or type(answer) is not str or not text.strip() or not answer.strip():
        raise ValueError('Only a complete question and answer may enter context.')
    return bounded_history(bounded_history(history) + [
        {'role': 'user', 'content': text}, {'role': 'assistant', 'content': answer}])


def needs_current_sources(text):
    """Conservative routing hint, not a claim of complete language understanding."""
    fresh = re.search(r'\b(latest|current|today|tonight|tomorrow|up.to.date|right now)\b', text, re.I)
    topic = re.search(r'\b(prices?|rates?|deadlines?|admissions?|requirements?|news|weather|'
                      r'schedules?|results?|laws?|regulations?|fees?|availability|specifications?)\b', text, re.I)
    return bool(fresh and topic)
