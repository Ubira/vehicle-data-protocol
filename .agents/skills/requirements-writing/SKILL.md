---
name: requirements-writing
description: >
  Guidance for writing, reviewing, and classifying software requirements in
  automotive projects. Covers ASPICE SWE.1 compliance, tier classification,
  FMEA/TARA traceability, testability, and quality criteria. Use this skill
  when writing new requirements, reviewing existing ones, classifying tiers,
  or checking requirement quality. Triggers: write requirement, requirement
  quality, tier classification, SWR review, testable requirement, requirement
  guidance, ASPICE SWE.1, requirement traceability.
---

# Requirements Writing Guidance

This document defines how to write, classify, review, and trace software
requirements for automotive embedded systems. It is both a human-readable
guide and an AI-usable reference.

---

## 1. Requirement Structure (sphinx-needs format)

```markdown
:::{sw_req} <Title in imperative or gerund form>
:id: SWR_<DOMAIN|COMPONENT>_<NNN>
:version: 1
:status: <Draft | Approved>
:derives: <LF_ID or parent requirement>
:verification: <T | I | A | D>
:tier: <emoji> <TIER>
:regulation: §<clause>        ← only if tier is 🔒 REG
:fmea: <FMEA-ID>             ← only if requirement mitigates a failure mode

<Single paragraph. One "shall" statement. Testable. Unambiguous.>
:::
```

**Function requirement template** (includes Rationale and ACs):

```markdown
:::{func_req} <Title — descriptive, no regulation ID>
:id: FUN_<DOMAIN>_<NNN>
:version: 1
:status: <Draft | Approved>
:derives: <SF_ID>
:regulation: §<clause>
:allocated_to: <LF_ID, LF_ID, ...>
:verification: <T | I | A | D>

The function shall <single obligation>.

**Rationale:** <Why this requirement exists — regulatory, safety, or
architectural motivation. Explains the "why" beyond what the regulation
field alone conveys.>

**Acceptance Criteria:**
1. <testable condition>
2. <testable condition>
:::
```

### Field reference

| Field | Purpose | Mandatory |
|-------|---------|-----------|
| `id` | Unique identifier, never reused | Yes |
| `version` | Integer version, increment on obligation change | Yes |
| `status` | Document maturity (Draft or Approved) | Yes |
| `derives` | Traces UP to logical function or parent req | Yes |
| `verification` | How it will be verified (see §7) | Yes |
| `tier` | Classification (see §3) | SWR only |
| `regulation` | Regulation clause creating the obligation | Only for 🔒 REG |
| `allocated_to` | Logical function(s) that realize this req | FUN only |
| `fmea` | FMEA entry this requirement mitigates | When applicable |
| `asil` | ASIL level (QM/A/B/C/D) | When ASIL > QM |
| `safety_goal` | Parent safety goal ID | When ASIL > QM |
| `safe_state` | Reference to defined safe state | When leading to safe state |

### 1.1 Function requirements vs SW requirements

| Aspect | Function Requirement (FUN) | SW Requirement (SWR) |
|--------|--------------------------|----------------------|
| **ID format** | FUN_\<DOMAIN\>_NNN | SWR_\<DOMAIN\|COMPONENT\>_NNN |
| **Scope** | One requirement per capability / function | One requirement per single testable behaviour (covers both service-level and app-component-level) |
| **Body structure** | Shall → Rationale → Acceptance Criteria | Shall statement only |
| **Rationale** | Always included — explains "why" | Not included (obligation is self-evident at component level) |
| **Acceptance Criteria** | Numbered ACs (function reqs scope broad capabilities) | No ACs — split into separate SWRs instead |
| **Subject** | "The \<function\> shall…" | "DM shall…" (the specific component) |
| **Traces up** | `:derives:` → System Function (SF) | `:derives:` → Function Requirement or LF |
| **Traces down** | `:allocated_to:` → Logical Function (LF) | — (SWR is the leaf) |

**Rules:**
- If you find yourself writing ACs on a SWR, each AC should become its own
  requirement. ACs are only appropriate at function level.
- Rationale at function level explains the "why" beyond the `:regulation:` field.
  Even when regulation is the driver, rationale should explain the *consequence*
  if the requirement is not met.
