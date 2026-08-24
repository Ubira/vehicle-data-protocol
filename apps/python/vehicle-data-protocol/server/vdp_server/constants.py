"""Protocol constants for the VDP Server (VDP-CM Remote).

The wire-format constants (message types, command types, error codes, bit-field layout)
are shared with the client and live in :mod:`vdp_common.constants`; they are re-exported
here so existing ``vdp_server.constants`` imports keep working and the two roles cannot
drift apart. This module adds the server's **deployment / configuration defaults**, which
are role-specific and therefore not part of the shared wire format.
"""

from __future__ import annotations

from vdp_common.constants import *  # noqa: F401,F403
from vdp_common.constants import __all__ as _SHARED_ALL

# --- Deployment / configuration defaults (server-only) ------------------------
DEFAULT_MAX_SLOT_ID = 256          # VDP.maxSlotID (<= 16382) [FO_PRS_VDP_00146]
DEFAULT_MAX_MESSAGE_SIZE = 1400    # VDP.maxMessageSize (bytes) [FO_PRS_VDP_00040]
DEFAULT_MTDT_MS = 10               # Minimum Transmission Distance Time
DEFAULT_MSDT_MS = 1                # Minimum Sampling Distance Time
DEFAULT_BUFFER_LIMIT = 64          # max buffered samples before overflow

__all__ = [
    *_SHARED_ALL,
    "DEFAULT_MAX_SLOT_ID",
    "DEFAULT_MAX_MESSAGE_SIZE",
    "DEFAULT_MTDT_MS",
    "DEFAULT_MSDT_MS",
    "DEFAULT_BUFFER_LIMIT",
]
