#include "vdp/vdp_server.h"

#include <string.h>

/* ======================================================================== */
/* Configuration                                                            */
/* ======================================================================== */

vdp_config_t vdp_config_default(void) {
    vdp_config_t c;
    c.max_slot_id = 256;
    c.max_message_size = VDP_MAX_MESSAGE_SIZE;
    c.mtdt_ms = 10;
    c.msdt_ms = 1;
    c.persistency_capacity = 32;
    return c;
}

/* ======================================================================== */
/* Helpers                                                                  */
/* ======================================================================== */

static uint8_t next_seq(uint8_t current) {
    return (current >= VDP_SEQ_MAX) ? VDP_SEQ_MIN : (uint8_t)(current + 1);
}

static int64_t server_now(const vdp_server_t *srv) {
    return srv->clock(srv->clock_user);
}

static void server_send(vdp_server_t *srv, const uint8_t *data, size_t len) {
    if (len == 0u || len > srv->config.max_message_size) {
        return; /* build failure or would exceed maxMessageSize -> drop */
    }
    srv->send(srv->send_user, data, len);
}

static vdp_dca_t *server_get_dca(vdp_server_t *srv, uint16_t dca_rem_id) {
    for (size_t i = 0; i < srv->dca_count; ++i) {
        if (srv->dcas[i]->dca_rem_id == dca_rem_id) {
            return srv->dcas[i];
        }
    }
    return NULL;
}

/* Drive one sample of slot_id through its DCA and buffer the result. */
static vdp_error_code_t server_sample_slot(vdp_server_t *srv, uint16_t slot_id) {
    vdp_slot_t *slot = vdp_slots_get(&srv->slots, slot_id);
    if (slot == NULL) {
        return VDP_EC_UNKNOWN_SLOT_ID;
    }
    vdp_dca_t *dca = server_get_dca(srv, slot->dca_rem_id);
    if (dca == NULL) {
        return VDP_EC_UNKNOWN_DCA_REM_ID;
    }
    vdp_sample_t sample;
    memset(&sample, 0, sizeof(sample));
    int n = dca->sample(dca, slot_id, sample.data, VDP_MAX_SAMPLE_DATA);
    int64_t now = server_now(srv);
    slot->last_sample_ms = now;
    if (n < 0) {
        vdp_buffer_add_async_error(&srv->buffer, slot_id, VDP_EC_SAMPLING_ERROR);
        return VDP_EC_SAMPLING_ERROR;
    }
    sample.slot_id = slot_id;
    sample.timestamp_ms = now;
    sample.data_len = (uint8_t)n;
    if (!vdp_buffer_add_sample(&srv->buffer, &sample)) {
        return VDP_EC_BUFFER_FULL;
    }
    if (slot->settings.tx_on_sampling) {
        vdp_scheduler_request_transmit(&srv->scheduler);
    }
    return VDP_EC_NONE;
}

/* ======================================================================== */
/* Control-response outcome                                                 */
/* ======================================================================== */

typedef struct {
    bool ack;
    struct {
        uint16_t ref_id;
        uint8_t code;
    } errs[VDP_MAX_SLOTS];
    size_t err_count;
} vdp_outcome_t;

static void outcome_init(vdp_outcome_t *o) {
    o->ack = true;
    o->err_count = 0;
}

static void outcome_fail(vdp_outcome_t *o, uint16_t ref_id, vdp_error_code_t code) {
    o->ack = false;
    if (o->err_count < VDP_MAX_SLOTS) {
        o->errs[o->err_count].ref_id = ref_id;
        o->errs[o->err_count].code = (uint8_t)code;
        o->err_count++;
    }
}

/* Handlers return -1 on success (outcome filled) or a vdp_pec_t on protocol error. */
#define HANDLER_OK (-1)

/* ======================================================================== */
/* Command handlers                                                         */
/* ======================================================================== */