- SWR subsumes both service-level (`SWR_COMM_001`) and app-component-level
  (`SWR_ENV_SENSOR_001`) requirements. The former `comp_req`/CMP_ type is
  collapsed into `sw_req`/SWR_.

### 1.2 Requirement versioning

Each requirement carries a `:version:` field (integer, starting at 1).

**Increment when:** The obligation changes — new condition added, threshold
changed, behaviour added or removed.

**Do NOT increment for:** Editorial fixes, typo corrections, wording
clarification that does not change testable meaning.

**Versioning enables:**
- Traceability to specific baselines
- Identifying which requirements need re-verification after change
- Release scoping documents referencing a specific version

### 1.3 Status semantics

| Status | Meaning |
|--------|---------|
| **Draft** | Being written or revised, not yet reviewed |
| **Approved** | Reviewed, approved, baselined — mandatory |

Implementation tracking (not_started / in_progress / done) belongs in ALM
tooling (e.g., Jira), not in the requirement specification. An approved
requirement is mandatory regardless of implementation state.

---

## 2. Writing Rules

### 2.1 The single-shall rule

Each requirement shall contain exactly **one** "shall" statement. If you find
yourself writing "and shall" or multiple sentences with "shall", split into
separate requirements.

**Exception:** A condition + consequence pair is acceptable as one requirement:
> "When X occurs, DM shall do Y."

But NOT:
> ~~"DM shall do Y and shall also do Z."~~ → Split into two SWRs.

### 2.2 Subject clarity

The subject of "shall" must be the component this SWRS belongs to.
- ✅ "DM shall persist the counter in NVM."
- ❌ "The ECU shall expose data via UDS." → This is a system-level requirement.

If the subject is another component, the requirement belongs elsewhere (system
requirements, interface spec, or supplier contract).

### 2.3 Testability

Every requirement must be verifiable. Ask: *"Can I write a test that passes
if and only if this behaviour is implemented correctly?"*

- ✅ "DM shall trigger an event upload within 3 minutes of the triggering event."
- ❌ "DM shall handle events efficiently." → Not measurable.

### 2.4 No implementation detail in SWRS

SWRS defines **what** the system shall do. **How** it does it belongs in SWDD.

- ✅ SWRS: "DM shall persist interval counters across power cycles."
- ✅ SWDD: "Counters stored in `/data/dm/interval.bin` using CRC32-protected binary format."

### 2.5 Redundancy avoidance

Before adding a requirement, check if the obligation is already covered by an
existing SWR. If it is, don't repeat it — even in a different section. Instead,
reference the existing SWR in prose.

### 2.6 Deviation vs requirement

If a requirement documents something you intentionally do NOT do (or do
differently), it should reference a SWDR (Software Deviation Report) and be
tier `💡 REF`. It must still contain a "shall" — describing what you SHALL do
as the placeholder/alternative.

---

## 3. Tier Classification

Every requirement has exactly one tier. The tier answers: *"Why does this
requirement exist?"*

| Emoji | Tier | Meaning | When to use |
|-------|------|---------|-------------|
| 🔒 | REG | Regulation-mandated | The regulation **explicitly states** this obligation. If you removed the clause, this requirement would disappear. |
| 📐 | ARCH | Architecture decision | Our **design choice** to fulfil a need. Regulation may mandate the outcome, but the specific mechanism is ours. |
| 🛡️ | FMEA | FMEA-driven | Exists solely to mitigate a failure mode identified in the FMEA. Without the FMEA entry, this requirement would not exist. |
| 💡 | REF | Reference / informational | Placeholder, deviation, or observability feature. Not strictly necessary for compliance but aids development. |

### 3.1 The REG litmus test

Before tagging a requirement `🔒 REG`, ask:

1. Can I quote the **exact regulation text** that mandates THIS behaviour?
2. Does the regulation specify the **mechanism**, or just the **outcome**?

If the regulation says "data shall be uploaded within 24 hours" → the upload
deadline is `🔒 REG`. But "use NVM to ensure no data loss" is `📐 ARCH`
because the regulation says "ensure no data loss" — NVM is our choice.

### 3.2 Common misclassifications

