"""Tests for the high-level VdpClient behaviour (sequence counter, state, resync)."""

from vdp_client.codec import Reader
from vdp_client.constants import ProtocolErrorCode, TimestampResolution
from vdp_client.decode import ErrorMessage
from vdp_client.header import decode_base_header
from vdp_client import DpConfig


def _con_sq_ct(message: bytes) -> int:
    return decode_base_header(Reader(message)).add


def test_control_requests_increment_sequence_counter(client_loopback):
    c = client_loopback.client
    assert c.add_config(1, [DpConfig(slot_id=1)]) == 1
    assert c.activate([1]) == 2
    assert c.deactivate([1]) == 3
    seqs = [_con_sq_ct(m) for m in client_loopback.sent]
    assert seqs == [1, 2, 3]
    assert c.next_con_sq_ct == 4


def test_sequence_counter_wraps_after_31(client_loopback):
    c = client_loopback.client
    for _ in range(31):
        c.trigger_transmission()
    assert c.next_con_sq_ct == 1  # wrapped 31 -> 1


def test_version_request_does_not_consume_counter(client_loopback):
    c = client_loopback.client
    c.request_version()
    assert c.next_con_sq_ct == 1
    assert _con_sq_ct(client_loopback.sent[0]) == 0


def test_add_config_records_slot_resolution(client_loopback):
    c = client_loopback.client
    c.add_config(1, [DpConfig(slot_id=7, tres=TimestampResolution.MS_100)])
    assert c.slot_resolutions[7] == TimestampResolution.MS_100
    c.remove_slots([7])
    assert 7 not in c.slot_resolutions


def test_client_resyncs_on_sequence_error(client_loopback):
    c = client_loopback.client
    # Simulate the server rejecting with the expected counter = 9.
    from vdp_client.codec import Writer
    from vdp_client.constants import MessageType

    err = (
        Writer()
        .write_u8(int(MessageType.ERROR))
        .write_u8(int(ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER))
        .write_u8(9)
        .to_bytes()
    )
    decoded = c.handle(err)
    assert isinstance(decoded, ErrorMessage)
    assert c.next_con_sq_ct == 9  # resynchronised to the server's expectation
