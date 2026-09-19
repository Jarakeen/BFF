# Phase 14 Comp Maker Rebuild Design

Date: 2026-09-18
Branch: phase14
Status: design contract / implementation target

## Product definition

Comp Maker is a constrained raid-composition adviser.

It accepts an incomplete trial group, respects choices the raid lead has already made,
and helps fill only the unresolved parts of the composition. Its purpose is not to
replace player decisions or manufacture a full raid from nothing.

Canonical workflow:

Raid Plan -> Comp Maker working state -> Raid Plan

The Raid Plan is the durable source of truth. Comp Maker owns recommendations and a
temporary working copy only.

## Primary user story

A raid lead can provide:

- a trial/achievement goal, such as Swashbuckler Supreme;
- only some of the players required for the group;
- known player roles/classes;
- explicit gear choices for any player/chair;
- explicit buff/debuff/provider assignments;
- empty chairs for players still needed.

Comp Maker must accept those facts without overwriting them. It then evaluates the
remaining optimization space and recommends players/classes/build packages/gear for
the unresolved chairs or unresolved gear slots.

Example:

- Tank 1: known player, class locked, gear open
- Tank 2: Recruit, role Tank, gear open
- Healer 1: known player, Warden, SPC + Ozezan locked
- Healer 2: Recruit, healer role, gear open
- DD 1-4: known players
- DD 5-8: Recruit

The healer's SPC + Ozezan choice is a constraint. The optimizer must work around it,
not silently replace it.

## Optimization objective

Do NOT maximize raw effect count.

Optimize for:

1. hard role/chair validity;
2. user-locked decisions;
3. explicitly assigned provider responsibilities;
4. high-priority raid buff/debuff/support coverage;
5. recipient coverage where a provider has limited target capacity;
6. survival/healing constraints;
7. minimal unnecessary duplicate support;
8. support concentrated on tanks/healers where mechanically sensible;
9. at most the support-DD cost actually justified by missing high-value coverage;
10. maximum remaining ordinary-DD damage opportunity;
11. evidence quality and confidence;
12. observed high-end usage as supporting evidence, never as canonical truth.

Encounter-specific optimization can become stricter later when encounter/runtime combat
knowledge is sufficiently complete.

## Non-negotiable behavior

### Locks are sacred

Every independently editable fact can be locked:

- player
- character
- role
- class
- selected saved build
- individual planned gear sets
- provider responsibility
- mechanic/utility assignment

A locked value is never changed by Auto-Fill. The adviser may explain tradeoffs and
offer an alternative, but applying it requires explicit user action.

### Partial rosters are first-class

A 12-person trial plan does not require 12 named players before optimization.

Neutral Recruit chairs remain planning chairs and may carry:

- required role
- required class
- planned gear
- provider responsibilities
- mechanic jobs
- recommendation evidence

Recruit placeholders never become Personnel records.

### Existing gear is accepted

If the user says "this healer is wearing X", Comp Maker treats X as current plan truth.
It evaluates what X contributes, what is still missing, and what the rest of the team
can do around it.

### Evidence does not become authority

ESO Logs, external catalogs, observed builds, and reference templates may propose or
support candidate choices. They do not silently override user choices or canonical game
mechanics.

## Canonical working model

Replace the current collection of parallel UI dictionaries with one typed working model.

Suggested names:

- CompPlanState
- CompChairState
- CompLockState
- CompCandidateOption
- CompTeamEvaluation

### CompPlanState

Fields should include at least:

- raid_plan_id
- raid_plan_name
- trial_id
- difficulty
- achievement_goal
- team_name
- chairs
- dirty
- generation/evaluation metadata

### CompChairState

One record per canonical seat:

- seat_id
- player_name
- character_name
- role
- eso_class
- selected_build_name
- planned_gear_sets
- planned_skills
- planned_mundus
- primary_assignment
- secondary_assignment
- utility_assignments
- lock state
- candidate options
- selected candidate/evidence
- unresolved reasons

