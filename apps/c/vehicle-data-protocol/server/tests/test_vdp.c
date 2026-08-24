/**
 * @file test_vdp.c
 * @brief Unit / scenario tests for the C VDP server. Returns non-zero on failure.
 */
#include <stdio.h>
#include <string.h>

#include "vdp/vdp_codec.h"
#include "vdp/vdp_proxy.h"
#include "vdp/vdp_server.h"

static int g_failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);         \
            ++g_failures;                                                  \
        }                                                                  \
    } while (0)

/* --- Captured outbound messages ------------------------------------------ */
#define CAP_MAX 32
static uint8_t g_msgs[CAP_MAX][VDP_MAX_MESSAGE_SIZE];
static size_t g_lens[CAP_MAX];
static size_t g_count;
static int64_t g_now;

static int64_t test_clock(void *user) { (void)user; return g_now; }

static void test_send(void *user, const uint8_t *data, size_t len) {
    (void)user;
    if (g_count < CAP_MAX) {
        memcpy(g_msgs[g_count], data, len);
        g_lens[g_count] = len;
        ++g_count;
    }
}

static void reset(void) { g_count = 0; }

static uint8_t last_mt(size_t i) { return g_msgs[i][0] & 0x03u; }

static void make_server(vdp_server_t *srv, vdp_demo_dca_t *dca) {
    vdp_config_t cfg = vdp_config_default();
    cfg.mtdt_ms = 0;
    cfg.msdt_ms = 0;
    vdp_server_init(srv, &cfg, test_send, NULL, test_clock, NULL);
    vdp_demo_dca_init(dca, 1, true, true);
    vdp_server_register_dca(srv, &dca->base);
}

/* --- Codec ---------------------------------------------------------------- */
static void test_ddle_roundtrip(void) {
    const uint32_t values[] = {0u, 1u, 127u, 128u, 16382u, 16383u, 100000u};
    for (size_t i = 0; i < sizeof(values) / sizeof(values[0]); ++i) {
        uint8_t buf[8];
        vdp_writer_t w;
        vdp_writer_init(&w, buf, sizeof(buf));
        vdp_write_ddle(&w, values[i]);
        vdp_reader_t r;
        vdp_reader_init(&r, buf, w.len);
        CHECK(vdp_read_ddle(&r) == values[i]);
    }
    /* The async marker must be bytes 0xFF 0x7F. */
    uint8_t marker[4];
    vdp_writer_t w;
    vdp_writer_init(&w, marker, sizeof(marker));
    vdp_write_ddle(&w, VDP_SLOT_ID_ASYNC_ERR);
    CHECK(w.len == 2 && marker[0] == 0xFF && marker[1] == 0x7F);
}

static void test_reader_underflow(void) {
    uint8_t data[1] = {0x01};
    vdp_reader_t r;
    vdp_reader_init(&r, data, sizeof(data));
    (void)vdp_read_u32(&r);
    CHECK(r.error);
}

/* --- Scenarios ------------------------------------------------------------ */
static void test_s1_version(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    reset();
    uint8_t buf[8];
    size_t n = vdp_proxy_version_request(buf, sizeof(buf));
    vdp_server_receive(&srv, buf, n);
    CHECK(g_count == 1);
    CHECK(last_mt(0) == VDP_MT_VERSION);
    CHECK(g_msgs[0][1] == VDP_PROTOCOL_VERSION_MAIN);
    CHECK(g_msgs[0][2] == VDP_PROTOCOL_VERSION_MINOR);
}

static void test_s2_add_ack(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    reset();
    uint8_t buf[64];
    vdp_proxy_dp_t dp = {0};
    dp.slot_id = 1; dp.cyclic = true; dp.sct_ms = 100;
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 1, 1, &dp, 1);
    vdp_server_receive(&srv, buf, n);
    CHECK(g_count == 1);
    CHECK(last_mt(0) == VDP_MT_CONTROL);
    CHECK((g_msgs[0][1] >> VDP_ACK_BIT) & 1u); /* ACK=1 */
    CHECK(vdp_slots_get(&srv.slots, 1) != NULL);
}

static void test_s2_unknown_dca_nack(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    reset();
    uint8_t buf[64];
    vdp_proxy_dp_t dp = {0};
    dp.slot_id = 1;
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 1, 99, &dp, 1);
    vdp_server_receive(&srv, buf, n);
    CHECK(g_count == 1);
    CHECK(((g_msgs[0][1] >> VDP_ACK_BIT) & 1u) == 0u); /* ACK=0 */
    vdp_reader_t r; vdp_reader_init(&r, g_msgs[0], g_lens[0]);
    (void)vdp_read_u8(&r); (void)vdp_read_u8(&r);
    CHECK(vdp_read_ddle(&r) == 99);
    CHECK(vdp_read_u8(&r) == VDP_EC_UNKNOWN_DCA_REM_ID);
}

