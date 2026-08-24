"""VDP control/version request builders — the requesting (VDP-CM Proxy) side.

These pure functions serialise the version and control (add / remove / activation /
trigger) requests that a client sends to a server. They take an explicit ``con_sq_ct``
so the caller owns the 5-bit control message sequence counter.

They are shared by:

* the real client (``vdp_client``), whose :class:`~vdp_client.client.VdpClient` wraps
  them and manages the counter; and
* the server's ``vdp_server.proxy`` test/demo helper, which drives the server without a
  separate client implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .codec import Writer
from .constants import (
    ACT_BIT,
    COL_SCHANGE_BIT,
    COL_SCYCLIC_BIT,
    COL_TCYCLIC_BIT,
    CommandType,
    MessageType,
    REMOVE_DCA_REM_BIT,
    REMOVE_GLOBAL_BIT,
    REMOVE_T_CYCLIC_BIT,
    SET_INIT_ACT_BIT,
    SET_PERSIST_BIT,
    SET_SEC_BIT,
    SET_TXMODE_ON_SAMPLING_BIT,
    TX_TRIG_BIT,
    TimestampResolution,
)
from .header import BaseHeader


def _base(mt: MessageType, add: int) -> Writer:
    writer = Writer()
    BaseHeader(mt, add=add).encode(writer)
    return writer


def version_request() -> bytes:
    """Version request (``MT=0``, no payload). Does not use the sequence counter."""
    return _base(MessageType.VERSION, 0).to_bytes()


@dataclass
class DpConfig:
    """A single data-point configuration inside an add request.

    Mirrors the server's slot ``SET``/``COL`` fields (see the shared wire format).
    """

    slot_id: int
    tres: TimestampResolution = TimestampResolution.MS_1
    sec: bool = False
    persist: bool = False
    tx_on_sampling: bool = False
    init_act: bool = False
    on_change: bool = False
    cyclic: bool = False
    sct_ms: int = 0
    tx_cyclic: bool = False
    tct_ms: int = 0
    dca_config: bytes = b""

    def _set_byte(self) -> int:
        value = int(self.tres) & 0x03
        value |= self.sec << SET_SEC_BIT
        value |= self.persist << SET_PERSIST_BIT
        value |= self.tx_on_sampling << SET_TXMODE_ON_SAMPLING_BIT
        value |= self.init_act << SET_INIT_ACT_BIT
        return value

    def _col_byte(self) -> int:
        value = self.on_change << COL_SCHANGE_BIT
        value |= self.cyclic << COL_SCYCLIC_BIT
        value |= self.tx_cyclic << COL_TCYCLIC_BIT
        return value

    def encode(self, writer: Writer) -> None:
        writer.write_ddle(self.slot_id)
        writer.write_u8(self._set_byte())
        writer.write_u8(self._col_byte())
        if self.cyclic:
            writer.write_ddle(self.sct_ms)
        if self.tx_cyclic:
            writer.write_ddle(self.tct_ms)
        writer.write_ddle(len(self.dca_config))
        writer.write_bytes(self.dca_config)


def add_config(con_sq_ct: int, dca_rem_id: int, dps: list[DpConfig]) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    writer.write_u8(int(CommandType.ADD_CONFIG))  # CT in bits [1:0]
    writer.write_ddle(dca_rem_id)
    writer.write_ddle(len(dps))
    for dp in dps:
        dp.encode(writer)
    return writer.to_bytes()


def activation(con_sq_ct: int, activate: bool, slot_ids: list[int]) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    ext = int(CommandType.ACTIVATION) | (int(activate) << ACT_BIT)
    writer.write_u8(ext)
    for slot_id in slot_ids:
        writer.write_ddle(slot_id)
    return writer.to_bytes()


def trigger(con_sq_ct: int, tx_trigger: bool, slot_ids: list[int]) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    ext = int(CommandType.TRIGGER) | (int(tx_trigger) << TX_TRIG_BIT)
    writer.write_u8(ext)
    for slot_id in slot_ids:
        writer.write_ddle(slot_id)
    return writer.to_bytes()


def remove_slots(con_sq_ct: int, slot_ids: list[int]) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    writer.write_u8(int(CommandType.REMOVE_CONFIG))
    for slot_id in slot_ids:
        writer.write_ddle(slot_id)
    return writer.to_bytes()


def remove_dcas(con_sq_ct: int, dca_ids: list[int]) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    writer.write_u8(int(CommandType.REMOVE_CONFIG) | (1 << REMOVE_DCA_REM_BIT))
    for dca_id in dca_ids:
        writer.write_ddle(dca_id)
    return writer.to_bytes()


def remove_all(con_sq_ct: int) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    writer.write_u8(int(CommandType.REMOVE_CONFIG) | (1 << REMOVE_GLOBAL_BIT))
    return writer.to_bytes()


def remove_cyclic_tx(con_sq_ct: int) -> bytes:
    writer = _base(MessageType.CONTROL, con_sq_ct)
    writer.write_u8(int(CommandType.REMOVE_CONFIG) | (1 << REMOVE_T_CYCLIC_BIT))
    return writer.to_bytes()


__all__ = [
    "DpConfig",
    "version_request",
    "add_config",
    "activation",
    "trigger",
    "remove_slots",
    "remove_dcas",
    "remove_all",
    "remove_cyclic_tx",
]
