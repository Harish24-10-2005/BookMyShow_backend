from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict

from app.models.entities import SeatStatus
from app.models.schemas import Seat


class LockMeta(TypedDict):
    show_id: str
    seats: List[str]
    expiry: float


class InMemoryLockManager:
    """Simple in-memory seat lock manager with TTL. Thread-safe within one process."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._locks: Dict[str, Dict[str, float]] = {}  # show_id -> seat_id -> expiry ts
        self._lock_id_to_meta: Dict[str, LockMeta] = {}
        self._lock = threading.Lock()

    def _purge_expired(self) -> None:
        now = time.time()
        for lock_id, meta in list(self._lock_id_to_meta.items()):
            if meta["expiry"] < now:
                self.release_by_lock_id(lock_id)

    def purge_expired(self) -> None:
        """Public helper to drop stale locks when listing seats."""
        with self._lock:
            self._purge_expired()

    def lock(self, show_id: str, seat_ids: List[str]) -> tuple[str, datetime]:
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        expiry_ts = expires_at.timestamp()
        lock_id = str(uuid.uuid4())
        with self._lock:
            self._purge_expired()
            show_locks = self._locks.setdefault(show_id, {})
            conflicts = [seat for seat in seat_ids if show_locks.get(seat, 0) > time.time()]
            if conflicts:
                raise ValueError(f"Seats already locked or booked: {conflicts}")
            for seat in seat_ids:
                show_locks[seat] = expiry_ts
            self._lock_id_to_meta[lock_id] = {"show_id": show_id, "seats": seat_ids, "expiry": expiry_ts}
        return lock_id, expires_at

    def release_by_lock_id(self, lock_id: str) -> None:
        with self._lock:
            meta = self._lock_id_to_meta.pop(lock_id, None)
            if not meta:
                return
            show_locks = self._locks.get(meta["show_id"], {})
            for seat_id in meta["seats"]:
                show_locks.pop(seat_id, None)

    def is_locked(self, show_id: str, seat_id: str, lock_id: Optional[str]) -> bool:
        with self._lock:
            show_locks = self._locks.get(show_id, {})
            expiry_ts = show_locks.get(seat_id, 0)
            if expiry_ts < time.time():
                return False
            # If lock_id is provided, ensure it matches
            if lock_id is None:
                return True
            meta = self._lock_id_to_meta.get(lock_id)
            if not meta or meta["show_id"] != show_id:
                return False
            return seat_id in meta["seats"]

    def extend(self, lock_id: str, extra_seconds: int) -> Optional[datetime]:
        with self._lock:
            meta = self._lock_id_to_meta.get(lock_id)
            if not meta:
                return None
            new_expiry = time.time() + extra_seconds
            show_locks = self._locks.get(meta["show_id"], {})
            for seat_id in meta["seats"]:
                if seat_id in show_locks:
                    show_locks[seat_id] = new_expiry
            meta["expiry"] = new_expiry
            return datetime.utcfromtimestamp(new_expiry)


def apply_lock_state_to_seats(show_id: str, seats: List[Seat], lock_manager: InMemoryLockManager) -> List[Seat]:
    updated = []
    for seat in seats:
        if lock_manager.is_locked(show_id, seat.id, None) and seat.status == SeatStatus.available:
            updated.append(Seat(**{**seat.model_dump(), "status": SeatStatus.locked}))
        else:
            updated.append(seat)
    return updated
