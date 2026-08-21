---
name: read-documentation
description: 'Enables the AI to read project documentation from the docs, requirements, and standards folders. Use when answering questions about the system architecture, design, stakeholder requirements, or engineering standards that live in this repository.'
---

# Read Documentation

## When to Use

- User asks a question about the system's design, architecture, or intended behavior
- User asks what a requirement, standard, or specification says
- A task needs grounding in documented decisions before writing code or other docs
- You need authoritative, in-repository source material to answer accurately

## Documentation Folders

| Folder | What lives here |
|--------|-----------------|
| `docs/` | System documentation organized by architectural views (see below) |
| `requirements/` | Stakeholder and system requirements (e.g. `stakeholder-requirements.md`) |
| `standards/` | Engineering standards, conventions, and compliance rules the project must follow |

### `docs/` architectural views

The `docs/` folder follows the 4+1 view model. Consult the view that matches the question:

| View | Answers questions about |
|------|-------------------------|
| `docs/logical view/` | Functional structure — components, responsibilities, relationships |
| `docs/development view/` | Code organization, modules, build structure, developer concerns |
| `docs/process view/` | Runtime behavior — concurrency, processes, data flow, timing |
| `docs/physical view/` | Deployment — hardware, nodes, infrastructure mapping |
| `docs/scenarios/` | End-to-end scenarios and use cases that tie the views together |

## Procedure

1. **Identify the relevant folder(s)** from the tables above based on the user's question:
   - Architecture / design → `docs/` (pick the matching view)
   - What the system must do / stakeholder needs → `requirements/`
   - Rules, conventions, compliance → `standards/`

2. **Discover the files** in the target folder before reading. List the folder contents so you read the right documents and do not miss related files.

3. **Read the documentation** thoroughly. Prefer reading a whole document (or a large section) over many small reads so you capture full context.

4. **Cross-reference when needed.** A question may span folders — for example, a requirement in `requirements/` may be realized in a `docs/` view and constrained by a rule in `standards/`. Read all relevant sources before concluding.

5. **Answer using what the documentation says**, and cite the specific file(s) and section(s) you relied on so the user can verify.

## Rules

- Ground answers in the documentation — do not invent facts that are not written down.
- If the documentation is silent, incomplete, or contradictory on a point, say so explicitly rather than guessing.
- This skill is read-only. Do not edit, move, or commit any files while reading.
- Quote or reference the source file and section when the answer depends on it.
- If several documents disagree, surface the conflict and point to each source.

## Failure Messages

- Empty or missing docs: "I looked in `<folder>/` but found no documentation covering that topic. The file may not exist yet, or the folder is empty."
- Ambiguous request: "Your question could map to more than one area (docs, requirements, or standards). Which one should I read from — or should I check all of them?"
