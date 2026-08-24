"""Transmission Scheduler.

Decides *when* to emit data messages according to the active transmission modes and
enforces the **Minimum Transmission Distance Time (MTDT)** so data messages cannot flood
the bus. Maintains the 5-bit data sequence counter ``SQ_CT``.

Transmission modes (process view):

* **Cyclic** — every ``TCT`` ms (>= MTDT).
* **On-sampling** — as soon as possible after a marked slot is sampled.
* **On-request** — as soon as possible after a transmission trigger.
* **Default** — when a buffer condition (e.g. full) is reached.

``FO_PRS_VDP_00027..00029``, ``FO_PRS_VDP_00053``, ``FO_PRS_VDP_00082``,
``FO_PRS_VDP_00092..00095``.
"""

from __future__ import annotations

from ..constants import SEQ_INIT, SEQ_MAX, SEQ_MIN
from .buffer import SampleBuffer
from .datamsg import DataMessageBuilder


def _next_seq(current: int) -> int:
    return SEQ_MIN if current >= SEQ_MAX else current + 1


class TransmissionScheduler:
    def __init__(
        self,
        buffer: SampleBuffer,
        builder: DataMessageBuilder,
        mtdt_ms: int,
    ) -> None:
        self._buffer = buffer
        self._builder = builder
        self._mtdt_ms = mtdt_ms
        self._seq_ct = SEQ_INIT
        self._last_tx_ms = -(10**12)
        self._cyclic_tct_ms = 0
        self._next_cyclic_ms = 0
        self._pending_request = False  # on-request or on-sampling pending

    @property
    def seq_ct(self) -> int:
        return self._seq_ct

    @property
    def cyclic_tct_ms(self) -> int:
        return self._cyclic_tct_ms

    def set_cyclic_tct(self, tct_ms: int, now_ms: int) -> None:
        self._cyclic_tct_ms = tct_ms
        self._next_cyclic_ms = now_ms + tct_ms

    def clear_cyclic_tct(self) -> None:
        self._cyclic_tct_ms = 0
        self._next_cyclic_ms = 0

    def request_transmit(self) -> None:
        """Mark an on-request / on-sampling transmission as due."""
        self._pending_request = True

    def _mtdt_ok(self, now_ms: int) -> bool:
        return now_ms - self._last_tx_ms >= self._mtdt_ms

    def _emit(self, now_ms: int) -> bytes | None:
        if not self._buffer.has_pending():
            self._pending_request = False
            return None
        if not self._mtdt_ok(now_ms):
            return None
        samples, errors = self._buffer.drain()
        message = self._builder.build(self._seq_ct, samples, errors)
        self._seq_ct = _next_seq(self._seq_ct)
        self._last_tx_ms = now_ms
        self._pending_request = False
        return message

    def tick(self, now_ms: int) -> list[bytes]:
        """Advance time; return any data messages that must be emitted now."""
        messages: list[bytes] = []

        due = self._pending_request or self._buffer.is_full()
        if self._cyclic_tct_ms and now_ms >= self._next_cyclic_ms:
            due = True
            self._next_cyclic_ms += self._cyclic_tct_ms

        if due:
            message = self._emit(now_ms)
            if message is not None:
                messages.append(message)
        return messages
