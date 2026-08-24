"""Interoperability tests: the client driving the real VDP Server over a loopback.

These exercise the end-to-end scenarios from ``docs/scenarios`` across both apps and
prove the shared wire format is consistent. They are skipped if the server package is
not available (see ``conftest.py``).
"""

from vdp_client import DpConfig
from vdp_client.constants import ErrorCode, ProtocolErrorCode, TimestampResolution
from vdp_client.decode import (
    ControlResponse,
    DataMessage,
    ErrorMessage,
    VersionResponse,
)


def test_s1_version(wired):
    wired.client.request_version()
    (resp,) = wired.pop_all()
    assert isinstance(resp, VersionResponse)
    assert (resp.main, resp.minor) == (0x01, 0x01)


def test_s2_add_config_ack(wired):
    wired.client.add_config(1, [DpConfig(slot_id=1, cyclic=True, sct_ms=100)])
    (resp,) = wired.pop_all()
    assert isinstance(resp, ControlResponse)
    assert resp.ack
    assert resp.con_sq_ct == 1


def test_s2_unknown_dca_nack(wired):
    wired.client.add_config(99, [DpConfig(slot_id=1)])
    (resp,) = wired.pop_all()
    assert isinstance(resp, ControlResponse)
    assert not resp.ack
    assert resp.errors[0].ref_id == 99
    assert resp.errors[0].code == ErrorCode.UNKNOWN_DCA_REM_ID


def test_s3_cyclic_sampling_roundtrip(wired):
    wired.client.add_config(
        1,
        [DpConfig(slot_id=1, cyclic=True, sct_ms=100, init_act=True,
                  tres=TimestampResolution.MS_10)],
    )
    wired.pop_all()
    for _ in range(5):
        wired.advance(100)
    wired.client.trigger_transmission()

    decoded = wired.pop_all()
    data = [d for d in decoded if isinstance(d, DataMessage)]
    assert data, "expected a data message"
    samples = data[0].samples
    assert len(samples) == 5
    # DemoDcaRemote emits an incrementing little-endian uint32 per sample.
    values = [int.from_bytes(s.data, "little") for s in samples]
    assert values == [0, 1, 2, 3, 4]
    # Timestamps reconstructed at 10 ms resolution, 100 ms apart.
    times = [s.timestamp_ms for s in samples]
    assert times == sorted(times)
    assert times[-1] - times[0] == 400


def test_s5_on_request_sampling(wired):
    wired.client.add_config(1, [DpConfig(slot_id=5)])  # no auto sampling
    wired.pop_all()
    wired.advance(500)
    wired.client.trigger_sampling([5])
    (resp,) = wired.pop_all()
    assert isinstance(resp, ControlResponse)
    assert resp.ack

    wired.client.trigger_transmission()
    data = [d for d in wired.pop_all() if isinstance(d, DataMessage)]
    assert data and data[0].samples[0].slot_id == 5


def test_s11_sequence_error_then_resync(wired):
    # Force a bad counter by advancing the client's counter out of step.
    wired.client._con_sq_ct = 5  # pretend the client lost sync
    wired.client.add_config(1, [DpConfig(slot_id=1)])
    (resp,) = wired.pop_all()
    assert isinstance(resp, ErrorMessage)
    assert resp.pec == ProtocolErrorCode.CONTROL_SEQUENCE_COUNTER
    # The client resynced to the server's expected counter (1); retry succeeds.
    assert wired.client.next_con_sq_ct == 1
    wired.client.add_config(1, [DpConfig(slot_id=1)])
    (retry,) = wired.pop_all()
    assert isinstance(retry, ControlResponse) and retry.ack


def test_s13_async_error_surfaced(wired):
    wired.client.add_config(1, [DpConfig(slot_id=3)])
    wired.pop_all()
    wired.server.report_async_error(3, ErrorCode.SAMPLING_ERROR)
    wired.client.trigger_transmission()
    data = [d for d in wired.pop_all() if isinstance(d, DataMessage)]
    assert data
    errs = data[0].async_errors
    assert errs and errs[0].slot_id == 3 and errs[0].code == ErrorCode.SAMPLING_ERROR
