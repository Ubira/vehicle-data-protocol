/**
 * @file vdp_types.h
 * @brief Protocol constants, enums and shared data structures for the VDP Server
 *        (AUTOSAR VDP-CM Remote role).
 *
 * The wire format matches the Python implementation under ../python; see
 * ../python/WIRE_FORMAT.md. Requirement identifiers such as FO_PRS_VDP_00007 refer to
 * the AUTOSAR source specifications in the repository's standards/ folder.
 */
#ifndef VDP_TYPES_H
#define VDP_TYPES_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

/* --- Protocol version [FO_PRS_VDP_00020..00023] --------------------------- */
#define VDP_PROTOCOL_VERSION_MAIN  0x01u
#define VDP_PROTOCOL_VERSION_MINOR 0x01u

/* --- Sequence counters (5-bit, 1..31, wrap 31->1) ------------------------- */
#define VDP_SEQ_MIN  1u
#define VDP_SEQ_MAX  31u
#define VDP_SEQ_INIT 1u

/* --- Identifier ranges ---------------------------------------------------- */
#define VDP_DCA_REM_ID_MIN     1u
#define VDP_DCA_REM_ID_MAX     16383u
#define VDP_SLOT_ID_MIN        1u
#define VDP_SLOT_ID_MAX_LIMIT  16382u
#define VDP_SLOT_ID_ASYNC_ERR  16383u   /* encodes to bytes 0xFF 0x7F */

/* --- Compile-time capacities (fixed, no dynamic allocation) --------------- */
#ifndef VDP_MAX_SLOTS
#define VDP_MAX_SLOTS 64
#endif
#ifndef VDP_MAX_DCAS
#define VDP_MAX_DCAS 8
#endif
#ifndef VDP_BUFFER_CAPACITY
#define VDP_BUFFER_CAPACITY 64
#endif
#ifndef VDP_MAX_SAMPLE_DATA
#define VDP_MAX_SAMPLE_DATA 32
#endif
#ifndef VDP_MAX_MESSAGE_SIZE
#define VDP_MAX_MESSAGE_SIZE 1400
#endif

/* --- Message types (MT, 2 bits) ------------------------------------------- */
typedef enum {
    VDP_MT_VERSION = 0,
    VDP_MT_CONTROL = 1,
    VDP_MT_DATA    = 2,
    VDP_MT_ERROR   = 3
} vdp_message_type_t;

/* --- Control command types (CT, 2 bits) ----------------------------------- */
typedef enum {
    VDP_CT_ADD_CONFIG    = 0,
    VDP_CT_REMOVE_CONFIG = 1,
    VDP_CT_ACTIVATION    = 2,
    VDP_CT_TRIGGER       = 3
} vdp_command_type_t;

/* --- Timestamp resolution (TRES, 2 bits) ---------------------------------- */
typedef enum {
    VDP_TRES_MS_1   = 0,
    VDP_TRES_MS_10  = 1,
    VDP_TRES_MS_100 = 2,
    VDP_TRES_S_1    = 3
} vdp_tres_t;

/* --- Protocol error codes (PEC, 5 bits) [FO_PRS_VDP_00006] ---------------- */
typedef enum {
    VDP_PEC_CONTROL_SEQUENCE_COUNTER = 0,
    VDP_PEC_INVALID_OPTIONS          = 1,
    VDP_PEC_DUPLICATED_SLOT_ID       = 2,
    VDP_PEC_INCORRECT_NUMBER_OF_BYTES= 3,
    VDP_PEC_UNKNOWN_MESSAGE_TYPE     = 4
} vdp_pec_t;