| Requirement pattern | Often tagged | Should be |
|---|---|---|
| "Read X from CarConfig" | REG | **ARCH** — regulation says use correct variant; how we determine it is our choice |
| "Persist to NVM before upload" | REG | **ARCH** — regulation says don't lose data; NVM is our mechanism |
| "Retain until backend ACK" | REG | **ARCH** — regulation says ensure delivery; retention strategy is ours |
| "Set DTC on failure" | REG | **ARCH** or **FMEA** — regulation doesn't mandate our DTC strategy |
| "Expose counter via DID" | REG | **REF** — observability, not a regulatory obligation |

### 3.3 Regulation reference format

When `:regulation:` is present, use the format `§<Annex>.<Section>.<Subsection>`:
- ✅ `§JD.4.2.1`
- ❌ `JD 4.2.1` or `Annex JD, section 4.2.1`

---

## 4. Traceability Connections

Requirements do not exist in isolation. They connect to artefacts above and
below in the V-model.

### 4.0 Architecture View Context (1+5 → ASPICE)

Requirements are derived through the 1+5 architecture views, which map
directly to ASPICE processes:

```
┌─────────────────────┬──────────────────────┬─────────────────────────┐
│ 1+5 View            │ ASPICE Process       │ Produces                │
├─────────────────────┼──────────────────────┼─────────────────────────┤
│ Operational View    │ SYS.1 Stakeholder Req│ Scenarios, use cases    │
│ Capability View     │ SYS.2 System Req     │ Capabilities, functions │
│ Logical View (LC+LF)│ SYS.3 System Arch   │ Logical decomposition   │
│ LF → SWR allocation│ SWE.1 SW Req         │ Software requirements   │
│ Physical View       │ SWE.2 SW Arch        │ SWAD                    │
│ Detailed View       │ SWE.3 SW Design      │ SWDD                    │
└─────────────────────┴──────────────────────┴─────────────────────────┘
```

**Derivation chain:**
```
Regulation
    ↓ (mandates)
Operational scenario  [Op View — what the system must do]
    ↓ (realizes)
System Function (SF)  [Cap View — observable system behaviour]
    ↓ (decomposes into)
Logical Component (LC) + Logical Function (LF)  [Log View]
    ↓ (:derives: on FUN_)
Function Requirement (FUN)  ← function architect scope
    ↓ (:derives: on SWR)
Software Requirement (SWR)  ← component developer scope
    ↓ (:verifies: on test)
Test Case
```

**Key rules:**
- Every SWR traces UP to an LF via `:derives:` (ASPICE bidirectional
  traceability between SWE.1 ↔ SYS.3).
- If no LF exists for a requirement, either (a) the LF is missing from the
  Logical View and should be added, or (b) the requirement is orphaned and
  its justification must be documented.
- The Physical and Detailed views produce architecture/design documents
  (SWAD, SWDD), not requirements.

---

### 4.1 Traceability diagram

```
Regulation / Stakeholder Need
       │
       ▼ (creates obligation)
System Function (SF)
       │
       ▼ (:derives: on FUN_)
Function Requirement (FUN)
       │
       ├──▶ :allocated_to: → LF (logical function realizing it)
       │
       ▼ (:derives: on SWR)
Software Requirement (SWR)
       │
       ├──▶ SWDD (design detail, :implements: SWR)
       ├──▶ FMEA (mitigation evidence)
       ├──▶ TARA (cybersecurity control)
       └──▶ Test Case (:verifies: SWR)
```

### 4.2 Upward traceability (`:derives:`)

Every requirement must trace UP via `:derives:`:
- **FUN_** traces to a System Function (SF) or safety requirement
- **SWR_** traces to a Function Requirement (FUN_) or Logical Function (LF)

This answers: *"What higher-level need does this satisfy?"*

### 4.3 FMEA traceability (`:fmea:`)

When a requirement **mitigates** a failure mode:
- Add `:fmea: FMEA-XX-NNN` to the SWR
- In the FMEA document, list the SWR in the "Current Controls" field

**Direction:** Bidirectional.
- SWR → FMEA: "I mitigate this failure"
- FMEA → SWR: "This control covers me"

**Key principle (from DIR FMEA review):**
> If an FMEA recommended action restates what a requirement already demands,
> the action is redundant. The requirement should be listed in "Current
> Controls" instead. If no requirement exists → create one to make it traceable.

### 4.4 FMEA coverage levels

Not all FMEA mitigations become requirements. Three coverage levels exist:

