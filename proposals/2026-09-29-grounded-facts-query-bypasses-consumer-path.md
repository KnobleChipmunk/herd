# Proposal: grounded facts queried through a table that is not the consumer's own code path

Status: accepted

## Class

grounded-facts-query-bypasses-consumer-path — grounded facts queried through a
table that is not the consumer's own code path

Events (friction ledger):
- 2026-09-29 project-mera #333 (windows): Plan reviewer: the lead's grounded-facts preparation queried the Friendlies Debuffs table whose two recipients were never shown to be tanks; round 2 had to re-verify through the consumer's own fetch_tank_debuff_events path.
- 2026-09-29 project-mera #333 (windows): Lead: the first verifier queried the Friendlies Debuffs table and inferred non-stacking from two clean kills; querying through the consumer's own fetch function plus a sweep for the failure mode (a missed swap) overturned the model — plan review caught it.

## Proposed change

Both events are the same move: a live-data fact was established by querying a
raw WCL table (Friendlies Debuffs) instead of the consumer's own code path
(`fetch_tank_debuff_events`), and the clean samples hid the mechanic that
distinguished the models. A broader query standing in for the consumer's own
actor selection and filters is not the same check.

Add a verifier-script rule to the sweep's live-data step (the read-only
verifier in a Herdr pane that loads `.env` itself): identify the consumer,
reproduce its actor selection and filters, and save results per selected
actor — never a broader table query. Label counts as per-actor or combined.
For any catalog grounded in live data, sample the failure mode (a missed
swap, a no-aura fight) as well as clean examples; a clean example cannot show
what an error looks like.

## Prediction

No `grounded-facts-query-bypasses-consumer-path` events in the next run's
friction lines; the sweep's live-data verifier outputs per-actor counts from
the consumer's own fetch function, and the plan reviewer's evidence table
cites the consumer's code path, not a raw table query.
