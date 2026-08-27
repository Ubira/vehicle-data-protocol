"""Core state: the slot table (domain model).

A **Slot** is a dynamically configured data point for the lifetime of a collection
task. It carries VDP settings (SET), collection settings (COL), its owning DCA Remote,
its activation state and its persistency flag.

``FO_PRS_VDP_00024..00069``, ``FO_PRS_VDP_00127..00146``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..constants import (
    SLOT_ID_MIN,
    TimestampResolution,
)


@dataclass
class VdpSettings:
    """Per-slot behaviour flags (SET)."""

    tres: TimestampResolution = TimestampResolution.MS_1
    sec: bool = False
    persist: bool = False
    tx_on_sampling: bool = False
    init_act: bool = False


@dataclass
class CollectionSettings:
    """Sampling behaviour (COL)."""

    on_change: bool = False   # SCHANGE
    cyclic: bool = False      # SCYCLIC
    sct_ms: int = 0           # sampling cycle time (when cyclic)


@dataclass
class Slot:
    slot_id: int
    dca_rem_id: int
    settings: VdpSettings = field(default_factory=VdpSettings)
    collection: CollectionSettings = field(default_factory=CollectionSettings)
    active: bool = False
    # runtime scheduling bookkeeping (ms of last sample / last emitted timestamp)
    last_sample_ms: int = -1
    next_sample_ms: int = 0


class SlotTable:
    """Owns all configured slots and enforces slot-ID / DCA-ID validity.

    Activation Controller and Configuration Manager operate on this table.
    """

    def __init__(self, max_slot_id: int) -> None:
        self._max_slot_id = max_slot_id
        self._slots: dict[int, Slot] = {}

    @property
    def max_slot_id(self) -> int:
        return self._max_slot_id

    def is_valid_slot_id(self, slot_id: int) -> bool:
        return SLOT_ID_MIN <= slot_id <= self._max_slot_id

    def exists(self, slot_id: int) -> bool:
        return slot_id in self._slots

    def get(self, slot_id: int) -> Slot | None:
        return self._slots.get(slot_id)

    def add(self, slot: Slot) -> None:
        self._slots[slot.slot_id] = slot

    def remove(self, slot_id: int) -> bool:
        return self._slots.pop(slot_id, None) is not None

    def remove_by_dca(self, dca_rem_id: int) -> int:
        to_drop = [sid for sid, s in self._slots.items() if s.dca_rem_id == dca_rem_id]
        for sid in to_drop:
            del self._slots[sid]
        return len(to_drop)

    def clear(self) -> None:
        self._slots.clear()

    def all_slots(self):
        return list(self._slots.values())

    def active_cyclic_slots(self):
        return [
            s
            for s in self._slots.values()
            if s.active and s.collection.cyclic and s.collection.sct_ms > 0
        ]
