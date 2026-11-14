"""Privileged executors. Every one is decorated @requires_gate.

These are the ONLY functions allowed to perform privileged changes, and
none of them is reachable from any model-facing surface: model-facing code
may construct ChangeRequest objects through Gate.request() and nothing else.

Layering rule (enforced by tests): executors import from security.gate -
gate never imports executors. Model-facing modules import gate, not these.
"""
from __future__ import annotations

from security.gate import (HIGH, MEDIUM, LOW, ChangeRequest, GateError,
                           requires_gate)


# ---- admin management ------------------------------------------------------
@requires_gate(HIGH, kind="admin_add")
def add_admin(request, *, store, name, face_templates, voice_templates,
              recovery_code):
    """Delegate to storage with the gate-approved request attached."""
    from security.protected_paths import guard_write
    guard_write(store.__file__, source="privileged executor")
    return store.register_primary_admin(
        name, face_templates, voice_templates, recovery_code)


@requires_gate(HIGH, kind="admin_remove")
def remove_admin(request, *, store, person_id):
    people = [p for p in store.list_people() if p.get("role") == "admin"
              and p.get("active")]
    if len(people) <= 1:
        raise GateError("Cannot remove the last active admin.")
    return store.remove_person(person_id)


@requires_gate(HIGH, kind="admin_role")
def change_role(request, *, store, person_id, role):
    if role == "admin":
        raise GateError("Promotion to admin uses admin_add, not role change.")
    return store.update_role(person_id, role)


# ---- credentials -------------------------------------------------------------
@requires_gate(HIGH, kind="password")
def change_password(request, *, store, person_id, old_password, new_password):
    if not store.verify_password(person_id, old_password):
        raise GateError("Current password verification failed.")
    return store.set_password(person_id, new_password)


@requires_gate(HIGH, kind="secret_key")
def change_secret_key(request, *, escalation, old_phrase, new_phrase, duress=None):
    if escalation.check_security_word(old_phrase) != "ok":
        raise GateError("The existing secret key did not verify; refusing to change it.")
    return escalation.set_security_word(new_phrase, duress)


# ---- capability grants -------------------------------------------------------
@requires_gate(HIGH, kind="capability")
def grant_capability(request, *, capability):
    """Capabilities are lines in policy sets (source code). The gate never
    edits source: instead it records the owner-approved grant and the change
    is applied manually through git by the owner. This executor validates and
    marks the request completed so the audit trail shows approval + intent."""
    from security.protected_paths import guard_write
    guard_write(__import__("security.policy", fromlist=["allowed"]).__file__,
                source="capability grant")
    return {"capability": capability,
            "note": "approved; applied manually by the owner via git"}


# ---- recovery (Bitwarden) ------------------------------------------------------
@requires_gate(HIGH, kind="recovery_enroll")
def enroll_phone_via_recovery(request, *, recovery_service, code_plain,
                              new_device_binding):
    """The ONLY privileged action a recovery code may perform."""
    return recovery_service.consume(code_plain, new_device_binding)


# ---- MEDIUM -----------------------------------------------------------------
@requires_gate(MEDIUM, kind="visitor_add")
def add_visitor(request, *, visitors, name, consent=False):
    return visitors.register(name, consent=consent)
