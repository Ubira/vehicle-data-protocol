"""Error types used by the VDP Server.

Distinguishes the three error-reporting paths from the process view:

* **Protocol errors** -> error message (``MT=3``) with a ``PEC`` code
  (``ProtocolError``). Raised for malformed / incorrectly serialised requests.
* **Processing errors** -> control response with ``ACK=0`` carrying per-slot / per-DCA
  error codes (``SlotError`` entries in a response payload).
* **Asynchronous errors** -> carried inside the next data message
  (``AsyncError``).
"""

from __future__ import annotations

from dataclasses import dataclass

from .constants import ErrorCode, ProtocolErrorCode


class ProtocolError(Exception):
    """Raised when a request is malformed and must be answered with an error message.

    ``FO_PRS_VDP_00120..00126``.
    """

    def __init__(self, pec: ProtocolErrorCode, info: bytes = b"") -> None:
        super().__init__(f"protocol error PEC={int(pec)}")
        self.pec = pec
        self.info = info


@dataclass(frozen=True)
class SlotError:
    """A per-slot or per-DCA processing error carried in an ``ACK=0`` response.

    ``FO_PRS_VDP_00017``, ``FO_PRS_VDP_00074``.
    """

    ref_id: int  # slot ID or DCA Remote ID the error refers to
    code: ErrorCode


@dataclass(frozen=True)
class AsyncError:
    """An asynchronous error embedded in a data message in place of a sample.

    ``FO_PRS_VDP_00105..00118``.
    """

    slot_id: int
    code: ErrorCode
    info: bytes = b""
