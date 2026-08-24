/**
 * @file vdp_dca.h
 * @brief DCA Remote adapter interface.
 *
 * The boundary through which the server activates/deactivates and triggers sampling and
 * receives samples. DCA Remotes implement the sampling modes; the server implements the
 * protocol and transmission (FO_PRS_VDP_00085). Implemented with function pointers so
 * concrete DCAs can be plugged in without touching the server.
 */
#ifndef VDP_DCA_H
#define VDP_DCA_H

#include "vdp/vdp_types.h"

typedef struct vdp_dca vdp_dca_t;

struct vdp_dca {
    uint16_t dca_rem_id;
    bool (*supports_cyclic)(vdp_dca_t *self);
    bool (*supports_on_change)(vdp_dca_t *self);
    /* Acquire one value for slot_id into out (<= cap bytes).
       Returns the number of bytes written, or -1 on a sampling failure. */
    int (*sample)(vdp_dca_t *self, uint16_t slot_id, uint8_t *out, size_t cap);
    void (*on_activate)(vdp_dca_t *self, uint16_t slot_id);   /* optional, may be NULL */
    void (*on_deactivate)(vdp_dca_t *self, uint16_t slot_id); /* optional, may be NULL */
};

/* A self-contained demo DCA that emits a per-slot monotonically increasing counter. */
typedef struct {
    vdp_dca_t base;
    bool cyclic;
    bool on_change;
    uint32_t counters[VDP_MAX_SLOTS];
} vdp_demo_dca_t;

void vdp_demo_dca_init(vdp_demo_dca_t *d, uint16_t dca_rem_id, bool cyclic, bool on_change);

#endif /* VDP_DCA_H */
