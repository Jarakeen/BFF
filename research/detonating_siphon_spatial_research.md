# Detonating Siphon Spatial Research

## Status

Production geometry remains fail-closed.

Reviewed skill reference data supports:

- duration: 20 seconds
- maximum range: 28m
- radius: 5m
- tooltip shape: damage around the corpse plus enemies between caster and corpse

Still unresolved:

- live 5m area anchor: tooltip says corpse-centered, observed community testing has reported caster-centered behavior
- tether/corridor half-width
- whether normalized ESO Logs coordinate units can be equated directly to in-game meters

## ESO Logs spatial metadata discovery

Ability evidence id `118766` exposes actor-position metadata on nearly every reviewed event:

- total events: 8,838
- events with `sourceResources.x/y`: 8,826
- events with `targetResources.x/y`: 8,826

ESO Logs documents these x/y values as actor positions stored at 100x scale. BFF therefore normalizes values such as `5209` to `52.09` for research analysis, without calling those normalized units meters.

## Cast-track topology result

Reviewed corpus:

- matching Siphon cast anchors: 1,380
- linked candidate events: 8,826
- events with source + target positions: 8,826
- events with cast-target candidate position: 8,826
- distinct cast-target candidate actors: 41

Using a 5-normalized-unit endpoint comparison radius:

- within radius of caster: 8,826
- within radius of cast-target candidate: 8,826
- within radius of either endpoint: 8,826
- beyond both endpoint radii: 0

Observed median target distances:

- target -> caster: 1.0963
- target -> cast-target candidate: 0.4687
- target -> caster/cast-target segment: 0.3226
- maximum target -> segment: 1.8866

This does **not** resolve the area anchor because the endpoint circles overlap for the reviewed casts.

## Endpoint-separation adequacy result

The same corpus is non-discriminating for a separated-endpoint test:

- casts with endpoint positions: 1,380
- median caster <-> cast-target separation: 0.5019
- P90 separation: 1.4486
- maximum separation: 2.9567
- casts at separation >= 5: 0
- casts at separation >= 10: 0
- casts at separation >= 15: 0
- casts at separation >= 20: 0

### Research conclusion

The reviewed ESO Logs corpus cannot adjudicate caster-centered versus corpse-centered 5-unit area behavior because it contains no casts with sufficiently separated caster and cast-target endpoints. This is a corpus limitation, not evidence for either anchor hypothesis.

Do not infer the live area anchor or tether width from this corpus.

## Next evidence source: controlled in-game testing

Use deliberately separated caster and corpse-candidate positions and record both **hit** and **no-hit** samples.

Useful sample families:

1. **Caster-only zone**: target within 5 units of caster and clearly outside 5 units of corpse candidate.
2. **Corpse-only zone**: target within 5 units of corpse candidate and clearly outside 5 units of caster.
3. **Interior tether line**: target near the middle of a widely separated caster/corpse segment, outside both endpoint circles.
4. **Tether width sweep**: repeat interior-line observations at increasing perpendicular offsets until damage changes from hit to no-hit.
5. **Outside-all control**: target outside both endpoint circles and well beyond any plausible tether width.

The research-only `RotationDetonatingSiphonControlledSpatialEvidenceService` can compare these observations with the two endpoint-circle hypotheses and derive a bounded interval for tether half-width when both hit and interior-segment no-hit samples exist.

No controlled-test result should enter production geometry until the sample identity, coordinate semantics, and repeatability are reviewed.
