#include "vdp/vdp_core.h"

#include <string.h>

/* ======================================================================== */
/* Slot table                                                               */
/* ======================================================================== */

void vdp_slots_init(vdp_slot_table_t *t, uint16_t max_slot_id) {
    memset(t, 0, sizeof(*t));
    t->max_slot_id = max_slot_id;
}

bool vdp_slots_valid_id(const vdp_slot_table_t *t, uint16_t slot_id) {
    return slot_id >= VDP_SLOT_ID_MIN && slot_id <= t->max_slot_id;
}

vdp_slot_t *vdp_slots_get(vdp_slot_table_t *t, uint16_t slot_id) {
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        if (t->slots[i].in_use && t->slots[i].slot_id == slot_id) {
            return &t->slots[i];
        }
    }
    return NULL;
}

vdp_slot_t *vdp_slots_add(vdp_slot_table_t *t) {
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        if (!t->slots[i].in_use) {
            memset(&t->slots[i], 0, sizeof(t->slots[i]));
            t->slots[i].in_use = true;
            return &t->slots[i];
        }
    }
    return NULL;
}

bool vdp_slots_remove(vdp_slot_table_t *t, uint16_t slot_id) {
    vdp_slot_t *slot = vdp_slots_get(t, slot_id);
    if (slot == NULL) {
        return false;
    }
    slot->in_use = false;
    return true;
}

int vdp_slots_remove_by_dca(vdp_slot_table_t *t, uint16_t dca_rem_id) {
    int removed = 0;
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        if (t->slots[i].in_use && t->slots[i].dca_rem_id == dca_rem_id) {
            t->slots[i].in_use = false;
            ++removed;
        }
    }
    return removed;
}

void vdp_slots_clear(vdp_slot_table_t *t) {
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        t->slots[i].in_use = false;
    }
}

bool vdp_slots_has_cyclic_tx(const vdp_slot_table_t *t) {
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        if (t->slots[i].in_use && t->slots[i].collection.tx_cyclic) {
            return true;
        }
    }
    return false;
}

/* ======================================================================== */
/* Sample buffer                                                            */
/* ======================================================================== */

void vdp_buffer_init(vdp_buffer_t *b) {
    memset(b, 0, sizeof(*b));
}

bool vdp_buffer_is_full(const vdp_buffer_t *b) {
    return b->sample_count >= VDP_BUFFER_CAPACITY;
}

bool vdp_buffer_add_sample(vdp_buffer_t *b, const vdp_sample_t *s) {
    if (vdp_buffer_is_full(b)) {
        if (!b->overflow_reported) {
            vdp_buffer_add_async_error(b, s->slot_id, VDP_EC_BUFFER_FULL);
            b->overflow_reported = true;
        }
        return false;
    }
    b->samples[b->sample_count++] = *s;
    return true;
}

void vdp_buffer_add_async_error(vdp_buffer_t *b, uint16_t slot_id, vdp_error_code_t code) {
    if (b->error_count >= VDP_BUFFER_CAPACITY) {
        return;
    }
    b->errors[b->error_count].slot_id = slot_id;
    b->errors[b->error_count].code = code;
    b->error_count++;
}

bool vdp_buffer_has_pending(const vdp_buffer_t *b) {
    return b->sample_count > 0u || b->error_count > 0u;
}

void vdp_buffer_clear(vdp_buffer_t *b) {
    b->sample_count = 0;
    b->error_count = 0;
    b->overflow_reported = false;
}

/* ======================================================================== */
/* Data message builder                                                     */
/* ======================================================================== */

static vdp_tres_t tres_for_slot(const vdp_slot_table_t *slots, uint16_t slot_id) {
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        if (slots->slots[i].in_use && slots->slots[i].slot_id == slot_id) {
            return slots->slots[i].settings.tres;
        }
    }
    return VDP_TRES_MS_1;
}

size_t vdp_build_data_message(const vdp_slot_table_t *slots,
                              uint8_t seq_ct,
                              const vdp_buffer_t *buffer,
                              uint8_t *out,
                              size_t out_cap) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, out_cap);

    /* Base header: MT=2, ADD=SQ_CT. */
    uint8_t header = (uint8_t)(VDP_MT_DATA | ((seq_ct & 0x1Fu) << 2));
    vdp_write_u8(&w, header);

    /* Reference timestamp: earliest buffered sample, in seconds. */
    int64_t ref_ms = 0;
    bool have_ref = false;
    for (size_t i = 0; i < buffer->sample_count; ++i) {
        if (!have_ref || buffer->samples[i].timestamp_ms < ref_ms) {
            ref_ms = buffer->samples[i].timestamp_ms;
            have_ref = true;
        }
    }
    uint32_t ref_ts_s = have_ref ? (uint32_t)(ref_ms / 1000) : 0u;
    vdp_write_u32(&w, ref_ts_s);

    int64_t previous_ms = (int64_t)ref_ts_s * 1000;
    for (size_t i = 0; i < buffer->sample_count; ++i) {
        const vdp_sample_t *s = &buffer->samples[i];
        vdp_write_ddle(&w, s->slot_id);
        uint32_t ticks = vdp_encode_rel_ticks(s->timestamp_ms, previous_ms,
                                              tres_for_slot(slots, s->slot_id));
        vdp_write_ddle(&w, ticks);
        vdp_write_ddle(&w, s->data_len);
        vdp_write_bytes(&w, s->data, s->data_len);
        previous_ms = s->timestamp_ms;
    }

    for (size_t i = 0; i < buffer->error_count; ++i) {
        const vdp_async_error_t *e = &buffer->errors[i];
        vdp_write_ddle(&w, VDP_SLOT_ID_ASYNC_ERR); /* marker 0xFF 0x7F */
        vdp_write_u8(&w, (uint8_t)e->code);
        vdp_write_ddle(&w, 2u); /* length: 2 bytes for the referenced slot id */
        vdp_write_u16(&w, e->slot_id);
    }

    if (w.overflow) {
        return 0;
    }
    return w.len;
}

/* ======================================================================== */
/* Transmission scheduler                                                   */
/* ======================================================================== */

void vdp_scheduler_init(vdp_scheduler_t *s, uint32_t mtdt_ms) {
    s->seq_ct = VDP_SEQ_INIT;
    s->last_tx_ms = (int64_t)-1000000000;
    s->mtdt_ms = mtdt_ms;
    s->cyclic_tct_ms = 0;
    s->next_cyclic_ms = 0;
    s->pending_request = false;
}

void vdp_scheduler_set_cyclic_tct(vdp_scheduler_t *s, uint32_t tct_ms, int64_t now_ms) {
    s->cyclic_tct_ms = tct_ms;
    s->next_cyclic_ms = now_ms + (int64_t)tct_ms;
}

void vdp_scheduler_clear_cyclic_tct(vdp_scheduler_t *s) {
    s->cyclic_tct_ms = 0;
    s->next_cyclic_ms = 0;
}

void vdp_scheduler_request_transmit(vdp_scheduler_t *s) {
    s->pending_request = true;
}
