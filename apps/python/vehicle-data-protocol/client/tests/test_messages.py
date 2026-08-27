"""Unit tests for client codec round-trips and message building."""

import pytest

from vdp_client.codec import Reader, Writer, decode_ddle, encode_ddle
from vdp_client.constants import SLOT_ID_ASYNC_ERROR, CommandType, MessageType
from vdp_client.header import decode_base_header
from vdp_client import messages


@pytest.mark.parametrize("value", [0, 1, 127, 128, 16382, 16383, 100000, 2**32])
def test_ddle_roundtrip(value):
    assert decode_ddle(encode_ddle(value)) == value


def test_async_marker_encoding():
    assert encode_ddle(SLOT_ID_ASYNC_ERROR) == bytes((0xFF, 0x7F))


def test_version_request_layout():
    msg = messages.version_request()
    header = decode_base_header(Reader(msg))
    assert header.mt == MessageType.VERSION
    assert header.add == 0
    assert len(msg) == 1


def test_add_config_layout():
    msg = messages.add_config(
        con_sq_ct=3,
        dca_rem_id=1,
        dps=[messages.DpConfig(slot_id=2, cyclic=True, sct_ms=100)],
    )
    reader = Reader(msg)
    header = decode_base_header(reader)
    assert header.mt == MessageType.CONTROL
    assert header.add == 3
    ext = reader.read_u8()
    assert CommandType((ext >> 5) & 0x07) == CommandType.ADD_CONFIG
    assert reader.read_ddle() == 1  # DCA_REM_ID
    assert reader.read_ddle() == 1  # DP_COUNT
    assert reader.read_ddle() == 2  # slot id


def test_trigger_transmission_only_layout():
    msg = messages.trigger(con_sq_ct=1, tx_trigger=True, slot_ids=[])
    reader = Reader(msg)
    decode_base_header(reader)
    ext = reader.read_u8()
    assert CommandType((ext >> 5) & 0x07) == CommandType.TRIGGER
    assert reader.at_end()  # no slot IDs