static int handle_add(vdp_server_t *srv, vdp_reader_t *r, uint8_t ext, vdp_outcome_t *o) {
    (void)ext;
    uint16_t seen[VDP_MAX_SLOTS];
    size_t seen_count = 0;

    if (vdp_reader_at_end(r)) {
        return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
    }

    while (!vdp_reader_at_end(r)) {
        uint16_t dca_rem_id = (uint16_t)vdp_read_ddle(r);
        uint32_t dp_count = vdp_read_ddle(r);
        vdp_dca_t *dca = server_get_dca(srv, dca_rem_id);

        for (uint32_t k = 0; k < dp_count; ++k) {
            uint16_t slot_id = (uint16_t)vdp_read_ddle(r);
            uint8_t set_byte = vdp_read_u8(r);
            uint8_t col_byte = vdp_read_u8(r);

            bool cyclic = (col_byte >> VDP_COL_SCYCLIC_BIT) & 1u;
            bool on_change = (col_byte >> VDP_COL_SCHANGE_BIT) & 1u;
            bool tx_cyclic = (col_byte >> VDP_COL_TCYCLIC_BIT) & 1u;

            uint32_t sct_ms = cyclic ? vdp_read_ddle(r) : 0u;
            uint32_t tct_ms = tx_cyclic ? vdp_read_ddle(r) : 0u;
            uint32_t dca_cfg_len = vdp_read_ddle(r);
            (void)vdp_read_bytes(r, dca_cfg_len);

            if (r->error) {
                return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
            }

            for (size_t i = 0; i < seen_count; ++i) {
                if (seen[i] == slot_id) {
                    return VDP_PEC_DUPLICATED_SLOT_ID;
                }
            }
            if (seen_count < VDP_MAX_SLOTS) {
                seen[seen_count++] = slot_id;
            }

            if (!vdp_slots_valid_id(&srv->slots, slot_id)) {
                return VDP_PEC_INVALID_OPTIONS;
            }

            if (dca == NULL) {
                outcome_fail(o, dca_rem_id, VDP_EC_UNKNOWN_DCA_REM_ID);
                continue;
            }
            if (vdp_slots_get(&srv->slots, slot_id) != NULL) {
                outcome_fail(o, slot_id, VDP_EC_DUPLICATE_SLOT_ID);
                continue;
            }
            if (cyclic && !dca->supports_cyclic(dca)) {
                outcome_fail(o, slot_id, VDP_EC_CYCLIC_NOT_SUPPORTED);
                continue;
            }
            if (on_change && !dca->supports_on_change(dca)) {
                outcome_fail(o, slot_id, VDP_EC_ONCHANGE_NOT_SUPPORTED);
                continue;
            }
            if (tx_cyclic && srv->scheduler.cyclic_tct_ms != 0u) {
                outcome_fail(o, slot_id, VDP_EC_CYCLIC_TX_ALREADY_SET);
                continue;
            }

            bool persist = (set_byte >> VDP_SET_PERSIST_BIT) & 1u;
            if (persist) {
                if (srv->persistency_used >= srv->config.persistency_capacity) {
                    outcome_fail(o, slot_id, VDP_EC_PERSISTENCY_LIMIT);
                    continue;
                }
                srv->persistency_used++;
            }

            vdp_slot_t *slot = vdp_slots_add(&srv->slots);
            if (slot == NULL) {
                outcome_fail(o, slot_id, VDP_EC_GENERIC);
                continue;
            }
            slot->slot_id = slot_id;
            slot->dca_rem_id = dca_rem_id;
            slot->settings.tres = (vdp_tres_t)(set_byte & VDP_SET_TRES_MASK);
            slot->settings.sec = (set_byte >> VDP_SET_SEC_BIT) & 1u;
            slot->settings.persist = persist;
            slot->settings.tx_on_sampling = (set_byte >> VDP_SET_TX_ON_SAMPLING_BIT) & 1u;
            slot->settings.init_act = (set_byte >> VDP_SET_INIT_ACT_BIT) & 1u;
            slot->collection.on_change = on_change;
            slot->collection.cyclic = cyclic;
            slot->collection.sct_ms = sct_ms;
            slot->collection.tx_cyclic = tx_cyclic;
            slot->collection.tct_ms = tct_ms;
            slot->active = slot->settings.init_act;

            int64_t now = server_now(srv);
            slot->last_sample_ms = -1;
            slot->next_sample_ms = now + (int64_t)sct_ms;

            if (tx_cyclic) {
                vdp_scheduler_set_cyclic_tct(&srv->scheduler, tct_ms, now);
            }
            if (slot->active && dca->on_activate != NULL) {
                dca->on_activate(dca, slot_id);
            }
        }
    }
    return HANDLER_OK;
}

