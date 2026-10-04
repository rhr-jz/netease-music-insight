"""Memory-only sessions with absolute expiry and explicit disposal."""
import secrets
import time
from dataclasses import dataclass
from threading import RLock

from .bridge import OnlineBridge
from .storage import LocalTemporaryStorage


@dataclass
class Session:
    id: str
    bridge: OnlineBridge
    created: float
    expires: float
    expires_wall: float
    streams: int = 0


class SessionManager:
    def __init__(self, settings, jobs, service_factory=None, clock=time.monotonic):
        self.settings, self.jobs, self.service_factory, self.clock = settings, jobs, service_factory, clock
        self._sessions = {}
        self._retired = []
        self._lock = RLock()

    def create(self):
        self.reap()
        with self._lock:
            if len(self._sessions) >= self.settings.max_sessions:
                raise RuntimeError("Session capacity reached")
            storage = LocalTemporaryStorage(self.settings.temporary_root)
            try:
                bridge = OnlineBridge(storage, self.jobs, self.settings, self.service_factory, self.clock)
                now = self.clock()
                session = Session(secrets.token_urlsafe(32), bridge, now,
                                  now + self.settings.session_ttl, time.time() + self.settings.session_ttl)
                self._sessions[session.id] = session
                return session
            except Exception:
                storage.close()
                raise

    def get(self, session_id):
        if not isinstance(session_id, str) or len(session_id) > 128:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session and (self.clock() >= session.expires or
                           (session.bridge._finished_at is not None and self.clock() >= session.bridge._finished_at + self.settings.result_ttl)):
                self._sessions.pop(session_id)
            else:
                return session
        self._dispose(session)
        return None

    def drop(self, session_id):
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            self._dispose(session)

    def _dispose(self, session):
        session.bridge.dispose()
        with self._lock:
            self._retired.append(session.bridge)

    def _reap_retired(self):
        with self._lock:
            retired = list(self._retired)
        for bridge in retired:
            thread = bridge._thread
            if thread and thread.is_alive():
                continue
            if bridge._storage.close():
                with self._lock:
                    if bridge in self._retired:
                        self._retired.remove(bridge)

    def reap(self):
        with self._lock:
            identifiers = list(self._sessions)
        for identifier in identifiers:
            self.get(identifier)
        self._reap_retired()

    def close(self):
        with self._lock:
            identifiers = list(self._sessions)
        for identifier in identifiers:
            self.drop(identifier)
        with self._lock:
            retired = list(self._retired)
        for bridge in retired:
            if bridge._thread and bridge._thread.is_alive():
                bridge._thread.join(timeout=2)
        self._reap_retired()
