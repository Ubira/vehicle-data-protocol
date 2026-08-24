#include "vdp/vdp_dca.h"

#include <string.h>

static bool demo_supports_cyclic(vdp_dca_t *self) {
    return ((vdp_demo_dca_t *)self)->cyclic;
}

static bool demo_supports_on_change(vdp_dca_t *self) {
    return ((vdp_demo_dca_t *)self)->on_change;
}

static int demo_sample(vdp_dca_t *self, uint16_t slot_id, uint8_t *out, size_t cap) {
    vdp_demo_dca_t *d = (vdp_demo_dca_t *)self;
    if (cap < 4u || slot_id >= VDP_MAX_SLOTS) {
        return -1;
    }
    uint32_t value = d->counters[slot_id]++;
    out[0] = (uint8_t)(value & 0xFFu);
    out[1] = (uint8_t)((value >> 8) & 0xFFu);
    out[2] = (uint8_t)((value >> 16) & 0xFFu);
    out[3] = (uint8_t)((value >> 24) & 0xFFu);
    return 4;
}

void vdp_demo_dca_init(vdp_demo_dca_t *d, uint16_t dca_rem_id, bool cyclic, bool on_change) {
    memset(d, 0, sizeof(*d));
    d->cyclic = cyclic;
    d->on_change = on_change;
    d->base.dca_rem_id = dca_rem_id;
    d->base.supports_cyclic = demo_supports_cyclic;
    d->base.supports_on_change = demo_supports_on_change;
    d->base.sample = demo_sample;
    d->base.on_activate = NULL;
    d->base.on_deactivate = NULL;
}
