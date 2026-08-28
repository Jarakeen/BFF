# BFF instructions for Claude

## Current development
- Primary development branch: `phase2`.
- Do not create/switch to throwaway branches unless explicitly requested.
- Preserve the existing architecture and make focused changes.
- The ESO database (`data/eso.db`) is the mechanical source of truth.
- `math/` contains collected ESO math references. Treat them as reference evidence; do not replace them with guessed formulas.

## Legacy / out-of-scope material
Do NOT spend time hunting, restoring, or repairing these unless the user explicitly asks:
- `old_pages` and other removed/legacy UI modules. They are not the current application architecture.
- ESO Logs/raw log archives, `data/backup/`, `data/raw/`, or large normalized log JSON files. These are data artifacts, not prerequisites for current Builds/MinMax work.
- Historical Phase 5 branches are reference/history only unless a task explicitly names one.

For current build/skill work, start with the active services, models, UI, tests, and `data/eso.db`.

## Testing
- Do not assume a missing legacy module is a current implementation dependency.
- Do not broaden a task into unrelated test repair.
- When pytest reports missing `old_pages` modules or ESO Logs/network failures, classify them as unrelated/pre-existing unless the current change introduced the dependency.
- Prefer focused tests for the code being changed, followed by the configured project suite.
- Do not modify `pytest.ini` merely to make a new test directory count as part of the suite without first establishing that the directory is intentionally part of the project's official testpaths.

## Skills
- Base skill and both morphs are distinct selectable abilities.
- `base_ability_id` identifies the skill family.
- `ability_id` identifies the exact selected ability/morph.
- Never use a base skill name in place of a morph name when the selected `ability_id` is a morph.
- Do not hard-code skill or morph names; resolve them from the database.