/* --- Error codes (EC, 1 byte) [FO_PRS_VDP_00005] --------------------------- */
/* Sent from the VDP-CM Remote to the VDP-CM Proxy in a control response (sync) */
/* or a data message (async). 0x00..0x08 originate in the DCA Remote;          */
/* 0x70..0x7D originate in the VDP-CM Remote.                                   */
typedef enum {
    /* Internal sentinel only: no error / success. Never sent on the wire (the
     * on-wire value 0x00 means Generic error (DCA Remote) -> VDP_EC_GENERIC_DCA). */
    VDP_EC_NONE                     = -1,

    /* Errors originating in the DCA Remote (0x00..0x08) */
    VDP_EC_GENERIC_DCA              = 0x00, /* Generic error (DCA Remote) */
    VDP_EC_DATA_SOURCE_ERROR        = 0x01, /* Data source error (async) */
    VDP_EC_SAMPLING_ERROR           = 0x02, /* Data point sampling error (sync/async) */
    VDP_EC_DATA_LOSS                = 0x03, /* Data loss error (async) */
    VDP_EC_INVALID_DCFG             = 0x04, /* Invalid DCA_REM_DP_DCFG (sync) */
    VDP_EC_DUPLICATED_DCFG          = 0x05, /* Duplicated DCA_REM_DP_DCFG (sync) */
    VDP_EC_DATA_POINT_LIMIT         = 0x06, /* Data point limit reached (sync) */
    VDP_EC_CYCLIC_NOT_SUPPORTED     = 0x07, /* Sampling mode cyclic not supported (sync) */
    VDP_EC_ONCHANGE_NOT_SUPPORTED   = 0x08, /* Sampling mode on-change not supported (sync) */

    /* Errors originating in the VDP-CM Remote (0x70..0x7D) */
    VDP_EC_GENERIC_REMOTE           = 0x70, /* Generic error (VDP-CM Remote) */
    VDP_EC_TIMESTAMP_ENCODING_ERROR = 0x71, /* Timestamp encoding error (async) */
    VDP_EC_TIMEBASE_ERROR           = 0x72, /* Timebase error (async) */
    VDP_EC_SAMPLE_TOO_LONG          = 0x73, /* Sample too long (async) */
    VDP_EC_BUFFER_FULL              = 0x74, /* Data buffer full (async) */
    VDP_EC_UNKNOWN_SLOT_ID          = 0x75, /* VDP Slot ID unknown (sync) */
    VDP_EC_UNKNOWN_DCA_REM_ID       = 0x76, /* DCA Remote ID unknown (sync) */
    VDP_EC_SLOT_ID_OUT_OF_RANGE     = 0x77, /* VDP Slot ID out of range (sync) */
    VDP_EC_PERSISTENCY_LIMIT        = 0x78, /* Persistency storage limit reached (sync) */
    VDP_EC_DUPLICATE_SLOT_ID        = 0x79, /* VDP Slot ID already in use (sync) */
    VDP_EC_DCA_REM_INCONSISTENCY    = 0x7A, /* DCA Remote inconsistency error (sync) */
    VDP_EC_SECURED_CHANNEL_NOT_SUPPORTED = 0x7B, /* Secured channel not supported (sync) */
    VDP_EC_CYCLIC_TX_ALREADY_SET    = 0x7C, /* TX mode cyclic already in use / not set (sync) */
    VDP_EC_SLOT_ID_RESERVED         = 0x7D  /* VDP Slot ID reserved (sync) */
} vdp_error_code_t;

/* --- SET field bit positions ---------------------------------------------- */
#define VDP_SET_TRES_MASK            0x03u
#define VDP_SET_SEC_BIT              2u
#define VDP_SET_PERSIST_BIT          3u
#define VDP_SET_TX_ON_SAMPLING_BIT   4u
#define VDP_SET_INIT_ACT_BIT         5u

/* --- COL field bit positions ---------------------------------------------- */
#define VDP_COL_SCHANGE_BIT 0u
#define VDP_COL_SCYCLIC_BIT 1u
#define VDP_COL_TCYCLIC_BIT 2u

/* --- Remove-command flag bit positions ------------------------------------ */
#define VDP_REMOVE_GLOBAL_BIT   2u
#define VDP_REMOVE_DCA_REM_BIT  3u
#define VDP_REMOVE_T_CYCLIC_BIT 4u

/* --- Activation / trigger / ack flag bit positions ------------------------ */
#define VDP_ACT_BIT     2u
#define VDP_TX_TRIG_BIT 2u
#define VDP_ACK_BIT     3u

/* --- Per-slot settings ---------------------------------------------------- */
typedef struct {
    vdp_tres_t tres;
    bool sec;
    bool persist;
    bool tx_on_sampling;
    bool init_act;
} vdp_settings_t;

typedef struct {
    bool on_change;   /* SCHANGE */
    bool cyclic;      /* SCYCLIC */
    uint32_t sct_ms;  /* sampling cycle time */
    bool tx_cyclic;   /* TCYCLIC */
    uint32_t tct_ms;  /* transmission cycle time */
} vdp_collection_t;

typedef struct {
    bool in_use;
    uint16_t slot_id;
    uint16_t dca_rem_id;
    vdp_settings_t settings;
    vdp_collection_t collection;
    bool active;
    int64_t last_sample_ms;
    int64_t next_sample_ms;
} vdp_slot_t;

typedef struct {
    uint16_t slot_id;
    int64_t timestamp_ms;
    uint8_t data[VDP_MAX_SAMPLE_DATA];
    uint8_t data_len;
} vdp_sample_t;

typedef struct {
    uint16_t slot_id;
    vdp_error_code_t code;
} vdp_async_error_t;

#endif /* VDP_TYPES_H */