static int handle_remove(vdp_server_t *srv, vdp_reader_t *r, uint8_t ext, vdp_outcome_t *o) {
    bool is_global = (ext >> VDP_REMOVE_GLOBAL_BIT) & 1u;
    bool per_dca = (ext >> VDP_REMOVE_DCA_REM_BIT) & 1u;
    bool stop_cyclic = (ext >> VDP_REMOVE_T_CYCLIC_BIT) & 1u;

    if (stop_cyclic) {
        if (!vdp_reader_at_end(r)) {
            return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
        }
        vdp_scheduler_clear_cyclic_tct(&srv->scheduler);
        for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
            if (srv->slots.slots[i].in_use) {
                srv->slots.slots[i].collection.tx_cyclic = false;
            }
        }
        return HANDLER_OK;
    }

    if (is_global) {
        if (per_dca || !vdp_reader_at_end(r)) {
            return VDP_PEC_INVALID_OPTIONS;
        }
        vdp_slots_clear(&srv->slots);
        srv->persistency_used = 0;
        vdp_scheduler_clear_cyclic_tct(&srv->scheduler);
        return HANDLER_OK;
    }

    if (vdp_reader_at_end(r)) {
        return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
    }

    if (per_dca) {
        while (!vdp_reader_at_end(r)) {
            uint16_t dca_rem_id = (uint16_t)vdp_read_ddle(r);
            if (r->error) {
                return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
            }
            if (server_get_dca(srv, dca_rem_id) == NULL) {
                outcome_fail(o, dca_rem_id, VDP_EC_UNKNOWN_DCA_REM_ID);
                continue;
            }
            vdp_slots_remove_by_dca(&srv->slots, dca_rem_id);
        }
    } else {
        while (!vdp_reader_at_end(r)) {
            uint16_t slot_id = (uint16_t)vdp_read_ddle(r);
            if (r->error) {
                return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
            }
            if (!vdp_slots_remove(&srv->slots, slot_id)) {
                outcome_fail(o, slot_id, VDP_EC_UNKNOWN_SLOT_ID);
            }
        }
    }

    if (!vdp_slots_has_cyclic_tx(&srv->slots)) {
        vdp_scheduler_clear_cyclic_tct(&srv->scheduler);
    }
    return HANDLER_OK;
}

static int handle_activation(vdp_server_t *srv, vdp_reader_t *r, uint8_t ext, vdp_outcome_t *o) {
    bool activate = (ext >> VDP_ACT_BIT) & 1u;

    if (vdp_reader_at_end(r)) {
        return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
    }

    while (!vdp_reader_at_end(r)) {
        uint16_t slot_id = (uint16_t)vdp_read_ddle(r);
        if (r->error) {
            return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
        }
        vdp_slot_t *slot = vdp_slots_get(&srv->slots, slot_id);
        if (slot == NULL) {
            outcome_fail(o, slot_id, VDP_EC_UNKNOWN_SLOT_ID);
            continue;
        }
        if (slot->active == activate) {
            continue;
        }
        slot->active = activate;
        vdp_dca_t *dca = server_get_dca(srv, slot->dca_rem_id);
        if (dca == NULL) {
            continue;
        }
        if (activate) {
            slot->next_sample_ms = server_now(srv) + (int64_t)slot->collection.sct_ms;
            if (dca->on_activate != NULL) {
                dca->on_activate(dca, slot_id);
            }
        } else if (dca->on_deactivate != NULL) {
            dca->on_deactivate(dca, slot_id);
        }
    }
    return HANDLER_OK;
}

static int handle_trigger(vdp_server_t *srv, vdp_reader_t *r, uint8_t ext, vdp_outcome_t *o) {
    bool tx_trigger = (ext >> VDP_TX_TRIG_BIT) & 1u;

    uint16_t slot_ids[VDP_MAX_SLOTS];
    size_t count = 0;
    while (!vdp_reader_at_end(r)) {
        uint16_t slot_id = (uint16_t)vdp_read_ddle(r);
        if (r->error) {
            return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
        }
        if (count < VDP_MAX_SLOTS) {
            slot_ids[count++] = slot_id;
        }
    }

    if (!tx_trigger && count == 0u) {
        return VDP_PEC_INCORRECT_NUMBER_OF_BYTES;
    }

    for (size_t i = 0; i < count; ++i) {
        if (vdp_slots_get(&srv->slots, slot_ids[i]) == NULL) {
            outcome_fail(o, slot_ids[i], VDP_EC_UNKNOWN_SLOT_ID);
            continue;
        }
        vdp_error_code_t rc = server_sample_slot(srv, slot_ids[i]);
        if (rc != VDP_EC_NONE && rc != VDP_EC_SAMPLING_ERROR && rc != VDP_EC_BUFFER_FULL) {
            outcome_fail(o, slot_ids[i], rc);
        }
    }

    if (tx_trigger) {
        vdp_scheduler_request_transmit(&srv->scheduler);
    }
    return HANDLER_OK;
}

