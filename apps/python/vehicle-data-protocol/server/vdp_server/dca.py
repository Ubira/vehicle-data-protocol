"""DCA Remote adapter interface.

The boundary through which the server activates / deactivates and triggers sampling and
receives samples. DCA Remotes implement the *sampling modes*; the server implements the
*protocol* and *transmission*. This decoupling is the central design principle of the
standard (process view, standards chapter 8).

``FO_PRS_VDP_00085``.
"""

from __future__ import annotations

import itertools
from abc import ABC, abstractmethod


class DcaRemote(ABC):
    """A Data Class Adapter that samples one class of data points."""

    def __init__(self, dca_rem_id: int) -> None:
        self.dca_rem_id = dca_rem_id

    @abstractmethod
    def supports_cyclic(self) -> bool:
        """Whether this DCA can perform cyclic sampling (``SCYCLIC``)."""

    @abstractmethod
    def supports_on_change(self) -> bool:
        """Whether this DCA can perform on-change sampling (``SCHANGE``)."""

    @abstractmethod
    def sample(self, slot_id: int) -> bytes | None:
        """Acquire one value for ``slot_id``.

        Returns the raw data bytes, or ``None`` if sampling failed (the server then
        emits an asynchronous sampling error ``0x02``).
        """

    def on_activate(self, slot_id: int) -> None:  # optional hook
        """Called when a slot owned by this DCA becomes active."""

    def on_deactivate(self, slot_id: int) -> None:  # optional hook
        """Called when a slot owned by this DCA becomes inactive."""


class DemoDcaRemote(DcaRemote):
    """A self-contained DCA Remote that produces a monotonically increasing counter.

    Useful for demonstrations and integration tests without real hardware.
    """

    def __init__(self, dca_rem_id: int, *, cyclic: bool = True, on_change: bool = True):
        super().__init__(dca_rem_id)
        self._cyclic = cyclic
        self._on_change = on_change
        self._counters: dict[int, itertools.count] = {}

    def supports_cyclic(self) -> bool:
        return self._cyclic

    def supports_on_change(self) -> bool:
        return self._on_change

    def sample(self, slot_id: int) -> bytes | None:
        counter = self._counters.setdefault(slot_id, itertools.count())
        value = next(counter)
        return value.to_bytes(4, "little")
