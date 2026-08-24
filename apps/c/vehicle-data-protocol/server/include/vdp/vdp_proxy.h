/**
 * @file vdp_proxy.h
 * @brief Proxy-side (client) request builders — a test/demo helper that shares the
 *        server codec. The full client lives under apps/python/vehicle-data-protocol/client.
 */
#ifndef VDP_PROXY_H
#define VDP_PROXY_H

#include "vdp/vdp_codec.h"
#include "vdp/vdp_types.h"

/* A single data-point configuration for an add request. */
typedef struct {
    uint16_t slot_id;
    vdp_tres_t tres;
    bool sec;
    bool persist;
    bool tx_on_sampling;
    bool init_act;
    bool on_change;
    bool cyclic;
    uint32_t sct_ms;
    bool tx_cyclic;
    uint32_t tct_ms;
} vdp_proxy_dp_t;

size_t vdp_proxy_version_request(uint8_t *out, size_t cap);
size_t vdp_proxy_add_config(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                            uint16_t dca_rem_id,
                            const vdp_proxy_dp_t *dps, size_t dp_count);
size_t vdp_proxy_activation(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                            bool activate, const uint16_t *slot_ids, size_t count);
size_t vdp_proxy_trigger(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                         bool tx_trigger, const uint16_t *slot_ids, size_t count);
size_t vdp_proxy_remove_slots(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                              const uint16_t *slot_ids, size_t count);
size_t vdp_proxy_remove_all(uint8_t *out, size_t cap, uint8_t con_sq_ct);

#endif /* VDP_PROXY_H */
