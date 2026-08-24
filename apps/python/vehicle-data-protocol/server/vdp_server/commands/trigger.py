"""Trigger Handler — sampling and transmission triggers (``CT=3``).

* ``TX_TRIG=0`` with slot IDs: trigger one on-request sample of each slot.
* ``TX_TRIG=1`` without slot IDs: transmit the currently buffered samples.
* ``TX_TRIG=1`` with slot IDs: transmit buffered samples *and* trigger sampling of the
  listed slots (whose new samples may appear in a subsequent data message).

The trigger response is always sent **before** any data message.

``FO_PRS_VDP_00081..00090``, ``FO_PRS_VDP_00119``.
"""

from __future__ import annotations

from ..codec import Reader
from ..constants import ErrorCode, ProtocolErrorCode, TX_TRIG_BIT
from ..context import ServerContext
from ..errors import ProtocolError, SlotError
from .base import ControlOutcome


def handle_trigger(ctx: ServerContext, reader: Reader, flags: int) -> ControlOutcome:
    outcome = ControlOutcome()
    tx_trigger = bool((flags >> TX_TRIG_BIT) & 1)

    slot_ids: list[int] = []
    while not reader.at_end():
        slot_ids.append(reader.read_ddle())

    # A pure sampling trigger (TX_TRIG=0) must name at least one slot.
    if not tx_trigger and not slot_ids:
        raise ProtocolError(ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES)

    for slot_id in slot_ids:
        if not ctx.slots.exists(slot_id):
            outcome.fail(SlotError(slot_id, ErrorCode.UNKNOWN_SLOT_ID))
            continue
        result = ctx.sample_slot(slot_id)
        if result not in (ErrorCode.NONE, ErrorCode.SAMPLING_ERROR, ErrorCode.BUFFER_FULL):
            outcome.fail(SlotError(slot_id, result))

    if tx_trigger:
        # Emitted after the control response is sent (see the server loop).
        ctx.scheduler.request_transmit()

    return outcome
