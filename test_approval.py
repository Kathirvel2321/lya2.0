"""Fake verifier only; no credentials, persistent grants or device collection."""
from dataclasses import replace
import unittest
from security.approval import ApprovalGate
from security.policy import Session


class ApprovalChecks(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.session = Session('admin', 'Fake', 's1', 'p1', 500)

    def gate(self, verifier=None):
        return ApprovalGate(verifier, clock=lambda: self.now, wall_clock=lambda: self.now)

    def test_missing_verifier_boolean_and_unknown_capability_deny(self):
        self.assertFalse(self.gate()('memory_read', 'show memories', self.session))
        self.assertFalse(self.gate(lambda c: True)('memory_read', 'x', self.session))
        self.assertFalse(self.gate(lambda c: c)('unknown', 'x', self.session))

    def test_exact_binding_and_replay(self):
        saved = []
        gate = self.gate(lambda c: saved.append(c) or c)
        self.assertTrue(gate('memory_read', 'show memories', self.session))
        gate.verifier = lambda c: saved[0]
        self.assertFalse(gate('memory_read', 'show memories', self.session))
        for changes in ({'parameters': 'other'}, {'action': 'memory_write'},
                        {'session': replace(self.session, person_id='p2')}, {'nonce': 'fake'}):
            gate.verifier = lambda c: replace(c, **changes)
            self.assertFalse(gate('memory_read', 'x', self.session))

    def test_expiry_invalidation_and_failure(self):
        gate = self.gate()
        def expire(c):
            self.now += 121
            return c
        gate.verifier = expire
        self.assertFalse(gate('memory_read', 'x', self.session))
        gate.verifier = lambda c: gate.invalidate() or c
        self.assertFalse(gate('memory_read', 'x', self.session))
        gate.verifier = lambda c: 1 / 0
        self.assertFalse(gate('memory_read', 'x', self.session))
        gate.verifier = lambda c: c
        self.assertTrue(gate('memory_read', 'x', self.session))
        self.assertFalse(gate('memory_read', 'x', replace(self.session, verified_until=0)))

if __name__ == '__main__':
    unittest.main()
