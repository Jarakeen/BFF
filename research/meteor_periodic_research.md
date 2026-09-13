# Meteor periodic research

## Status

Meteor remains **unresolved / not represented by identifiable evidence in the current imported ESO Logs corpus**. No production runtime semantics should be promoted from the audits below.

## Reviewed mechanic shape

Public references support a post-impact periodic damage component with an approximately 1 second cadence over an 11 second window. That reviewed timing shape was used only as a research filter.

## Raw identity audit

The current ESO Logs runtime database contains no raw events whose ability name is exactly:

- Meteor
- Ice Comet
- Shooting Star

No cast-like events were therefore available under those names.

## Anonymous timing-signature audit

A research-only scan for anonymous damage streams resembling an 11 second / 1 second periodic pattern produced several candidates. The strongest clean-cadence candidates included ESO Logs handles 121090, 119169, and 26879.

Matching timing alone was not treated as identity evidence.

## Candidate topology drilldown

The candidate drilldown segmented damage streams into runs using a greater-than-2.25-second gap boundary and inspected nearby cast-like events.

Across the reviewed output, 146 runs had a same-track prior cast. Every observed same-track prior cast used ESO Logs ability id **26869**. Typical offsets from that cast to the reviewed periodic runs were roughly 2.1 to 2.25 seconds, with some longer offsets in interrupted or merged streams.

External ESO ability-id references associate **26869 with Blazing Spear**, not Meteor. This makes the anonymous Meteor-like timing candidates substantially more consistent with Blazing Spear-family periodic damage than with a hidden Meteor identity.

This external identification is research evidence only and is not promoted as a canonical runtime mapping by this note.

## Conclusion

The current corpus does not provide trustworthy Meteor-family cast or damage identity evidence.

The timing-shape candidates are contaminated by, and strongly linked to, another skill family. Continuing to infer Meteor from anonymous approximately-1-second streams would create false confidence.

Therefore:

- do not map 121090, 119169, or 26879 to Meteor from this corpus
- do not promote Meteor periodic event ids from this audit
- preserve the reviewed 11 second / 1 second mechanic shape as non-executable reference evidence only
- revisit Meteor when a log corpus containing an explicit Meteor / Ice Comet / Shooting Star cast is available

## Evidence guardrails

- same-track linkage is observational evidence, not automatic identity proof
- numeric ids are ESO Logs evidence handles unless independently resolved through canonical data
- anonymous cadence similarity is never sufficient to establish skill identity
- lack of a matching event in this corpus does not mean Meteor lacks the mechanic in game
