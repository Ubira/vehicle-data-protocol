"""Data Message Builder.

Assembles data messages (``MT=2``) from buffered samples and asynchronous errors:

* base header ``MT=2``, ``ADD = SQ_CT`` (data sequence counter);
* reference timestamp ``REF_TS`` (uint32 seconds) (``FO_PRS_VDP_00097``);
* repeated data-point information (DPI), each either a **Data Point Sample**
  (``VDP_SLOT_ID``, relative timestamp, length, data) or an **Asynchronous Error**
  (marker ``0xFF 0x7F`` = slot 16383, error code, length, info).

Relative timestamps chain: the first DPI is relative to ``REF_TS``; each subsequent DPI
is relative to the reconstructed time of the previous sample, at the slot resolution
``TRES`` (``FO_PRS_VDP_00101``, ``FO_PRS_VDP_00042``).
"""

from __future__ import annotations

from ..codec import Writer, encode_relative_timestamp
from ..constants import (
    MessageType,
    SLOT_ID_ASYNC_ERROR,
    TimestampResolution,
)
from ..errors import AsyncError
from ..header import BaseHeader
from .buffer import Sample
from .slots import SlotTable


class DataMessageBuilder:
    def __init__(self, slots: SlotTable) -> None:
        self._slots = slots

    def _tres_for(self, slot_id: int) -> TimestampResolution:
        slot = self._slots.get(slot_id)
        return slot.settings.tres if slot else TimestampResolution.MS_1

    def build(
        self,
        seq_ct: int,
        samples: list[Sample],
        async_errors: list[AsyncError],
        ref_ts_s: int | None = None,
    ) -> bytes:
        """Serialise one data message. ``ref_ts_s`` defaults to the earliest sample."""
        writer = Writer()
        BaseHeader(MessageType.DATA, add=seq_ct).encode(writer)

        if ref_ts_s is None:
            if samples:
                ref_ts_s = min(s.timestamp_ms for s in samples) // 1000
            else:
                ref_ts_s = 0
        writer.write_u32(ref_ts_s)

        previous_ms = ref_ts_s * 1000
        for sample in samples:
            writer.write_ddle(sample.slot_id)
            rel = encode_relative_timestamp(
                sample.timestamp_ms, previous_ms, self._tres_for(sample.slot_id)
            )
            writer.write_bytes(rel)
            writer.write_ddle(len(sample.data))
            writer.write_bytes(sample.data)
            previous_ms = sample.timestamp_ms

        for error in async_errors:
            # Async errors use the reserved slot marker 16383 -> bytes 0xFF 0x7F.
            writer.write_ddle(SLOT_ID_ASYNC_ERROR)
            writer.write_u8(int(error.code))
            writer.write_ddle(len(error.info) + 2)  # 2 bytes for the referenced slot id
            writer.write_u16(error.slot_id)
            writer.write_bytes(error.info)

        return writer.to_bytes()
