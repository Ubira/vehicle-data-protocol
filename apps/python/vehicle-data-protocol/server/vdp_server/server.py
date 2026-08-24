"""The VDP Server (VDP-CM Remote) — top-level assembly.

Wires the codec, dispatcher, command handlers, core state and DCA Remotes together and
drives the two time-based activities from the process view:

* **Sampling** — cyclic sampling of active slots, honouring the Minimum Sampling
  Distance Time (MSDT).
* **Transmission** — the scheduler emits data messages according to the transmission
  mode, honouring the Minimum Transmission Distance Time (MTDT).

The server is single-threaded and deterministic: call :meth:`receive` to process an
inbound control/version message and :meth:`tick` to advance time. This mirrors the
"main function period" model of the Classic Platform and keeps the whole server
unit-testable without real concurrency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from .constants import (
    DEFAULT_BUFFER_LIMIT,
    DEFAULT_MAX_MESSAGE_SIZE,
    DEFAULT_MAX_SLOT_ID,
    DEFAULT_MSDT_MS,
    DEFAULT_MTDT_MS,
    ErrorCode,
)
from .context import PersistencyStore, ServerContext
from .core.buffer import SampleBuffer
from .core.datamsg import DataMessageBuilder
from .core.scheduler import TransmissionScheduler
from .core.slots import SlotTable
from .dca import DcaRemote
from .dispatch import Dispatcher
from .errors import AsyncError
from .transport import Transport


@dataclass
class ServerConfig:
    max_slot_id: int = DEFAULT_MAX_SLOT_ID
    max_message_size: int = DEFAULT_MAX_MESSAGE_SIZE
    mtdt_ms: int = DEFAULT_MTDT_MS
    msdt_ms: int = DEFAULT_MSDT_MS
    buffer_limit: int = DEFAULT_BUFFER_LIMIT
    persistency_capacity: int = 32


def _default_clock() -> int:
    return int(time.monotonic() * 1000)


class VdpServer:
    def __init__(
        self,
        transport: Transport,
        config: ServerConfig | None = None,
        clock_ms: Callable[[], int] = _default_clock,
    ) -> None:
        self._transport = transport
        self._config = config or ServerConfig()
        self._clock = clock_ms

        slots = SlotTable(self._config.max_slot_id)
        buffer = SampleBuffer(self._config.buffer_limit)
        builder = DataMessageBuilder(slots)
        scheduler = TransmissionScheduler(buffer, builder, self._config.mtdt_ms)
        self.ctx = ServerContext(
            slots=slots,
            buffer=buffer,
            scheduler=scheduler,
            builder=builder,
            clock_ms=clock_ms,
            persistency=PersistencyStore(self._config.persistency_capacity),
        )
        self._dispatcher = Dispatcher(self.ctx)

    # --- setup -----------------------------------------------------------------
    def register_dca(self, dca: DcaRemote) -> None:
        self.ctx.register_dca(dca)

    @property
    def config(self) -> ServerConfig:
        return self._config

    # --- control / version processing -----------------------------------------
    def receive(self, message: bytes) -> None:
        """Handle one inbound control/version message and emit its response(s)."""
        for out in self._dispatcher.handle(message):
            self._transport.send(out)
        # A transmission trigger requests data *after* the control response; flush it.
        self.tick()

    # --- time-driven activities ------------------------------------------------
    def tick(self, now_ms: int | None = None) -> None:
        now = self._clock() if now_ms is None else now_ms
        self._run_sampling(now)
        for message in self.ctx.scheduler.tick(now):
            self._transport.send(message)

    def _run_sampling(self, now: int) -> None:
        """Cyclic sampling of active slots, honouring MSDT."""
        for slot in self.ctx.slots.active_cyclic_slots():
            if now < slot.next_sample_ms:
                continue
            if slot.last_sample_ms >= 0 and now - slot.last_sample_ms < self._config.msdt_ms:
                continue
            self.ctx.sample_slot(slot.slot_id)
            # Schedule the next cycle relative to the intended time to avoid drift.
            slot.next_sample_ms += max(slot.collection.sct_ms, self._config.msdt_ms)
            if slot.next_sample_ms <= now:
                slot.next_sample_ms = now + slot.collection.sct_ms

    # --- asynchronous error injection (e.g. timebase loss) --------------------
    def report_async_error(self, slot_id: int, code: ErrorCode, info: bytes = b"") -> None:
        self.ctx.buffer.add_async_error(AsyncError(slot_id, code, info))
