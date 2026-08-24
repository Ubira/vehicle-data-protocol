"""Unit tests for the Message Codec: DDLE round-trips and relative timestamps."""

import pytest

from vdp_server.codec import (
    Reader,
    Writer,
    decode_ddle,
    decode_relative_timestamp,
    encode_ddle,
    encode_relative_timestamp,
)
from vdp_server.constants import SLOT_ID_ASYNC_ERROR, TimestampResolution
from vdp_server.errors import ProtocolError


@pytest.mark.parametrize("value", [0, 1, 127, 128, 16382, 16383, 100000, 2**32])
def test_ddle_roundtrip(value):
    assert decode_ddle(encode_ddle(value)) == value


def test_async_error_marker_encoding():
    # The reserved slot 16383 must encode to the documented bytes 0xFF 0x7F.
    assert encode_ddle(SLOT_ID_ASYNC_ERROR) == bytes((0xFF, 0x7F))


def test_ddle_omits_leading_zero_bytes():
    assert encode_ddle(0) == b"\x00"
    assert len(encode_ddle(127)) == 1
    assert len(encode_ddle(128)) == 2


def test_reader_little_endian():
    data = Writer().write_u16(0x1234).write_u32(0xAABBCCDD).to_bytes()
    reader = Reader(data)
    assert reader.read_u16() == 0x1234
    assert reader.read_u32() == 0xAABBCCDD


def test_reader_underflow_raises_protocol_error():
    with pytest.raises(ProtocolError):
        Reader(b"\x01").read_u32()


def test_relative_timestamp_roundtrip():
    tres = TimestampResolution.MS_10
    encoded = encode_relative_timestamp(1250, 1000, tres)
    ticks = decode_ddle(encoded)
    assert decode_relative_timestamp(ticks, 1000, tres) == 1250
