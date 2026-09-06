"""Versioned stage events. Callbacks receive snapshots, never mutable pipeline state."""
import copy
import time
import uuid
from contextlib import contextmanager

class Trace:
    def __init__(self, callback=None):
        self.run_id = str(uuid.uuid4())
        self.callback = callback or (lambda event: None)
        self.sequence = 0

    def emit(self, stage, status, **fields):
        self.sequence += 1
        self.callback(copy.deepcopy(dict(version="1.0", runId=self.run_id,
            sequence=self.sequence, stage=stage, status=status, timestamp=time.time(), **fields)))

    @contextmanager
    def stage(self, name, inputs=None):
        started = time.perf_counter()
        self.emit(name, "running", input=inputs)
        result = {}
        try:
            yield result
        except Exception as exc:
            self.emit(name, "failed", elapsedMs=(time.perf_counter()-started)*1000,
                      error=str(exc), **result)
            raise
        else:
            self.emit(name, "completed", elapsedMs=(time.perf_counter()-started)*1000, **result)

class TracedProvider:
    def __init__(self, provider, trace):
        self.provider, self.trace, self.calls = provider, trace, 0

    def complete(self, system, user, **kwargs):
        self.calls += 1
        self.provider.last_usage = None
        with self.trace.stage("model_call_" + str(self.calls), dict(system=system, user=user, **kwargs)) as event:
            result = self.provider.complete(system, user, **kwargs)
            event.update(output=result, usage=getattr(self.provider, "last_usage", None))
            return result