| Level | Meaning | Where documented |
|-------|---------|-----------------|
| **SWR** | Mitigation creates observable behaviour or interface contract | SWRS (`:fmea:` field) |
| **SWD** | Mitigation is an internal design choice within an existing SWR | SWDD section |
| **Test** | Mitigation is a verification activity | SWTD test case |

### 4.5 TARA traceability

When a requirement implements a cybersecurity control identified in TARA:
- Add `:tara: TARA-XX-NNN` to the SWR
- Reference the cybersecurity goal (`:cybersecurity_goal: CSG-ID`) if applicable
- The TARA document should list the SWR as evidence of control implementation

**Cybersecurity requirement examples:**
- "DM shall reject diagnostic write requests from unauthenticated sessions."
- "DM shall verify SecOC authenticity on safety/security-relevant signal groups before accepting data."
- "DM shall log failed authorization attempts with timestamp and source identity."

**Verification for cybersecurity:** Beyond functional tests, consider penetration
testing, fuzzing, interface misuse tests, and static analysis (these map to
verification method `T` or `A` depending on scope).

### 4.6 Regulation traceability

For `🔒 REG` requirements, the `:regulation:` field provides direct forward
traceability from the design to the regulation clause. This enables auditors
to verify: "For each regulatory obligation, show me the requirement that
satisfies it."

---

## 5. Safety and ASIL Requirements (ISO 26262)

Safety requirements follow the ISO 26262 decomposition chain:
```
HARA → Safety Goal → FSR → TSR → SW Safety Requirement
```

### 5.1 Additional fields for safety-related requirements

```markdown
:asil: <QM | ASIL-A | ASIL-B | ASIL-C | ASIL-D>
:safety_goal: <SG-ID>
:safe_state: <reference to defined safe state>
```

### 5.2 Safety requirement rules

- **ASIL inheritance:** SW safety requirements inherit ASIL from parent TSR
  unless ASIL decomposition is applied (document decomposition explicitly).
- **Fault detection + reaction:** Safety requirements typically come in pairs:
  one for detecting the fault, one for the reaction (including timing).
- **Timing:** Safety requirements with timing constraints must state both the
  deadline and the reference point (e.g., "within 50 ms of fault detection").
- **Safe state:** Requirements leading to safe state must reference the defined
  safe state and the transition mechanism.

### 5.3 Safety requirement examples

```markdown
:::{sw_req} Transition to SafeState on heartbeat loss
:id: SWR_XX_080
:status: implemented
:derives: TSR-042
:verification: T
:tier: 🛡️ FMEA
:asil: ASIL-B
:safe_state: SS-01
:fmea: FMEA-XX-015

When heartbeat supervision detects loss of dependency X for more than
100 ms, Component shall transition to SafeState SS-01 within 50 ms.
:::
```

```markdown
:::{sw_req} Reject safety input with invalid E2E status
:id: SWR_XX_081
:status: implemented
:derives: TSR-043
:verification: T
:tier: 🛡️ FMEA
:asil: ASIL-B
:fmea: FMEA-XX-016

Component shall discard safety-related input signals with E2E protection
status ≠ OK and use the last valid value for no longer than the configured
fault tolerance time (default 100 ms).
:::
```

### 5.4 Safety vs FMEA tier

- Use `🛡️ FMEA` tier when the requirement exists primarily to mitigate a
  failure mode (regardless of whether it also has an ASIL).
- Add `:asil:` field to indicate the integrity level, even on FMEA-tier reqs.
- A requirement can be `🔒 REG` tier AND have `:asil: ASIL-B` — the tier
  indicates the primary driver; ASIL is an additional constraint.

---

## 6. Non-Functional Requirement Patterns

Non-functional requirements constrain HOW well the system performs, not WHAT
it does. They are still testable and must follow the same structure.

### 6.1 Common categories

| Category | Example pattern |
|----------|----------------|
| **Timing** | "shall complete X within N ms of Y" |
| **Resource** | "shall not exceed N MB / N% CPU" |
| **Startup** | "shall be operational within N ms of PlatformState RUN" |
| **Persistence** | "shall recover state after controlled and uncontrolled power loss" |
| **Availability** | "shall operate in degraded mode when dependency Z is unavailable" |
| **Robustness** | "shall reject malformed input and continue operation" |

