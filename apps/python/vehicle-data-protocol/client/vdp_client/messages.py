"""Request builders — the client (VDP-CM Proxy) requesting side.

The version and control (add / remove / activation / trigger) request builders and the
:class:`DpConfig` data-point configuration are shared with the server's test/demo proxy;
they live in :mod:`vdp_common.builders` and are re-exported here under
``vdp_client.messages``. :class:`~vdp_client.client.VdpClient` wraps them and manages the
control sequence counter.
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
