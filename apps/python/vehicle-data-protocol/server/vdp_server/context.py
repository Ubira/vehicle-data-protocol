"""Mutable server state shared by the command handlers.

Bundles the core state (slot table, sample buffer, transmission scheduler, data message
builder), the registered DCA Remotes, the clock, and the persistency store so handlers
can be written as small functions operating on a single context object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .constants import ErrorCode
from .core.buffer import SampleBuffer
from .core.datamsg import DataMessageBuilder
from .core.scheduler import TransmissionScheduler
from .core.slots import SlotTable
from .dca import DcaRemote


@dataclass
class PersistencyStore:
    """Very small model of non-volatile storage for ``PERSIST=1`` configurations.

    Storage exhaustion is reported as error ``0x78`` (``FO_PRS_VDP_00052``).
    """

    capacity: int = 32
    _used: set[int] = field(default_factory=set)

    def try_store(self, slot_id: int) -> bool:
        if slot_id in self._used:
            return True
        if len(self._used) >= self.capacity:
            return False
        self._used.add(slot_id)
        return True

    def remove(self, slot_id: int) -> None:
        self._used.discard(slot_id)

    def clear(self) -> None:
        self._used.clear()


@dataclass
class ServerContext:
    slots: SlotTable
    buffer: SampleBuffer
    scheduler: TransmissionScheduler
    builder: DataMessageBuilder
    clock_ms: Callable[[], int]
    dcas: dict[int, DcaRemote] = field(default_factory=dict)
    persistency: PersistencyStore = field(default_factory=PersistencyStore)

    def register_dca(self, dca: DcaRemote) -> None:
        self.dcas[dca.dca_rem_id] = dca

    def get_dca(self, dca_rem_id: int) -> DcaRemote | None:
        return self.dcas.get(dca_rem_id)

    def now_ms(self) -> int:
        return self.clock_ms()

    def sample_slot(self, slot_id: int) -> ErrorCode:
        """Drive one sample of ``slot_id`` through its DCA and buffer the result.

        Returns ``ErrorCode.NONE`` on success, otherwise the async error code that was
        recorded (``0x02`` sampling error / ``0x74`` buffer full).
        """
        from .core.buffer import Sample  # local import to avoid a cycle
        from .errors import AsyncError

        slot = self.slots.get(slot_id)
        if slot is None:
            return ErrorCode.UNKNOWN_SLOT_ID
        dca = self.get_dca(slot.dca_rem_id)
        if dca is None:
            return ErrorCode.UNKNOWN_DCA_REM_ID
        data = dca.sample(slot_id)
        now = self.now_ms()
        slot.last_sample_ms = now
        if data is None:
            self.buffer.add_async_error(AsyncError(slot_id, ErrorCode.SAMPLING_ERROR))
            return ErrorCode.SAMPLING_ERROR
        stored = self.buffer.add_sample(Sample(slot_id, now, data))
        if not stored:
            return ErrorCode.BUFFER_FULL
        if slot.settings.tx_on_sampling:
            self.scheduler.request_transmit()
        return ErrorCode.NONE