The visible table, chair detail panel, Team Health, Save, Coverage handoff, and Auto-Fill
must all read from this same record.

No UI-owned parallel truth is allowed.

In particular, the rebuilt page must not depend on these as authoritative state:

- _comp_applied_candidates
- _comp_manual_gear_sets_by_slot
- _comp_roster_member_by_slot
- generated draft state
- presentation-table text

Compatibility adapters may temporarily populate/read them during migration, but they
must not own decisions.

## Data-source hierarchy

Highest authority first:

1. User-locked Raid Plan decisions
2. Existing Raid Plan assignments/planned gear
3. Explicit saved FoundryDock builds selected for the chair
4. Canonical FoundryDock mechanic/provider/set catalogs
5. Saved ESO Logs catalog evidence
6. Live ESO Logs evidence
7. Versioned curated build/reference sources
8. Other external discovery sources such as ESO-Hub when added

Observed popularity is never equivalent to mechanical validity.

## Existing services to reuse

Do not rebuild these capabilities unless a specific defect is proven.

### Candidate discovery
services.comp_builder_build_candidates

Provides deterministic per-chair candidates from saved builds and reference templates.

### Provider evidence
services.comp_builder_provider_evidence

Canonical provider identities only. Unknown remains unknown.

### Whole-team optimization
services.comp_builder_team_candidate_optimizer

Already owns coherent team candidate selection and hard provider/uniqueness constraints.

### Authoritative prescription materialization
services.comp_builder_authoritative_prescription

May remain as a compatibility/output adapter, but the normal Raid Plan workflow should
not require an intermediate generated draft to preserve page state.

### Team provider recipient coverage
services.team_provider_coverage_service

Use where one source cannot necessarily cover the entire intended recipient set.

### Raid support coverage
services.raid_plan_coverage_scope_service
services.raid_plan_coverage_assignment_service
services.raid_unique_support_set_capability_service
services.raid_named_group_effect_capability_service
services.saved_build_capability_service

These should feed the group evaluation layer rather than being reimplemented in the UI.

### ESO Logs
services.esologs_composition_evidence
ui.comp_builder_esologs_support
existing TopTeamService/catalog machinery

Saved catalog evidence should be preferred when available so ordinary Comp Maker use
does not require a live ESO Logs fetch.

## Provider-local modifiers

Provider ownership must preserve actor identity.

Example: Jorvuld's Guidance modifies eligible Major/Minor buffs and damage shields
applied by the wearer. It is not a team-wide generic duration modifier.

Therefore the team state must be able to express relationships such as:

chair/provider -> effect -> local modifier -> recipients

rather than reducing the group to a set of effect names.

## Priority model

Add an explicit Comp support-priority policy instead of treating every Coverage row as
equally valuable.

Suggested initial levels:

- REQUIRED
- HIGH
- USEFUL
- SITUATIONAL
- INFORMATIONAL

Priority is policy, not canonical game mechanics.

Initially the default 12-player endgame profile may be general-purpose. Later,
trial/achievement/encounter profiles can override priorities and requirements.

Swashbuckler Supreme can therefore start as:

- Dreadsail Reef trial context
- general endgame support priority
- saved/live DSR ESO Logs evidence

and later gain encounter-specific runtime/mechanic constraints without redesigning the
Comp Maker state model.

## Team evaluation output

Comp Maker should produce a team-level explanation with at least:

- high-priority effects covered
- high-priority effects missing
- conditional coverage
- duplicate primary support
- recipient-capacity problems
- assigned provider conflicts
- open player chairs
- open gear/build decisions
- DD support tax
- recommendations that would free an ordinary DD for damage
- evidence/source for each recommendation

The evaluation must distinguish:

- PRESENT
- ASSIGNED + PROVEN
- CONDITIONAL
- MISSING
- DUPLICATED
- AVAILABLE BUT UNASSIGNED
- BLOCKED BY LOCKED CHOICE
- UNKNOWN / INSUFFICIENT EVIDENCE

