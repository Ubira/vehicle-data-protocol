"""Proxy-side request builders (test / demo helper).

These functions build the *client* (VDP-CM Proxy) requests that the server consumes, so
the demo and tests can drive the server without a separate client implementation. They
are the same builders the real client uses; they live in :mod:`vdp_common.builders` and
are re-exported here under ``vdp_server.proxy``. The real client lives under
``apps/vehicle-data-protocol/client``.
"""

from __future__ import annotations

from vdp_common.builders import (
    DpConfig,
    activation,
    add_config,
    remove_all,
    remove_cyclic_tx,
    remove_dcas,
    remove_slots,
    trigger,
    version_request,
)

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
