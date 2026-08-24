#include "vdp/vdp_codec.h"

#include <string.h>

void vdp_reader_init(vdp_reader_t *r, const uint8_t *data, size_t len) {
    r->data = data;
    r->len = len;
    r->pos = 0;
    r->error = false;
}

bool vdp_reader_at_end(const vdp_reader_t *r) {
    return r->pos >= r->len;
}

size_t vdp_reader_remaining(const vdp_reader_t *r) {
    return (r->pos <= r->len) ? (r->len - r->pos) : 0u;
}

static bool reader_need(vdp_reader_t *r, size_t n) {
    if (r->error || vdp_reader_remaining(r) < n) {
        r->error = true;
        return false;
    }
    return true;
}

uint8_t vdp_read_u8(vdp_reader_t *r) {
    if (!reader_need(r, 1)) {
        return 0;
    }
    return r->data[r->pos++];
}

uint16_t vdp_read_u16(vdp_reader_t *r) {
    if (!reader_need(r, 2)) {
        return 0;
    }
    uint16_t v = (uint16_t)r->data[r->pos] |
                 (uint16_t)((uint16_t)r->data[r->pos + 1] << 8);
    r->pos += 2;
    return v;
}

uint32_t vdp_read_u32(vdp_reader_t *r) {
    if (!reader_need(r, 4)) {
        return 0;
    }
    uint32_t v = (uint32_t)r->data[r->pos] |
                 ((uint32_t)r->data[r->pos + 1] << 8) |
                 ((uint32_t)r->data[r->pos + 2] << 16) |
                 ((uint32_t)r->data[r->pos + 3] << 24);
    r->pos += 4;
    return v;
}

const uint8_t *vdp_read_bytes(vdp_reader_t *r, size_t n) {
    if (!reader_need(r, n)) {
        return NULL;
    }
    const uint8_t *p = &r->data[r->pos];
    r->pos += n;
    return p;
}

uint32_t vdp_read_ddle(vdp_reader_t *r) {
    uint32_t value = 0;
    unsigned shift = 0;
    for (;;) {
        if (!reader_need(r, 1)) {
            return 0;
        }
        uint8_t byte = r->data[r->pos++];
        value |= (uint32_t)(byte & 0x7Fu) << shift;
        if ((byte & 0x80u) == 0u) {
            return value;
        }
        shift += 7u;
        if (shift > 28u) { /* would overflow a uint32 */
            r->error = true;
            return 0;
        }
    }
}

void vdp_writer_init(vdp_writer_t *w, uint8_t *buf, size_t cap) {
    w->data = buf;
    w->cap = cap;
    w->len = 0;
    w->overflow = false;
}

static bool writer_room(vdp_writer_t *w, size_t n) {
    if (w->overflow || (w->len + n) > w->cap) {
        w->overflow = true;
        return false;
    }
    return true;
}

void vdp_write_u8(vdp_writer_t *w, uint8_t v) {
    if (!writer_room(w, 1)) {
        return;
    }
    w->data[w->len++] = v;
}

void vdp_write_u16(vdp_writer_t *w, uint16_t v) {
    if (!writer_room(w, 2)) {
        return;
    }
    w->data[w->len++] = (uint8_t)(v & 0xFFu);
    w->data[w->len++] = (uint8_t)((v >> 8) & 0xFFu);
}

void vdp_write_u32(vdp_writer_t *w, uint32_t v) {
    if (!writer_room(w, 4)) {
        return;
    }
    w->data[w->len++] = (uint8_t)(v & 0xFFu);
    w->data[w->len++] = (uint8_t)((v >> 8) & 0xFFu);
    w->data[w->len++] = (uint8_t)((v >> 16) & 0xFFu);
    w->data[w->len++] = (uint8_t)((v >> 24) & 0xFFu);
}

void vdp_write_bytes(vdp_writer_t *w, const uint8_t *data, size_t n) {
    if (n == 0u) {
        return;
    }
    if (!writer_room(w, n)) {
        return;
    }
    memcpy(&w->data[w->len], data, n);
    w->len += n;
}

void vdp_write_ddle(vdp_writer_t *w, uint32_t v) {
    for (;;) {
        uint8_t byte = (uint8_t)(v & 0x7Fu);
        v >>= 7;
        if (v != 0u) {
            vdp_write_u8(w, (uint8_t)(byte | 0x80u));
        } else {
            vdp_write_u8(w, byte);
            return;
        }
    }
}

uint32_t vdp_tres_step_ms(vdp_tres_t tres) {
    switch (tres) {
        case VDP_TRES_MS_10:  return 10u;
        case VDP_TRES_MS_100: return 100u;
        case VDP_TRES_S_1:    return 1000u;
        case VDP_TRES_MS_1:
        default:              return 1u;
    }
}

uint32_t vdp_encode_rel_ticks(int64_t sample_ms, int64_t previous_ms, vdp_tres_t tres) {
    int64_t delta = sample_ms - previous_ms;
    if (delta < 0) {
        delta = 0;
    }
    return (uint32_t)(delta / (int64_t)vdp_tres_step_ms(tres));
}
