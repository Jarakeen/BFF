# Migration

Explicit one-purpose transition code for old schemas, persisted data, identity repair, and compatibility conversion.

Normal application runtime must not depend on this directory as a mechanics, UI, persistence, or domain authority. Migration/bootstrap tools may invoke it deliberately.

See `docs/CODE_RETIREMENT_AND_QUARANTINE.md`.
