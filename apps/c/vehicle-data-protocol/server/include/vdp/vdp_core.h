/**
 * @file vdp_core.h
 * @brief Core state: slot table, sample buffer, transmission scheduler and the data
 *        message builder (the "core state" group of the development view).
 */
#ifndef VDP_CORE_H
#define VDP_CORE_H

#include "vdp/vdp_codec.h"
#include "vdp/vdp_types.h"

/* --- Slot table (Configuration Manager / Activation Controller state) ------ */
typedef struct {
    uint16_t max_slot_id;
    vdp_slot_t slots[VDP_MAX_SLOTS];
} vdp_slot_table_t;

void vdp_slots_init(vdp_slot_table_t *t, uint16_t max_slot_id);
bool vdp_slots_valid_id(const vdp_slot_table_t *t, uint16_t slot_id);
vdp_slot_t *vdp_slots_get(vdp_slot_table_t *t, uint16_t slot_id);
vdp_slot_t *vdp_slots_add(vdp_slot_table_t *t); /* returns a free slot, or NULL */
bool vdp_slots_remove(vdp_slot_table_t *t, uint16_t slot_id);
int vdp_slots_remove_by_dca(vdp_slot_table_t *t, uint16_t dca_rem_id);
void vdp_slots_clear(vdp_slot_table_t *t);
bool vdp_slots_has_cyclic_tx(const vdp_slot_table_t *t);

/* --- Sample buffer [FO_PRS_VDP_00096], [FO_PRS_VDP_00118] ------------------ */
typedef struct {
    vdp_sample_t samples[VDP_BUFFER_CAPACITY];
    size_t sample_count;
    vdp_async_error_t errors[VDP_BUFFER_CAPACITY];
    size_t error_count;
    bool overflow_reported;
} vdp_buffer_t;

void vdp_buffer_init(vdp_buffer_t *b);
bool vdp_buffer_is_full(const vdp_buffer_t *b);
bool vdp_buffer_add_sample(vdp_buffer_t *b, const vdp_sample_t *s);
void vdp_buffer_add_async_error(vdp_buffer_t *b, uint16_t slot_id, vdp_error_code_t code);
bool vdp_buffer_has_pending(const vdp_buffer_t *b);
void vdp_buffer_clear(vdp_buffer_t *b);

/* --- Data Message Builder [FO_PRS_VDP_00091..00105] ----------------------- */
size_t vdp_build_data_message(const vdp_slot_table_t *slots,
                              uint8_t seq_ct,
                              const vdp_buffer_t *buffer,
                              uint8_t *out,
                              size_t out_cap);

/* --- Transmission Scheduler [FO_PRS_VDP_00027..00095] --------------------- */
typedef struct {
    uint8_t seq_ct;
    int64_t last_tx_ms;
    uint32_t mtdt_ms;
    uint32_t cyclic_tct_ms;
    int64_t next_cyclic_ms;
    bool pending_request;
} vdp_scheduler_t;

void vdp_scheduler_init(vdp_scheduler_t *s, uint32_t mtdt_ms);
void vdp_scheduler_set_cyclic_tct(vdp_scheduler_t *s, uint32_t tct_ms, int64_t now_ms);
void vdp_scheduler_clear_cyclic_tct(vdp_scheduler_t *s);
void vdp_scheduler_request_transmit(vdp_scheduler_t *s);

#endif /* VDP_CORE_H */
