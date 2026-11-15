"""Bounded recovery policy for a stalled HID stream or worker."""
import time

class SilenceRecovery:
    def __init__(self, now):
        self.last_report = now
        self.seen = False
        self.reopened = False
        self.reconnected = False
        self.last_radio_attempt = -float("inf")

    def report(self, now):
        self.last_report = now
        self.seen = True
        self.reopened = False
        self.reconnected = False

    def action(self, now):
        age = now - self.last_report
        if age >= 8 and not self.reopened:
            self.reopened = True
            return "reopen"
        # A silent remote may simply be asleep. Try only once per silent
        # period, never more often than once every two minutes.
        if age >= 30 and self.seen and not self.reconnected and now-self.last_radio_attempt >= 120:
            self.reconnected = True
            self.last_radio_attempt = now
            return "radio"
        return None

class WorkerDeadline:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.deadline = clock() + 75
        self.stage = "startup"

    def arm(self, stage, seconds):
        self.stage = stage
        self.deadline = self.clock() + seconds

    def expired(self):
        return self.clock() > self.deadline