### 6.2 Examples

```
Bad:    "DM shall start quickly."
Better: "DM shall complete initialization within 500 ms."
Best:   "DM shall complete initialization and report RUNNING to SFW
         within 500 ms of receiving PlatformState RUN."
```

```
Bad:    "DM shall use reasonable storage."
Better: "DM shall not exceed 20 MB persistent storage."
Best:   "DM shall not exceed 20 MB persistent storage for retained
         payloads; buffer capacity is configurable at build time."
```

### 6.3 Verification of non-functional requirements

| Category | Typical method |
|----------|---------------|
| Timing | T (instrumented test) or A (worst-case analysis) |
| Resource | T (profiling) or A (static analysis) |
| Persistence | T (power-cycle test) |
| Robustness | T (fault injection, fuzzing) |

---

## 7. Verification Methods (ASPICE SWE.4 / ISO 26262)

The `:verification:` field specifies HOW the requirement will be verified:

| Code | Method | When to use |
|------|--------|-------------|
| **T** | Test | Behaviour can be stimulated and observed in a test environment |
| **I** | Inspection | Verified by reviewing code, documents, or configuration |
| **A** | Analysis | Verified by reasoning, calculation, simulation, or static analysis |
| **D** | Demonstration | Verified by showing correct operation under defined conditions |

> **Note:** Behavioural requirements should normally use `T` or `D`. Use `I`
> only for structural/process requirements. Use `A` for timing analysis,
> resource calculations, or formal verification.

### 7.1 Test levels and requirement mapping

| Test level | Scope | Typical SWR tier | ASPICE process |
|------------|-------|------------------|----------------|
| Unit test | Single function/module in isolation | ARCH, FMEA | SWE.4 |
| Component test | Single component, mocked dependencies | ARCH, REG | SWE.4 |
| Integration test | Multiple components, real interfaces | ARCH, REG | SWE.5 |
| Qualification test | Full SW against requirements | REG | SWE.6 |

### 7.2 Test case naming convention

Test names should reference the SWR they verify:
```
ut_<section>_<swr_number>_<behaviour_description>
it_<swr_number>_<scenario>
st_<regulation_clause>_<scenario>
```

Examples:
- `ut_s05_042_payload_retained_until_ack`
- `it_054_upload_failure_triggers_degraded`
- `st_jd421_event_upload_within_3min`

### 7.3 FMEA action → test connection

FMEA Verification actions (V-type) map directly to test cases:
- Each V-type action should have at least one test case
- The FMEA traceability matrix documents this mapping
- Priority: P1 Verification actions must have tests before release

### 7.4 Coverage expectations

| Tier | Expected test coverage |
|------|----------------------|
| 🔒 REG | Must have explicit test(s) — regulatory evidence |
| 📐 ARCH | Should have test(s) — design validation |
| 🛡️ FMEA | Must have test(s) — FMEA mitigation evidence |
| 💡 REF | Inspection sufficient unless behaviour is critical |

---

## 8. Quality Checklist (for review)

Use this checklist when reviewing requirements:

### 8.1 Individual requirement quality

- [ ] Single "shall" statement (no bundling)
- [ ] Subject is this component (not another)
- [ ] Testable — pass/fail criteria are clear
- [ ] No implementation detail (WHAT not HOW)
- [ ] Tier correctly assigned (passes litmus test §3.1)
- [ ] `:derives:` traces to a logical function or parent requirement
- [ ] `:verification:` method is appropriate
- [ ] Not redundant with another SWR

### 8.2 Document-level quality

- [ ] No orphan requirements (every SWR traces up AND has verification)
- [ ] Consistent terminology (use glossary terms)
- [ ] Tier emoji format consistent (`🔒 REG` not `REG`)
- [ ] Requirement IDs are unique and never reused
- [ ] Regulation references use `§X.Y.Z` format
- [ ] FMEA traceability is bidirectional where applicable
- [ ] No system-level requirements masquerading as SW requirements
- [ ] Revision history is up-to-date

### 8.3 Completeness check

- [ ] Every regulation clause in scope has at least one SWR
- [ ] Every FMEA P1 Design action has a covering SWR
- [ ] Every `🔒 REG` and `🛡️ FMEA` requirement has a test case
- [ ] Interface assumptions are documented (or moved to system level)

---

