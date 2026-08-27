"""The VDP Client (VDP-CM Proxy) — high-level requesting side.

Wraps the request builders and response decoders, manages the 5-bit control message
sequence counter (``CON_SQ_CT``), and records each configured slot's timestamp
resolution so inbound data messages can be decoded with correct absolute times.

Usage is transport-agnostic and single-threaded:

* call a request method (e.g. :meth:`add_config`) to send a request;
* feed every inbound message from the server to :meth:`handle`, which decodes it and
  dispatches to the optional callbacks.

``FO_PRS_VDP_00010..00015``.
"""

from __future__ import annotations

from typing import Callable, Optional

from . import messages
from .constants import SEQ_INIT, SEQ_MAX, SEQ_MIN, TimestampResolution
from .decode import (
    ControlResponse,
    DataMessage,
    Decoded,
    ErrorMessage,
    VersionResponse,
    decode_message,
)
from .messages import DpConfig
from .transport import Transport


def _next_seq(current: int) -> int:
    return SEQ_MIN if current >= SEQ_MAX else current + 1


class VdpClient:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self._con_sq_ct = SEQ_INIT
        self._slot_tres: dict[int, TimestampResolution] = {}

        # Optional callbacks; assign to observe decoded messages.
        self.on_version: Optional[Callable[[VersionResponse], None]] = None
        self.on_control_response: Optional[Callable[[ControlResponse], None]] = None
        self.on_data: Optional[Callable[[DataMessage], None]] = None
        self.on_error: Optional[Callable[[ErrorMessage], None]] = None

    # --- state -----------------------------------------------------------------
    @property
    def next_con_sq_ct(self) -> int:
        """The control sequence counter that the next control request will carry."""
        return self._con_sq_ct

    @property
    def slot_resolutions(self) -> dict[int, TimestampResolution]:
        return dict(self._slot_tres)

    def _send_control(self, message: bytes, con_sq_ct: int) -> int:
        # Advance the counter before sending so that a synchronous response (e.g. a
        # sequence-error resync over a loopback transport) is not overwritten.
        self._con_sq_ct = _next_seq(con_sq_ct)
        self._transport.send(message)
        return con_sq_ct

    # --- requests --------------------------------------------------------------
    def request_version(self) -> None:
        """Send a protocol version request (does not consume the sequence counter)."""
        self._transport.send(messages.version_request())

    def add_config(
        self,
        dca_rem_id: int,
        dps: list[DpConfig],
        *,
        tx_cyclic: bool = False,
        tct_ms: int = 0,
    ) -> int:
        """Send an add-dynamic-configuration request; returns the ``CON_SQ_CT`` used.

        ``tx_cyclic`` / ``tct_ms`` request cyclic transmission at ``tct_ms`` milliseconds
        for the remote (carried in the extended header, ``FO_PRS_VDP_00024``).
        """
        seq = self._con_sq_ct
        for dp in dps:
            self._slot_tres[dp.slot_id] = dp.tres
        message = messages.add_config(
            seq, dca_rem_id, dps, tx_cyclic=tx_cyclic, tct_ms=tct_ms
        )
        return self._send_control(message, seq)

    def remove_slots(self, slot_ids: list[int]) -> int:
        seq = self._con_sq_ct
        for slot_id in slot_ids:
            self._slot_tres.pop(slot_id, None)
        return self._send_control(messages.remove_slots(seq, slot_ids), seq)

    def remove_dcas(self, dca_ids: list[int]) -> int:
        seq = self._con_sq_ct
        return self._send_control(messages.remove_dcas(seq, dca_ids), seq)

    def remove_all(self) -> int:
        seq = self._con_sq_ct
        self._slot_tres.clear()
        return self._send_control(messages.remove_all(seq), seq)

    def remove_cyclic_tx(self) -> int:
        seq = self._con_sq_ct
        return self._send_control(messages.remove_cyclic_tx(seq), seq)

    def activate(self, slot_ids: list[int]) -> int:
        seq = self._con_sq_ct
        return self._send_control(messages.activation(seq, True, slot_ids), seq)

    def deactivate(self, slot_ids: list[int]) -> int:
        seq = self._con_sq_ct
        return self._send_control(messages.activation(seq, False, slot_ids), seq)

    def trigger_sampling(self, slot_ids: list[int]) -> int:
        """Trigger on-request sampling of ``slot_ids`` (no transmission trigger)."""
        seq = self._con_sq_ct
        return self._send_control(messages.trigger(seq, False, slot_ids), seq)

    def trigger_transmission(self, slot_ids: list[int] | None = None) -> int:
        """Trigger transmission of buffered data, optionally also sampling ``slot_ids``."""
        seq = self._con_sq_ct
        return self._send_control(messages.trigger(seq, True, slot_ids or []), seq)

    # --- inbound ---------------------------------------------------------------
    def handle(self, message: bytes) -> Decoded:
        """Decode one inbound message from the server and dispatch to callbacks."""
        decoded = decode_message(message, self._slot_tres)
        if isinstance(decoded, VersionResponse):
            if self.on_version is not None:
                self.on_version(decoded)
        elif isinstance(decoded, ControlResponse):
            if self.on_control_response is not None:
                self.on_control_response(decoded)
        elif isinstance(decoded, DataMessage):
            if self.on_data is not None:
                self.on_data(decoded)
        elif isinstance(decoded, ErrorMessage):
            # An unexpected sequence counter tells us the server's expected value; the
            # client resynchronises so the next control request is accepted.
            expected = decoded.expected_con_sq_ct
            if expected is not None:
                self._con_sq_ct = expected
            if self.on_error is not None:
                self.on_error(decoded)
        return decoded
