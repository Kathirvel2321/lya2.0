"""Approximate familiarity and bounded RAM-only activity, never owner authority."""
import secrets
import time

from security.owner_profiles import FACE_MODEL, checked_vector


class Visitors:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.counts = dict(requests=0, limited_apps=0, blocked=0)
        self.end_presence()

    def end_presence(self):
        self.person = None
        self.until = 0
        self.pending = None

    def observe(self, vector, people):
        self.end_presence()
        if vector is None:
            return None
        vector = checked_vector(vector, FACE_MODEL)
        scores = []
        for person in people:
            samples = person['samples']
            if not 1 <= len(samples) <= 3:
                raise ValueError('Invalid face references.')
            score = min(sum(a*b for a,b in zip(vector,checked_vector(s,FACE_MODEL))) for s in samples)
            scores.append((score,person))
        scores.sort(key=lambda item:item[0],reverse=True)
        # shortcut: uncalibrated webcam familiarity, never use this as phone or private-data proof.
        if scores and scores[0][0] >= .45 and (len(scores)==1 or scores[0][0]-scores[1][0] >= .08):
            self.person = {key:scores[0][1][key] for key in
                           ('person_id','display_name','role','nickname','greeting','style')
                           if key in scores[0][1]}
            self.until = self.clock()+300
        else:
            self.pending = dict(token=secrets.token_urlsafe(20),vector=vector,until=self.clock()+600)
        return self.person

    def attach_pending(self, pending_id):
        if self.pending is not None and type(pending_id) is str and pending_id:
            self.pending['pending_id'] = pending_id

    def current(self):
        if self.clock() >= self.until:
            self.person = None
        if self.pending is not None and self.clock() >= self.pending['until']:
            self.pending = None
        return self.person

    def material(self):
        self.current()
        if self.pending is None:
            raise PermissionError('No recent unregistered face is available. No camera was opened.')
        return dict(self.pending,vector=self.pending['vector'][:])

    def record(self, kind):
        if kind not in self.counts:
            raise ValueError('Invalid activity category.')
        self.counts[kind] = min(1000,self.counts[kind]+1)

    def discard(self):
        self.counts = dict(requests=0,limited_apps=0,blocked=0)
        self.pending = None
