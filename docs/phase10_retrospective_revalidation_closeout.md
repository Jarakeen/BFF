# Phase 10 Retrospective Revalidation Closeout

Date: 2026-09-03
Branch: `phase12`

## Why this retrospective was required

Phase 9 corpus hardening changed the authoritative encounter mechanic inputs consumed by Phase 10. The review pass classified 109 raw inferred mechanics, accepted 94 for canonical persistence, rejected 15 as currently inferred, and persisted the accepted rows as `reviewed_single_source` facts with UESP evidence.

Phase 10 therefore required a dependency-impact rerun under the hardened roadmap completion standard. The goal was not to make every encounter fully evaluable. The goal was to prove that real roster evaluation consumes canonical encounter truth, excludes rejected raw inference, preserves unknown/conflicting outcomes, and still completes at least one real encounter end-to-end.

## Canonical mechanic consumption boundary

Focused canonical-boundary audit:

- raw inferred source mechanics: **109**;
- canonical mechanic facts: **94**;
- accepted inferred replacements: **94**;
- rejected/unpersisted inferred: **15**;
- canonical facts without raw inferred source rows: **0**;
- raw inferred downstream leaks: **0**;
- result: **PASS**.

The encounter repository now overlays persisted canonical `mechanic_detail` facts and excludes raw `interpretation_status=inferred` mechanics from downstream evaluation unless a reviewed canonical fact exists.

This preserves raw UESP source data for provenance and future review without allowing unreviewed or rejected inference to masquerade as canonical encounter truth.

## Focused regression checkpoint

The Phase 10 focused regression set completed with:

- **38 passed in 3.34s**.

The tests explicitly protect the canonical mechanic boundary and update historical fixtures to the current `SavedBuildCapabilityAudit` contract.

## Real roster

Authoritative real saved roster used for both retrospective runs:

- **Magrat → DF Healer**;
- **Susan → Necro Tank**.

Both selected builds reported:

- capability-resolution gaps: **0**.

Provider assignment remained outside this validation. Provider rows remained **0**, preserving the Phase 10 / Phase 11 ownership boundary.

## Oaxiltso veteran control run

The historical control encounter was rerun through the hardened canonical path.

Results:

- encounter: **Oaxiltso**;
- difficulty: **veteran**;
- fully evaluable: **true**;
- capability-ready: **true**;
- execution rows: **6**;
- provider rows: **0**;
- Phase 10 exit ready: **true**.

Exit criteria:

- PASS real saved-build data exists;
- PASS at least two unique real roster members selected;
- PASS selected roster has no capability-resolution gaps;
- PASS real roster is capability-ready for the selected real encounter.

This satisfies the real integration gate after the upstream Phase 9 changes.

## Hiath the Battlemaster veteran boundary run

A second reviewed-single-source encounter was deliberately run to verify that unresolved execution semantics remain explicit rather than being guessed.

Hiath has five canonical Phase 10 requirements:

1. Agony → interrupt;
2. Invisibility → positioning;
3. Purifying Light → cleanse;
4. Roll Dodge → movement;
5. Solar Disturbance → interrupt.

Observed execution evaluation:

- **Agony [interrupt]** → COVERED via `core_bash / standard_interrupt_bash`;
- **Invisibility [positioning]** → UNKNOWN because no source-backed execution-method fact is persisted;
- **Purifying Light [cleanse]** → COVERED via `core_action / break_free`;
- **Roll Dodge [movement]** → UNKNOWN because no player movement handling method is source-backed;
- **Solar Disturbance [interrupt]** → COVERED via `core_bash / standard_interrupt_bash`.

Overall:

- fully evaluable: **false**;
- capability-ready: **false**;
- execution rows: **5**;
- provider rows: **0**;
- Phase 10 exit ready for Hiath specifically: **false**.

This result is expected and valid under the hardened Phase 10 contract because the remaining unknowns are explicit and explainable.

### Hiath follow-up boundary

The source text for `Roll Dodge` says that **Hiath performs the roll dodge to avoid incoming damage**. The persisted canonical mechanic currently carries `requires_movement=true`, which Phase 10 interprets as a player movement demand. That reveals an actor-semantics limitation in the current mechanic requirement contract: movement ownership is not represented explicitly.

Phase 10 must not “fix” this by inventing a player action. The row remains UNKNOWN until the canonical encounter schema can distinguish boss-owned movement from player-owned movement or the reviewed canonical fact is corrected through an explicit source-backed review/persistence path.

The source text for `Invisibility` establishes a positioning dependency but there is no persisted `execution_method` fact describing a coarse player handling method. It therefore remains UNKNOWN rather than being derived from prose.

These are data/semantic enrichment follow-ups, not failures of the Phase 10 evaluator. The evaluator is behaving correctly by refusing to guess.

## Corpus after canonical filtering

Current execution-corpus audit after the reviewed mechanic boundary was applied:

- encounters with requirements: **18**;
- fully evaluable encounters: **6**;
- fully ready encounters: **6**;
- covered requirements: **20**;
- unknown requirements: **24**;
- conflicting requirements: **0**.

The reduction from historical raw-inference counts is expected because rejected inferred mechanics no longer flow downstream.

## Retrospective conclusion

Phase 10 satisfies the hardened dependency-impact gate:

- canonical persisted mechanic truth is authoritative downstream;
- rejected raw inference has zero downstream leaks;
- a real two-character saved roster traverses Encounter + Requirements + Roster + Builds successfully on Oaxiltso veteran;
- selected builds have zero capability-resolution gaps;
- provider assignment remains owned by Phase 11;
- a second reviewed-single-source encounter preserves unsupported execution semantics as explicit UNKNOWN outcomes;
- no unknown or rejected mechanic is silently treated as covered, false, or zero-cost.

**Phase 10 retrospective revalidation: PASS.**

Phase 10 may return to **🟢 Complete** under the hardened roadmap standard.
