/**
 * @file vdp_codec.h
 * @brief Message Codec: little-endian byte reader/writer and DDLE[UINT].
 *
 * Implements the cross-cutting encoding rules from the development view:
 * little-endian fields (FO_PRS_VDP_00001), reserved bits 0 (FO_PRS_VDP_00138) and
 * dynamic-length unsigned integers DDLE[UINT] (FO_PRS_VDP_00003). All reads are
 * bounds-checked; on underflow the reader latches an error flag.
 */
#ifndef VDP_CODEC_H
#define VDP_CODEC_H

#include "vdp/vdp_types.h"

typedef struct {
    const uint8_t *data;
    size_t len;
    size_t pos;
    bool error; /* set on out-of-bounds read */
} vdp_reader_t;

typedef struct {
    uint8_t *data;
    size_t cap;
    size_t len;
    bool overflow; /* set when a write would exceed cap */
} vdp_writer_t;

void vdp_reader_init(vdp_reader_t *r, const uint8_t *data, size_t len);
bool vdp_reader_at_end(const vdp_reader_t *r);
size_t vdp_reader_remaining(const vdp_reader_t *r);
uint8_t vdp_read_u8(vdp_reader_t *r);
uint16_t vdp_read_u16(vdp_reader_t *r);
uint32_t vdp_read_u32(vdp_reader_t *r);
const uint8_t *vdp_read_bytes(vdp_reader_t *r, size_t n);
uint32_t vdp_read_ddle(vdp_reader_t *r);

void vdp_writer_init(vdp_writer_t *w, uint8_t *buf, size_t cap);
void vdp_write_u8(vdp_writer_t *w, uint8_t v);
void vdp_write_u16(vdp_writer_t *w, uint16_t v);
void vdp_write_u32(vdp_writer_t *w, uint32_t v);
void vdp_write_bytes(vdp_writer_t *w, const uint8_t *data, size_t n);
void vdp_write_ddle(vdp_writer_t *w, uint32_t v);

/* Relative timestamp helpers (FO_PRS_VDP_00004, FO_PRS_VDP_00042). */
uint32_t vdp_tres_step_ms(vdp_tres_t tres);
uint32_t vdp_encode_rel_ticks(int64_t sample_ms, int64_t previous_ms, vdp_tres_t tres);

#endif /* VDP_CODEC_H */
