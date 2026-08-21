---
name: update-documentation
description: 'Enables the AI to update documentation in current repository. The AI can edit and commit changes to documentation files in the repository to answer user questions.'
---

# Update Documentation

## When to Use

- User asks to add, edit, correct, or improve documentation in this repository
- New knowledge or findings need to be captured in the repository's docs
- Existing documentation is outdated, incomplete, or inconsistent and must be fixed
- User wants a documentation change committed to the repository

## Scope

- **In scope**: Markdown and documentation files that live inside the current repository — for example `README.md`, files under `knowledge/`, `docs/`, and skill/agent documentation under `.agents/`.
- **Out of scope**: Cloned external repositories under `knowledge/references/*/repo/` — these are read-only. To read from them, use the `read-documentation` skill instead. Never edit or commit inside those `repo/` subfolders.

## Procedure

1. **Locate the documentation** to change based on the user's request. Search the repository for the relevant file(s) before editing. If the target is ambiguous, ask the user to confirm which file(s) to update.

2. **Read the file first** so edits preserve existing structure, tone, and formatting. Never edit a file you have not read.

3. **Make the edit** using the file editing tools:
   - Keep changes focused on what the user requested.
   - Match the existing Markdown style (heading levels, tables, code fences, list markers).
   - Do not reformat or rewrite unrelated sections.

4. **Review the change** by inspecting the diff to confirm only the intended content changed.
   ```bash
   git status
   git diff
   ```

5. **Commit the change** only after the user confirms, or when the user explicitly asked for the change to be committed.
   ```bash
   git add <path-to-doc>
   git commit -m "docs: <concise summary of the change>"
   ```
   - Use a clear, conventional commit message (`docs:` prefix) describing the update.
   - Stage only the documentation files you changed — never use `git add -A` blindly.

6. **Report** the file(s) changed and, if committed, the commit summary back to the user.

## Rules

- **Never edit files inside `knowledge/references/*/repo/`** — those are cloned upstream repositories and are read-only.
- Only edit documentation files that already exist unless the user explicitly asks for a new document.
- Do not commit unrelated changes; stage and commit only the documentation you edited.
- Do **not** push (`git push`) unless the user explicitly asks you to.
- Never force-push, reset, amend published commits, or rewrite history.
- Preserve existing formatting conventions; keep edits minimal and on-topic.
- If content depends on facts from an external repository, use the `read-documentation` skill to verify before writing.

## Failure Messages

- Edit target unclear: "I could not determine which documentation file to update. Please tell me the file path or section you want changed."
- Commit failure: "I could not commit the documentation change. `git commit` failed — please check the repository state (e.g. merge conflicts, unstaged changes, or hooks)."
- Read-only violation: "That file lives inside a cloned reference repository (`knowledge/references/<folder>/repo/`), which is read-only. I can read it, but I cannot edit or commit changes there."