/* ======================================================================== */
/* Response / error message encoders                                        */
/* ======================================================================== */

static void send_version_response(vdp_server_t *srv) {
    uint8_t buf[8];
    vdp_writer_t w;
    vdp_writer_init(&w, buf, sizeof(buf));
    vdp_write_u8(&w, (uint8_t)VDP_MT_VERSION);
    vdp_write_u8(&w, VDP_PROTOCOL_VERSION_MAIN);
    vdp_write_u8(&w, VDP_PROTOCOL_VERSION_MINOR);
    server_send(srv, w.data, w.len);
}

static void send_error_message(vdp_server_t *srv, vdp_pec_t pec,
                               const uint8_t *info, size_t info_len) {
    uint8_t buf[16];
    vdp_writer_t w;
    vdp_writer_init(&w, buf, sizeof(buf));
    vdp_write_u8(&w, (uint8_t)VDP_MT_ERROR); /* ADD = 0 */
    vdp_write_u8(&w, (uint8_t)(pec & 0x1Fu));
    vdp_write_bytes(&w, info, info_len);
    server_send(srv, w.data, w.len);
}

static void send_control_response(vdp_server_t *srv, uint8_t con_sq_ct,
                                  vdp_command_type_t ct, const vdp_outcome_t *o) {
    uint8_t buf[VDP_MAX_MESSAGE_SIZE];
    vdp_writer_t w;
    vdp_writer_init(&w, buf, sizeof(buf));
    vdp_write_u8(&w, (uint8_t)(VDP_MT_CONTROL | ((con_sq_ct & 0x1Fu) << 2)));
    uint8_t ext = (uint8_t)ct;
    if (o->ack) {
        ext |= (uint8_t)(1u << VDP_ACK_BIT);
    }
    vdp_write_u8(&w, ext);
    if (!o->ack) {
        for (size_t i = 0; i < o->err_count; ++i) {
            vdp_write_ddle(&w, o->errs[i].ref_id);
            vdp_write_u8(&w, o->errs[i].code);
        }
    }
    server_send(srv, w.data, w.len);
}

/* ======================================================================== */
/* Transmission scheduling (data messages)                                  */
/* ======================================================================== */

static void scheduler_flush(vdp_server_t *srv, int64_t now) {
    vdp_scheduler_t *s = &srv->scheduler;

    bool due = s->pending_request || vdp_buffer_is_full(&srv->buffer);
    if (s->cyclic_tct_ms != 0u && now >= s->next_cyclic_ms) {
        due = true;
        s->next_cyclic_ms += (int64_t)s->cyclic_tct_ms;
    }
    if (!due) {
        return;
    }
    if (!vdp_buffer_has_pending(&srv->buffer)) {
        s->pending_request = false;
        return;
    }
    if (now - s->last_tx_ms < (int64_t)s->mtdt_ms) {
        return; /* MTDT not elapsed yet */
    }

    uint8_t buf[VDP_MAX_MESSAGE_SIZE];
    size_t len = vdp_build_data_message(&srv->slots, s->seq_ct, &srv->buffer,
                                        buf, sizeof(buf));
    if (len > 0u) {
        server_send(srv, buf, len);
        s->seq_ct = next_seq(s->seq_ct);
        s->last_tx_ms = now;
    }
    vdp_buffer_clear(&srv->buffer);
    s->pending_request = false;
}

/* ======================================================================== */
/* Sampling                                                                 */
/* ======================================================================== */

static void run_sampling(vdp_server_t *srv, int64_t now) {
    for (size_t i = 0; i < VDP_MAX_SLOTS; ++i) {
        vdp_slot_t *slot = &srv->slots.slots[i];
        if (!slot->in_use || !slot->active || !slot->collection.cyclic ||
            slot->collection.sct_ms == 0u) {
            continue;
        }
        if (now < slot->next_sample_ms) {
            continue;
        }
        if (slot->last_sample_ms >= 0 &&
            (now - slot->last_sample_ms) < (int64_t)srv->config.msdt_ms) {
            continue;
        }
        (void)server_sample_slot(srv, slot->slot_id);
        uint32_t step = slot->collection.sct_ms;
        if (step < srv->config.msdt_ms) {
            step = srv->config.msdt_ms;
        }
        slot->next_sample_ms += (int64_t)step;
        if (slot->next_sample_ms <= now) {
            slot->next_sample_ms = now + (int64_t)slot->collection.sct_ms;
        }
    }
}

