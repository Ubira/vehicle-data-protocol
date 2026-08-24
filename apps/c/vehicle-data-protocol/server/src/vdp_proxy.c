#include "vdp/vdp_proxy.h"

static void write_base(vdp_writer_t *w, vdp_message_type_t mt, uint8_t add) {
    vdp_write_u8(w, (uint8_t)(mt | ((add & 0x1Fu) << 2)));
}

size_t vdp_proxy_version_request(uint8_t *out, size_t cap) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, cap);
    write_base(&w, VDP_MT_VERSION, 0);
    return w.overflow ? 0 : w.len;
}

static uint8_t set_byte(const vdp_proxy_dp_t *dp) {
    uint8_t v = (uint8_t)(dp->tres & VDP_SET_TRES_MASK);
    v |= (uint8_t)(dp->sec << VDP_SET_SEC_BIT);
    v |= (uint8_t)(dp->persist << VDP_SET_PERSIST_BIT);
    v |= (uint8_t)(dp->tx_on_sampling << VDP_SET_TX_ON_SAMPLING_BIT);
    v |= (uint8_t)(dp->init_act << VDP_SET_INIT_ACT_BIT);
    return v;
}

static uint8_t col_byte(const vdp_proxy_dp_t *dp) {
    uint8_t v = (uint8_t)(dp->on_change << VDP_COL_SCHANGE_BIT);
    v |= (uint8_t)(dp->cyclic << VDP_COL_SCYCLIC_BIT);
    v |= (uint8_t)(dp->tx_cyclic << VDP_COL_TCYCLIC_BIT);
    return v;
}

size_t vdp_proxy_add_config(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                            uint16_t dca_rem_id,
                            const vdp_proxy_dp_t *dps, size_t dp_count) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, cap);
    write_base(&w, VDP_MT_CONTROL, con_sq_ct);
    vdp_write_u8(&w, (uint8_t)VDP_CT_ADD_CONFIG);
    vdp_write_ddle(&w, dca_rem_id);
    vdp_write_ddle(&w, (uint32_t)dp_count);
    for (size_t i = 0; i < dp_count; ++i) {
        const vdp_proxy_dp_t *dp = &dps[i];
        vdp_write_ddle(&w, dp->slot_id);
        vdp_write_u8(&w, set_byte(dp));
        vdp_write_u8(&w, col_byte(dp));
        if (dp->cyclic) {
            vdp_write_ddle(&w, dp->sct_ms);
        }
        if (dp->tx_cyclic) {
            vdp_write_ddle(&w, dp->tct_ms);
        }
        vdp_write_ddle(&w, 0u); /* DCA_CFG_LEN */
    }
    return w.overflow ? 0 : w.len;
}

size_t vdp_proxy_activation(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                            bool activate, const uint16_t *slot_ids, size_t count) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, cap);
    write_base(&w, VDP_MT_CONTROL, con_sq_ct);
    uint8_t ext = (uint8_t)(VDP_CT_ACTIVATION | ((uint8_t)activate << VDP_ACT_BIT));
    vdp_write_u8(&w, ext);
    for (size_t i = 0; i < count; ++i) {
        vdp_write_ddle(&w, slot_ids[i]);
    }
    return w.overflow ? 0 : w.len;
}

size_t vdp_proxy_trigger(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                         bool tx_trigger, const uint16_t *slot_ids, size_t count) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, cap);
    write_base(&w, VDP_MT_CONTROL, con_sq_ct);
    uint8_t ext = (uint8_t)(VDP_CT_TRIGGER | ((uint8_t)tx_trigger << VDP_TX_TRIG_BIT));
    vdp_write_u8(&w, ext);
    for (size_t i = 0; i < count; ++i) {
        vdp_write_ddle(&w, slot_ids[i]);
    }
    return w.overflow ? 0 : w.len;
}

size_t vdp_proxy_remove_slots(uint8_t *out, size_t cap, uint8_t con_sq_ct,
                              const uint16_t *slot_ids, size_t count) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, cap);
    write_base(&w, VDP_MT_CONTROL, con_sq_ct);
    vdp_write_u8(&w, (uint8_t)VDP_CT_REMOVE_CONFIG);
    for (size_t i = 0; i < count; ++i) {
        vdp_write_ddle(&w, slot_ids[i]);
    }
    return w.overflow ? 0 : w.len;
}

size_t vdp_proxy_remove_all(uint8_t *out, size_t cap, uint8_t con_sq_ct) {
    vdp_writer_t w;
    vdp_writer_init(&w, out, cap);
    write_base(&w, VDP_MT_CONTROL, con_sq_ct);
    vdp_write_u8(&w, (uint8_t)(VDP_CT_REMOVE_CONFIG | (1u << VDP_REMOVE_GLOBAL_BIT)));
    return w.overflow ? 0 : w.len;
}
