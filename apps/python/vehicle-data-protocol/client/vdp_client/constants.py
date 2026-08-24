"""Protocol constants for the VDP Client (VDP-CM Proxy).

Re-exported from the shared protocol core (:mod:`vdp_common.constants`) so the client and
the VDP Server under ``apps/python/vehicle-data-protocol/server`` use the exact same wire format
and cannot drift apart. The client has no role-specific deployment defaults to add.
"""

from __future__ import annotations

from vdp_common.constants import *  # noqa: F401,F403
from vdp_common.constants import __all__ as __all__
