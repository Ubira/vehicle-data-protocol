"""Configuration Manager — add / remove dynamic configuration (``CT=0`` / ``CT=1``).

Owns the slot table: adds and removes data-point dynamic configurations per data point,
per DCA Remote, or globally; validates slot IDs and DCA IDs; manages persistency and the
single cyclic transmission-cycle-time.

``FO_PRS_VDP_00024..00069``, ``FO_PRS_VDP_00127..00146``.
"""

from __future__ import annotations

from ..codec import Reader
from ..constants import (
    COL_SCHANGE_BIT,
    COL_SCYCLIC_BIT,
    COL_TCYCLIC_BIT,
    ErrorCode,
    ProtocolErrorCode,
    REMOVE_DCA_REM_BIT,
    REMOVE_GLOBAL_BIT,
    REMOVE_T_CYCLIC_BIT,
    SET_INIT_ACT_BIT,
    SET_PERSIST_BIT,
    SET_SEC_BIT,
    SET_TRES_MASK,
    SET_TXMODE_ON_SAMPLING_BIT,
    TimestampResolution,
)
from ..context import ServerContext
from ..core.slots import CollectionSettings, Slot, VdpSettings
from ..errors import ProtocolError, SlotError
from .base import ControlOutcome


def _bit(value: int, position: int) -> bool:
    return bool((value >> position) & 1)


def handle_add(ctx: ServerContext, reader: Reader, flags: int) -> ControlOutcome:
    """Parse and apply an *add dynamic configuration* request.

    Payload is one or more DCA groups, each: ``DCA_REM_ID`` (DDLE), ``DP_COUNT`` (DDLE),
    then ``DP_COUNT`` x DP_DCFG. A DP_DCFG is: ``VDP_SLOT_ID`` (DDLE), ``SET`` (u8),
    ``COL`` (u8), optional ``SCT`` (DDLE if cyclic), optional ``TCT`` (DDLE if tx-cyclic),
    then ``DCA_REM_DP_DCFG`` = length (DDLE) + bytes.
    """
    outcome = ControlOutcome()
    seen_slots: set[int] = set()

    if reader.at_end():
        raise ProtocolError(ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES)

    while not reader.at_end():
        dca_rem_id = reader.read_ddle()
        dp_count = reader.read_ddle()
        dca = ctx.get_dca(dca_rem_id)

        for _ in range(dp_count):
            slot_id = reader.read_ddle()
            set_byte = reader.read_u8()
            col_byte = reader.read_u8()

            cyclic = _bit(col_byte, COL_SCYCLIC_BIT)
            on_change = _bit(col_byte, COL_SCHANGE_BIT)
            tx_cyclic = _bit(col_byte, COL_TCYCLIC_BIT)

            sct_ms = reader.read_ddle() if cyclic else 0
            tct_ms = reader.read_ddle() if tx_cyclic else 0
            dca_cfg_len = reader.read_ddle()
            reader.read_bytes(dca_cfg_len)  # DCA-specific opaque configuration

            # Duplicated slot ID within this single message -> protocol error PEC=2.
            if slot_id in seen_slots:
                raise ProtocolError(ProtocolErrorCode.DUPLICATED_SLOT_ID)
            seen_slots.add(slot_id)

            # Slot ID out of the valid range -> invalid options (PEC=1).
            if not ctx.slots.is_valid_slot_id(slot_id):
                raise ProtocolError(ProtocolErrorCode.INVALID_OPTIONS)

            # --- per-slot processing errors (ACK=0) ---
            if dca is None:
                outcome.fail(SlotError(dca_rem_id, ErrorCode.UNKNOWN_DCA_REM_ID))
                continue
            if ctx.slots.exists(slot_id):
                outcome.fail(SlotError(slot_id, ErrorCode.DUPLICATE_SLOT_ID))
                continue
            if cyclic and not dca.supports_cyclic():
                outcome.fail(SlotError(slot_id, ErrorCode.CYCLIC_NOT_SUPPORTED))
                continue
            if on_change and not dca.supports_on_change():
                outcome.fail(SlotError(slot_id, ErrorCode.ONCHANGE_NOT_SUPPORTED))
                continue
            if tx_cyclic and ctx.scheduler.cyclic_tct_ms:
                outcome.fail(SlotError(slot_id, ErrorCode.CYCLIC_TX_ALREADY_SET))
                continue

            persist = _bit(set_byte, SET_PERSIST_BIT)
            if persist and not ctx.persistency.try_store(slot_id):
                outcome.fail(SlotError(slot_id, ErrorCode.PERSISTENCY_LIMIT))
                continue

            settings = VdpSettings(
                tres=TimestampResolution(set_byte & SET_TRES_MASK),
                sec=_bit(set_byte, SET_SEC_BIT),
                persist=persist,
                tx_on_sampling=_bit(set_byte, SET_TXMODE_ON_SAMPLING_BIT),
                init_act=_bit(set_byte, SET_INIT_ACT_BIT),
            )
            collection = CollectionSettings(
                on_change=on_change,
                cyclic=cyclic,
                sct_ms=sct_ms,
                tx_cyclic=tx_cyclic,
                tct_ms=tct_ms,
            )
            slot = Slot(
                slot_id=slot_id,
                dca_rem_id=dca_rem_id,
                settings=settings,
                collection=collection,
                active=settings.init_act,
            )
            now = ctx.now_ms()
            slot.next_sample_ms = now + sct_ms
            ctx.slots.add(slot)

            if tx_cyclic:
                ctx.scheduler.set_cyclic_tct(tct_ms, now)
            if slot.active:
                dca.on_activate(slot_id)

    return outcome