## UI target

### Top context

- Raid Plan
- Trial / achievement goal
- Difficulty
- plan style/policy if still useful
- Auto-Fill Open Decisions
- Save Plan

For a Raid Plan-bound session, loading a separate Team should not be necessary.

A separate "Load Players" action may remain for an ad-hoc/new composition workflow.

### Left: Team Plan

12 canonical chairs grouped by Tank / Healer / Damage.

Columns should remain concise:

- Player
- Role / Class
- Planned Build / Gear
- Key Responsibility
- Status

Each row should expose lock state without adding a forest of controls.

### Right: Selected Chair Adviser

Show:

- current locked/current choices
- what this chair currently contributes
- recommendation
- alternatives
- gain/loss to the whole team
- evidence source/confidence
- explicit Apply action

Example explanation:

Roaring Opportunist + Jorvuld's Guidance
- gains Major Slayer capability currently missing
- Jorvuld modifies eligible buffs applied by this wearer
- keeps an ordinary DD free for damage gear
- loses Pillager's Profit group-Ultimate support from the current package

The explanation must never claim runtime uptime when only static capability is proven.

### Bottom: Team Health

This reads from CompPlanState only.

It should show:

- Covered
- Missing high priority
- Conditional
- Duplicate
- Open players
- Open gear/build decisions
- Support DD tax / ordinary DDs preserved

It should not maintain its own candidate or gear state.

## Auto-Fill behavior

Rename the conceptual action from "Generate Team Plan" to something like
"Auto-Fill Open Decisions".

Algorithm:

1. Snapshot CompPlanState.
2. Freeze all locked fields.
3. Resolve current coverage and assigned providers.
4. Identify missing high-priority requirements.
5. Build candidate pools only for unresolved fields/chairs.
6. Reject candidates violating hard role/class/player locks.
7. Reject duplicate saved-player assignments.
8. Respect explicit provider ownership first.
9. Rank candidate combinations using high-priority coverage, recipient capacity,
   duplication cost, support-DD tax, evidence quality, then softer style/novelty signals.
10. Return proposed changes plus explanation.
11. Apply only to unlocked fields.
12. Re-evaluate the whole team from the resulting CompPlanState.

Auto-Fill should be deterministic for the same state/evidence/policy.

## Save behavior

Save must serialize CompPlanState directly back into the same Raid Plan.

It must preserve fields Comp Maker does not own, including:

- notes
- utility assignments
- primary/secondary assignments
- other Raid Plan metadata

Normal Raid Plan save must not:

- create a Roster Team
- create Personnel
- require a generated-roster draft
- rename the Raid Plan unexpectedly
- overwrite reusable saved Builds

Generated roster draft storage may remain for compatibility/ad-hoc experiments but is
not the canonical normal save path.

## Legacy quarantine rule

The old Comp Maker implementation must be progressively isolated so it cannot silently
repopulate, overwrite, or reinterpret the new canonical state.

Legacy code may remain temporarily for compatibility, but it must obey these rules:

- old modules are read-only adapters unless explicitly designated otherwise;
- legacy dictionaries and generated-draft state never become authoritative again;
- new UI code must not import legacy presentation helpers directly;
- compatibility bridges may translate old outputs into CompPlanState, but may not write
  around CompPlanState;
- installer order must make the new state/controller layer the final owner of visible
  behavior;
- each migrated feature removes one legacy write path rather than leaving both active;
- deprecated modules should be moved or renamed into an explicit legacy/compatibility
  namespace once callers are reduced enough to do so safely;
- tests must fail if a legacy path mutates Raid Plan or Comp state behind the new
  controller's back;
- generated-roster draft code remains compatibility/ad-hoc tooling only and must not
  participate in the normal Raid Plan -> Comp Maker -> Raid Plan save path;
- final cleanup should delete dead legacy code only after coverage proves no supported
  workflow still depends on it.