/* ======================================================================== */
/* Dispatch                                                                 */
/* ======================================================================== */

static void dispatch_control(vdp_server_t *srv, uint8_t con_sq_ct, vdp_reader_t *r) {
    if (con_sq_ct != srv->expected_con_sq_ct) {
        uint8_t expected = (uint8_t)(srv->expected_con_sq_ct & 0x1Fu);
        send_error_message(srv, VDP_PEC_CONTROL_SEQUENCE_COUNTER, &expected, 1);
        return;
    }

    uint8_t ext = vdp_read_u8(r);
    vdp_command_type_t ct = (vdp_command_type_t)(ext & 0x03u);

    vdp_outcome_t outcome;
    outcome_init(&outcome);

    int result;
    switch (ct) {
        case VDP_CT_ADD_CONFIG:    result = handle_add(srv, r, ext, &outcome); break;
        case VDP_CT_REMOVE_CONFIG: result = handle_remove(srv, r, ext, &outcome); break;
        case VDP_CT_ACTIVATION:    result = handle_activation(srv, r, ext, &outcome); break;
        case VDP_CT_TRIGGER:
        default:                   result = handle_trigger(srv, r, ext, &outcome); break;
    }

    srv->expected_con_sq_ct = next_seq(srv->expected_con_sq_ct);

    if (result != HANDLER_OK) {
        send_error_message(srv, (vdp_pec_t)result, NULL, 0);
        return;
    }
    send_control_response(srv, con_sq_ct, ct, &outcome);
}

void vdp_server_receive(vdp_server_t *srv, const uint8_t *data, size_t len) {
    vdp_reader_t r;
    vdp_reader_init(&r, data, len);

    uint8_t header = vdp_read_u8(&r);
    if (r.error) {
        send_error_message(srv, VDP_PEC_INCORRECT_NUMBER_OF_BYTES, NULL, 0);
        return;
    }
    vdp_message_type_t mt = (vdp_message_type_t)(header & 0x03u);
    uint8_t add = (uint8_t)((header >> 2) & 0x1Fu);

    switch (mt) {
        case VDP_MT_VERSION:
            send_version_response(srv);
            break;
        case VDP_MT_CONTROL:
            dispatch_control(srv, add, &r);
            break;
        default:
            /* Data / error messages are server -> client only. */
            send_error_message(srv, VDP_PEC_UNKNOWN_MESSAGE_TYPE, NULL, 0);
            break;
    }

    /* A transmission trigger requests data after the control response; flush it. */
    vdp_server_tick(srv, server_now(srv));
}

/* ======================================================================== */
/* Public API                                                               */
/* ======================================================================== */

void vdp_server_init(vdp_server_t *srv,
                     const vdp_config_t *config,
                     vdp_send_fn send, void *send_user,
                     vdp_clock_fn clock, void *clock_user) {
    memset(srv, 0, sizeof(*srv));
    srv->config = (config != NULL) ? *config : vdp_config_default();
    srv->send = send;
    srv->send_user = send_user;
    srv->clock = clock;
    srv->clock_user = clock_user;
    srv->expected_con_sq_ct = VDP_SEQ_INIT;
    srv->persistency_used = 0;
    vdp_slots_init(&srv->slots, srv->config.max_slot_id);
    vdp_buffer_init(&srv->buffer);
    vdp_scheduler_init(&srv->scheduler, srv->config.mtdt_ms);
}

bool vdp_server_register_dca(vdp_server_t *srv, vdp_dca_t *dca) {
    if (srv->dca_count >= VDP_MAX_DCAS) {
        return false;
    }
    srv->dcas[srv->dca_count++] = dca;
    return true;
}

void vdp_server_tick(vdp_server_t *srv, int64_t now_ms) {
    run_sampling(srv, now_ms);
    scheduler_flush(srv, now_ms);
}

void vdp_server_report_async_error(vdp_server_t *srv, uint16_t slot_id, vdp_error_code_t code) {
    vdp_buffer_add_async_error(&srv->buffer, slot_id, code);
}
