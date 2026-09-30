# Stale HERDR pane/tab IDs on resumed sessions

Status: applied https://github.com/KnobleChipmunk/herd/pull/76 2026-09-30

## Class: stale-herdr-pane-ids (inherited HERDR pane/tab IDs are stale on resume)

- 2026-09-27 herd #55 (windows): The resumed session inherited stale HERDR_PANE_ID w1:p2Z and HERDR_TAB_ID w1:tP while the live pane was w1:p30 in w1:t11, so the first split using --current failed; socket discovery plus explicit pane targeting fixed dispatch.
- 2026-09-27 herd #55 (windows): Lead: a first split with --current failed even though read-only layout discovery found the live pane w1:p30 in w1:t11, because the inherited pane/tab IDs were stale; explicit IDs were required.

## Proposed change

Add a resume rule to the lead section of `skill/SKILL.md`: after resuming a session, do not trust inherited `HERDR_PANE_ID` / `HERDR_TAB_ID` — verify the live caller pane and tab via read-only socket/layout discovery, and pass explicit pane and tab IDs to every split and dispatch. Cost in #55 was a failed first split plus a discovery round-trip.

## Prediction

The next run's friction lines show no `stale-herdr-pane-ids` events, and a resumed run's first split succeeds on the first attempt without a discovery retry.
