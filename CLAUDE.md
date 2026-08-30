# BFF instructions for Claude

## Current development
- Primary development branch: `phase2`.
- Do not create/switch to throwaway branches unless explicitly requested.
- Preserve the existing architecture and make focused changes.
- Start from the smallest active dependency chain that can answer the task.
- Do not inspect unrelated subsystems merely because they exist in the repository.
- The ESO database (`data/eso.db`) is the mechanical source of truth.
- `math/` contains collected ESO math references. Treat them as reference evidence; do not replace them with guessed formulas.

## Default Phase 2 search scope
For normal Builds/MinMax work, start with:
- `minmax/`
- `models/`
- directly relevant `services/`
- `widgets/`
- `ui/`
- relevant tests
- `data/eso.db`
- `math/`

Only expand beyond this scope when the active code proves a dependency exists or the user explicitly asks.

Do NOT perform broad searches for:
- `old_pages` or removed/legacy UI
- ESO Logs/raw log archives
- `data/backup/`
- `data/raw/`
- large normalized log JSON files
- historical/backup branches

These are not prerequisites for current Builds/MinMax work. Do not hunt, restore, or repair them unless explicitly requested or a direct active dependency requires it.

## Testing
- Do not assume a missing legacy module is a current implementation dependency.
- Do not broaden a task into unrelated test repair.
- When pytest reports missing `old_pages` modules or ESO Logs/network failures, classify them as unrelated/pre-existing unless the current change introduced the dependency.
- Prefer focused tests for the code being changed, followed by the configured project suite.
- Do not modify `pytest.ini` merely to make a new test directory count as part of the suite without first establishing that the directory is intentionally part of the project's official testpaths.

## Phase 2 character foundation
- A fully leveled character has a fixed pool of 64 attribute points split among Health, Magicka, and Stamina.
- Attribute points do not continue increasing after the 64-point pool is spent.
- Character level and Champion Points are separate progression concepts.
- CP earning/progression speed is out of scope for MinMax; current CP state is what matters.
- Champion Points cap at 3600.
- Only four slottable CP abilities may be active in each of Blue, Red, and Green at once; purchased passive CP remains separate from active slots.
- Do not invent or hard-code unverified CP earning mechanics.

## Ability scaling
Keep these scaling rules distinct:
- explicit Health scaling
- explicit Magicka scaling
- explicit Stamina scaling
- `HIGHEST_RESOURCE`: highest of Magicka and Stamina
- `HIGHEST_ATTRIBUTE`: highest of Health, Magicka, and Stamina
- fixed/non-attribute scaling

Do not assume every damage or healing ability uses the same scaling rule. Resolve special cases from ability data/reference evidence.

## Combat environment
- PvE is the current optimization target.
- PvP optimization is out of scope for now, but the data model must not assume all effects are universally active.
- Preserve the ability to represent effects restricted to monsters, players, PvE, PvP, or campaign-specific environments.
- Vengeance/campaign-specific content should be treated as environment restrictions, not as ordinary universal effects.

## Skills
- Base skill and both morphs are distinct selectable abilities.
- `base_ability_id` identifies the skill family.
- `ability_id` identifies the exact selected ability/morph.
- Never use a base skill name in place of a morph name when the selected `ability_id` is a morph.
- Do not hard-code skill or morph names; resolve them from the database.