The goal is not merely to hide old widgets. The goal is to remove old ownership.

## Migration strategy

Do not rewrite all Comp services at once.

### Stage 1 - canonical working state
Create typed CompPlanState/CompChairState and adapters:

RaidPlan -> CompPlanState
CompPlanState -> RaidPlan

Tests prove exact round-trip preservation of assignments, classes, players, planned
gear, locks, and untouched Raid Plan fields.

### Stage 2 - read-only new page shell
Render current Raid Plan from CompPlanState. No optimization yet.

Prove table, selected-chair detail and Team Health all read the same state.

### Stage 3 - chair edits and locks
Move player/class/gear/build edits into CompChairState. Add dirty/save contract.

### Stage 4 - candidate adviser
Adapt existing candidate discovery and ESO Logs/reference evidence to produce
CompCandidateOption records for the selected chair.

### Stage 5 - group evaluation
Reuse Coverage/provider services to evaluate the current CompPlanState.

### Stage 6 - constrained Auto-Fill
Wire the existing whole-team optimizer to unlocked/open decisions only.

### Stage 7 - quarantine and retire compatibility state
Move remaining old Comp Maker UI/controller paths behind an explicit legacy compatibility
boundary. Remove page dependence on old parallel dictionaries/generated-draft handoff
only after round-trip and optimizer acceptance tests are green. Add regression tests that
prove legacy paths cannot mutate canonical CompPlanState or Raid Plan state behind the
new controller.

### Stage 8 - delete dead legacy ownership
After supported workflows no longer call legacy write paths, remove the dead ownership
code rather than leaving dormant duplicate state machinery in place.

## Acceptance tests

Minimum acceptance cases:

1. Partial roster with 5 known players + 7 Recruit chairs saves/reloads exactly.
2. Locked healer gear remains untouched after Auto-Fill.
3. Locked player/class with open gear receives recommendations only for gear.
4. Open Tank chair may receive class/build/player recommendation without changing
   locked chairs.
5. Existing Major Courage provider remains credited even when that provider is a DD.
6. Missing high-priority coverage is preferred over low-value raw effect count.
7. Duplicate support is surfaced rather than rewarded.
8. One support-DD recommendation is allowed when it is the lowest-cost valid solution.
9. Saved ESO Logs catalog evidence can generate candidates without live network access.
10. ESO Logs popularity cannot override a mechanically invalid candidate.
11. Jorvuld's Guidance affects only eligible buffs/shields applied by its wearer.
12. Team Health, selected-chair adviser, Save and Coverage all agree on the same planned
    gear package.
13. Saving Comp Plan creates no Roster Team and no Personnel record.
14. Save/reload preserves Assignments responsibilities exactly.
15. Coverage opened afterward observes the exact same Raid Plan planned gear and
    assignments.

## Out of scope for the first rebuild pass

- exact combat DPS prediction
- exact encounter uptime
- full Rotation proof
- automatic ESO Logs skill-package application
- automated external-web scraping during every optimization
- declaring observed ESO Logs setups universally optimal
- rewriting existing canonical mechanic services

### Later enhancement: ESO Logs skill evidence

The existing Comp/ESO Logs path has historically captured observed skills as well as
gear. Preserve that capability for a later improvement after the new state boundary is
stable.

Later behavior should:

- attach observed skill packages to CompCandidateOption evidence;
- show which skills are commonly observed for the selected chair/build;
- use skill overlap as candidate-fit evidence where appropriate;
- never treat observed skills as canonical mechanics or proof of optimal rotation;
- never overwrite a locked or explicitly planned skill package;
- require explicit user action before observed skills are copied into CompPlanState;
- hand accepted planned skills to Rotation Builder as planning input, where runtime
  cadence/uptime can be evaluated separately.

These can be layered in after the state boundary is trustworthy.

## Architectural principle

Comp Maker recommends.

Raid Plan decides.

Coverage audits.

Rotation proves execution.

Those boundaries must remain distinct even when the services share evidence.
