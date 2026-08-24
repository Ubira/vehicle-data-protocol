"""Activation Controller — activate / deactivate slots (``CT=2``).

Tracks and changes the active / inactive state of each configured slot. Unknown slot IDs
yield a partial error (``ACK=0``) with error code ``0x75``.

``FO_PRS_VDP_00054``, ``FO_PRS_VDP_00055``, ``FO_PRS_VDP_00067..00080``.
"""

from __future__ import annotations

from ..codec import Reader
from ..constants import ACT_BIT, ErrorCode, ProtocolErrorCode
from ..context import ServerContext
from ..errors import ProtocolError, SlotError
from .base import ControlOutcome


def handle_activation(ctx: ServerContext, reader: Reader, flags: int) -> ControlOutcome:
    """Payload: a list of ``VDP_SLOT_ID`` (DDLE). ``ACT`` flag: 1 = activate."""
    outcome = ControlOutcome()
    activate = bool((flags >> ACT_BIT) & 1)

    if reader.at_end():
        raise ProtocolError(ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES)

    while not reader.at_end():
        slot_id = reader.read_ddle()
        slot = ctx.slots.get(slot_id)
        if slot is None:
            outcome.fail(SlotError(slot_id, ErrorCode.UNKNOWN_SLOT_ID))
            continue
        if slot.active == activate:
            continue  # already in the requested state; nothing to do
        slot.active = activate
        dca = ctx.get_dca(slot.dca_rem_id)
        if dca is None:
            continue
        if activate:
            slot.next_sample_ms = ctx.now_ms() + slot.collection.sct_ms
            dca.on_activate(slot_id)
        else:
            dca.on_deactivate(slot_id)

    return outcome
