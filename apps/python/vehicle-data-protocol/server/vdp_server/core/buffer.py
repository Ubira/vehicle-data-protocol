"""Core state: the sample buffer.

Aggregates acquired samples awaiting transmission and enforces a buffer limit,
reporting overflow once as an asynchronous error (``0x74``).

``FO_PRS_VDP_00096``, ``FO_PRS_VDP_00118``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import ErrorCode
from ..errors import AsyncError


@dataclass(frozen=True)
class Sample:
    """A single acquired value (DPSI)."""

    slot_id: int
    timestamp_ms: int
    data: bytes


class SampleBuffer:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._samples: list[Sample] = []
        self._async_errors: list[AsyncError] = []
        self._overflow_reported = False

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def limit(self) -> int:
        return self._limit

    def is_full(self) -> bool:
        return len(self._samples) >= self._limit

    def add_sample(self, sample: Sample) -> bool:
        """Buffer a sample. On overflow, drop it and report ``0x74`` once."""
        if self.is_full():
            if not self._overflow_reported:
                self._async_errors.append(
                    AsyncError(sample.slot_id, ErrorCode.BUFFER_FULL)
                )
                self._overflow_reported = True
            return False
        self._samples.append(sample)
        return True

    def add_async_error(self, error: AsyncError) -> None:
        self._async_errors.append(error)

    def has_pending(self) -> bool:
        return bool(self._samples) or bool(self._async_errors)

    def drain(self) -> tuple[list[Sample], list[AsyncError]]:
        """Return and clear all buffered samples and async errors, oldest first."""
        samples = sorted(self._samples, key=lambda s: s.timestamp_ms)
        errors = list(self._async_errors)
        self._samples.clear()
        self._async_errors.clear()
        self._overflow_reported = False
        return samples, errors