static void test_s3_cyclic_sampling(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    g_now = 0;
    uint8_t buf[64];
    vdp_proxy_dp_t dp = {0};
    dp.slot_id = 1; dp.cyclic = true; dp.sct_ms = 100; dp.init_act = true;
    dp.tres = VDP_TRES_MS_10;
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 1, 1, &dp, 1);
    vdp_server_receive(&srv, buf, n);
    for (int i = 0; i < 5; ++i) { g_now += 100; vdp_server_tick(&srv, g_now); }
    reset();
    n = vdp_proxy_trigger(buf, sizeof(buf), 2, true, NULL, 0);
    vdp_server_receive(&srv, buf, n);
    CHECK(g_count >= 2);
    CHECK(last_mt(0) == VDP_MT_CONTROL); /* trigger response first */
    bool saw_data = false;
    for (size_t i = 0; i < g_count; ++i) {
        if (last_mt(i) == VDP_MT_DATA) { saw_data = true; }
    }
    CHECK(saw_data);
}

static void test_s5_on_request(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    g_now = 0;
    uint8_t buf[64];
    vdp_proxy_dp_t dp = {0};
    dp.slot_id = 5; /* no automatic sampling */
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 1, 1, &dp, 1);
    vdp_server_receive(&srv, buf, n);
    g_now = 500; vdp_server_tick(&srv, g_now);
    CHECK(srv.buffer.sample_count == 0);
    reset();
    uint16_t slot5 = 5;
    n = vdp_proxy_trigger(buf, sizeof(buf), 2, false, &slot5, 1);
    vdp_server_receive(&srv, buf, n);
    CHECK((g_msgs[0][1] >> VDP_ACK_BIT) & 1u);
    CHECK(srv.buffer.sample_count == 1);
}

static void test_s11_sequence_error(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    reset();
    uint8_t buf[64];
    vdp_proxy_dp_t dp = {0}; dp.slot_id = 1;
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 5, 1, &dp, 1); /* expected 1, sent 5 */
    vdp_server_receive(&srv, buf, n);
    CHECK(g_count == 1);
    CHECK(last_mt(0) == VDP_MT_ERROR);
    CHECK(g_msgs[0][1] == VDP_PEC_CONTROL_SEQUENCE_COUNTER);
    CHECK(g_msgs[0][2] == 1); /* expected counter */
}

static void test_s12_malformed(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    reset();
    uint8_t buf[64];
    size_t n = vdp_proxy_activation(buf, sizeof(buf), 1, true, NULL, 0); /* empty payload */
    vdp_server_receive(&srv, buf, n);
    CHECK(last_mt(0) == VDP_MT_ERROR);
    CHECK(g_msgs[0][1] == VDP_PEC_INCORRECT_NUMBER_OF_BYTES);
}

static void test_duplicate_slot_in_message(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    reset();
    uint8_t buf[64];
    vdp_proxy_dp_t dps[2] = {0};
    dps[0].slot_id = 7; dps[1].slot_id = 7;
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 1, 1, dps, 2);
    vdp_server_receive(&srv, buf, n);
    CHECK(last_mt(0) == VDP_MT_ERROR);
    CHECK(g_msgs[0][1] == VDP_PEC_DUPLICATED_SLOT_ID);
}

static void test_async_error_in_data(void) {
    vdp_server_t srv; vdp_demo_dca_t dca; make_server(&srv, &dca);
    g_now = 0;
    uint8_t buf[64];
    vdp_proxy_dp_t dp = {0}; dp.slot_id = 3;
    size_t n = vdp_proxy_add_config(buf, sizeof(buf), 1, 1, &dp, 1);
    vdp_server_receive(&srv, buf, n);
    vdp_server_report_async_error(&srv, 3, VDP_EC_SAMPLING_ERROR);
    reset();
    n = vdp_proxy_trigger(buf, sizeof(buf), 2, true, NULL, 0);
    vdp_server_receive(&srv, buf, n);
    bool ok = false;
    for (size_t i = 0; i < g_count; ++i) {
        if (last_mt(i) == VDP_MT_DATA) {
            vdp_reader_t r; vdp_reader_init(&r, g_msgs[i], g_lens[i]);
            (void)vdp_read_u8(&r); (void)vdp_read_u32(&r);
            CHECK(vdp_read_ddle(&r) == VDP_SLOT_ID_ASYNC_ERR);
            CHECK(vdp_read_u8(&r) == VDP_EC_SAMPLING_ERROR);
            ok = true;
        }
    }
    CHECK(ok);
}

int main(void) {
    test_ddle_roundtrip();
    test_reader_underflow();
    test_s1_version();
    test_s2_add_ack();
    test_s2_unknown_dca_nack();
    test_s3_cyclic_sampling();
    test_s5_on_request();
    test_s11_sequence_error();
    test_s12_malformed();
    test_duplicate_slot_in_message();
    test_async_error_in_data();

    if (g_failures == 0) {
        printf("All C tests passed.\n");
        return 0;
    }
    printf("%d C test(s) failed.\n", g_failures);
    return 1;
}
