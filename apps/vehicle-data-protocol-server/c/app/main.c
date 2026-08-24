/**
 * @file main.c
 * @brief Runnable demo mirroring scenarios S1-S5 against a loopback (callback) send.
 */
#include <stdio.h>

#include "vdp/vdp_proxy.h"
#include "vdp/vdp_server.h"

/* A mutable clock the demo advances by hand. */
static int64_t g_now_ms = 0;
static int64_t demo_clock(void *user) {
    (void)user;
    return g_now_ms;
}

static const char *mt_name(uint8_t header) {
    switch (header & 0x03u) {
        case VDP_MT_VERSION: return "VERSION";
        case VDP_MT_CONTROL: return "CONTROL";
        case VDP_MT_DATA:    return "DATA   ";
        default:             return "ERROR  ";
    }
}

static void demo_send(void *user, const uint8_t *data, size_t len) {
    (void)user;
    printf("  S->P: %s ", mt_name(data[0]));
    for (size_t i = 0; i < len; ++i) {
        printf("%02x", data[i]);
    }
    printf("\n");
}

int main(void) {
    uint8_t buf[VDP_MAX_MESSAGE_SIZE];
    size_t n;

    vdp_config_t config = vdp_config_default();
    vdp_server_t server;
    vdp_server_init(&server, &config, demo_send, NULL, demo_clock, NULL);

    vdp_demo_dca_t dca;
    vdp_demo_dca_init(&dca, 1, true, true);
    vdp_server_register_dca(&server, &dca.base);

    printf("S1: query protocol version\n");
    n = vdp_proxy_version_request(buf, sizeof(buf));
    vdp_server_receive(&server, buf, n);

    printf("\nS2/S3: add a cyclic slot with initial activation ON\n");
    vdp_proxy_dp_t dp = {0};
    dp.slot_id = 1;
    dp.cyclic = true;
    dp.sct_ms = 100;
    dp.init_act = true;
    dp.tres = VDP_TRES_MS_10;
    n = vdp_proxy_add_config(buf, sizeof(buf), 1, 1, &dp, 1);
    vdp_server_receive(&server, buf, n);

    printf("\nRun 500 ms of cyclic sampling, then pull the buffered data\n");
    for (int i = 0; i < 5; ++i) {
        g_now_ms += 100;
        vdp_server_tick(&server, g_now_ms);
    }
    n = vdp_proxy_trigger(buf, sizeof(buf), 2, true, NULL, 0);
    vdp_server_receive(&server, buf, n);

    printf("\nDeactivate slot 1\n");
    uint16_t slot1 = 1;
    n = vdp_proxy_activation(buf, sizeof(buf), 3, false, &slot1, 1);
    vdp_server_receive(&server, buf, n);

    return 0;
}