## 9. ASPICE Alignment

This guidance supports the following ASPICE processes:

| Process | How this guidance supports it |
|---------|-------------------------------|
| **SWE.1** (SW Requirements Analysis) | Requirement structure, quality rules, traceability |
| **SWE.2** (SW Architectural Design) | ARCH tier → design decisions documented in SWRS/SWDD |
| **SWE.3** (SW Detailed Design and Unit Construction) | Clear boundary: SWRS = what, SWDD = how |
| **SWE.4** (SW Unit Verification) | Verification method, test naming, coverage expectations |
| **SWE.5** (SW Integration and Integration Test) | Integration test level mapping |
| **SWE.6** (SW Qualification Test) | Qualification test mapping for REG requirements |
| **MAN.5** (Risk Management) | FMEA/TARA traceability |

### 9.1 Bidirectional traceability (ASPICE base practice)

ASPICE requires bidirectional traceability. This guidance ensures:
- **Up:** SWR → LF → Regulation (`:derives:` + `:regulation:`)
- **Down:** SWR → SWDD section → Code → Test case
- **Lateral:** SWR ↔ FMEA (`:fmea:` field + Current Controls)

---

## 10. Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| "DM shall handle errors gracefully" | Not testable | Specify exact behaviour for each error |
| Multiple shalls in one SWR | Untestable as unit, unclear scope | Split into separate SWRs |
| ECU obligation in SW spec | Wrong owner | Move to system-level requirements |
| REG tier for design choices | Misleads auditors, over-constrains | Reclassify to ARCH |
| FMEA action duplicates a requirement | Maintenance burden, confusion | Remove action, add SWR to Current Controls |
| Vague "shall not" without observable condition | Not testable, too broad | Acceptable if the forbidden condition is observable and verifiable; otherwise rewrite as positive obligation |
| Requirement with no test | Unverifiable claim | Add test or change verification to I/A/D |
| Design detail in SWRS | Over-constrains implementation | Move to SWDD, keep SWRS abstract |
| Regulation ID in title | Redundant — `:regulation:` field handles traceability | Use descriptive titles (what it does, not which clause) |

---

## 11. Workflow: Adding a New Requirement

1. **Identify the need** — What obligation, failure mode, or security threat creates this?
2. **Check for duplicates** — Does an existing SWR already cover this?
3. **Write the SWR** — One shall, correct subject, testable
4. **Classify tier** — Apply litmus test (§3.1)
5. **Add traceability** — `:derives:`, `:fmea:`, `:regulation:` as applicable
6. **Set verification method** — T/I/A/D
7. **Update FMEA** — If FMEA-driven, add SWR to Current Controls
8. **Write/plan test** — If verification = T, ensure test case exists or is planned
9. **Peer review** — Use quality checklist (§8)

---

## 12. Glossary of Tier Decisions (examples)

These examples from the China 7 DataManager SWRS illustrate tier decisions:

| Requirement | Tier | Reasoning |
|---|---|---|
| "Upload within 3 minutes of event" | 🔒 REG | Regulation JD.4.2.1 explicitly states this deadline |
| "Persist payload to NVM before upload" | 📐 ARCH | Regulation says "ensure data is not lost" — NVM is our choice |
| "Set DTC on buffer full" | 📐 ARCH | Our observability strategy, not regulation-mandated |
| "Expose late-event counter via DID" | 💡 REF | Diagnostic observability, not required for compliance |
| "Enter DEGRADED on dependency failure" | 🛡️ FMEA | Exists to mitigate FMEA-DM-003 (subscription loss) |
| "Read CarConfig to select JD.9 variant" | 📐 ARCH | Regulation mandates correct variant; our mechanism is CarConfig |

**Cross-project examples (DIR/SWEPAC):**

| Requirement | Tier | Reasoning |
|---|---|---|
| "Abort on unavailable safety signal" | 🛡️ FMEA | Exists to mitigate FMEA-005; without FMEA entry this would not exist |
| "Limit recovery attempts to 2 consecutive" | 📐 ARCH | Addresses safety need; specific limit is our design choice |
| "Report E2E timeout via DTC within 100 ms" | 🔒 REG | Safety concept mandates detection time budget explicitly |
| "Log state transitions to DLT" | 💡 REF | Observability for development/service; not compliance-critical |