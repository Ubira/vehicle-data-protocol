/**
 * @file vdp_server.h
 * @brief The VDP Server (VDP-CM Remote) — top-level assembly and public API.
 *
 * Single-threaded and deterministic: call vdp_server_receive() to process an inbound
 * control/version message and vdp_server_tick() to advance time (the Classic Platform
 * "main function period" model). Outbound messages are delivered through a send
 * callback; time is read through a clock callback, so the whole server is testable
 * without real I/O or concurrency.
 */
#ifndef VDP_SERVER_H
#define VDP_SERVER_H

#include "vdp/vdp_core.h"
#include "vdp/vdp_dca.h"
#include "vdp/vdp_types.h"

typedef void (*vdp_send_fn)(void *user, const uint8_t *data, size_t len);
typedef int64_t (*vdp_clock_fn)(void *user);

typedef struct {
    uint16_t max_slot_id;
    size_t max_message_size;
    uint32_t mtdt_ms;
    uint32_t msdt_ms;
    uint16_t persistency_capacity;
} vdp_config_t;

vdp_config_t vdp_config_default(void);

typedef struct {
    vdp_config_t config;
    vdp_slot_table_t slots;
    vdp_buffer_t buffer;
    vdp_scheduler_t scheduler;

    vdp_dca_t *dcas[VDP_MAX_DCAS];
    size_t dca_count;

    uint8_t expected_con_sq_ct;
    uint16_t persistency_used;

    vdp_send_fn send;
    void *send_user;
    vdp_clock_fn clock;
    void *clock_user;
} vdp_server_t;

void vdp_server_init(vdp_server_t *srv,
                     const vdp_config_t *config,
                     vdp_send_fn send, void *send_user,
                     vdp_clock_fn clock, void *clock_user);

bool vdp_server_register_dca(vdp_server_t *srv, vdp_dca_t *dca);

/* Process one inbound control/version message and emit its response(s). */
void vdp_server_receive(vdp_server_t *srv, const uint8_t *data, size_t len);

/* Advance time: run cyclic sampling and let the scheduler emit data messages. */
void vdp_server_tick(vdp_server_t *srv, int64_t now_ms);

/* Inject an asynchronous error (e.g. timebase loss) into the next data message. */
void vdp_server_report_async_error(vdp_server_t *srv, uint16_t slot_id, vdp_error_code_t code);

#endif /* VDP_SERVER_H */