def handle_remove(ctx: ServerContext, reader: Reader, flags: int) -> ControlOutcome:
    """Parse and apply a *remove dynamic configuration* request.

    Flags (extended header): ``GLOBAL``, ``DCA_REM``, ``T_CYCLIC``.
    """
    outcome = ControlOutcome()
    is_global = _bit(flags, REMOVE_GLOBAL_BIT)
    per_dca = _bit(flags, REMOVE_DCA_REM_BIT)
    stop_cyclic = _bit(flags, REMOVE_T_CYCLIC_BIT)

    # Stop cyclic transmission: no payload expected.
    if stop_cyclic:
        if not reader.at_end():
            raise ProtocolError(ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES)
        ctx.scheduler.clear_cyclic_tct()
        for slot in ctx.slots.all_slots():
            slot.collection.tx_cyclic = False
        return outcome

    # Global removal: no payload expected.
    if is_global:
        if per_dca or not reader.at_end():
            raise ProtocolError(ProtocolErrorCode.INVALID_OPTIONS)
        ctx.slots.clear()
        ctx.persistency.clear()
        ctx.scheduler.clear_cyclic_tct()
        return outcome

    # A per-data-point or per-DCA removal requires a non-empty payload.
    if reader.at_end():
        raise ProtocolError(ProtocolErrorCode.INCORRECT_NUMBER_OF_BYTES)

    if per_dca:
        while not reader.at_end():
            dca_rem_id = reader.read_ddle()
            if ctx.get_dca(dca_rem_id) is None:
                outcome.fail(SlotError(dca_rem_id, ErrorCode.UNKNOWN_DCA_REM_ID))
                continue
            ctx.slots.remove_by_dca(dca_rem_id)
    else:
        while not reader.at_end():
            slot_id = reader.read_ddle()
            if not ctx.slots.remove(slot_id):
                outcome.fail(SlotError(slot_id, ErrorCode.UNKNOWN_SLOT_ID))
                continue
            ctx.persistency.remove(slot_id)

    if not ctx.slots.has_cyclic_tx():
        ctx.scheduler.clear_cyclic_tct()
    return outcome
