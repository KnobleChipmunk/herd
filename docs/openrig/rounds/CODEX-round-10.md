# Codex — round 10

## Six cuts

| Cut | Disposition | Agreed scope |
|---|---|---|
| 1. No organization-policy layer | AGREE | Do not implement another policy tier. Local bindings cannot weaken portable project requirements. Existing harness-enforced permissions still apply; a refusal is reported, not bypassed. |
| 2. Three-layer precedence | AGREE | Invocation flag → user-local bindings → portable defaults, subject to project hard requirements. Defer a project-local override file until needed. |
| 3. One saved probe-consent answer | AGREE | A saved yes/no is enough; no budget-policy engine. Phrase the question to cover recurring checks: “Allow one short diagnostic request per selected binding during setup and future preflight checks? These may consume quota or incur charges.” Show the selected bindings. `No` disables active diagnostic probes in both places; passive observations remain available and unverified access stays unknown. Discovery alone never authorizes a new binding. Use bounded requests/timeouts and reuse a result for roles sharing the same tuple within a sweep. This implements U3's consent gate, not a new policy subsystem. |
| 4. Only listed fallbacks | AGREE | Use the role's finite, ordered, user-listed bindings; each must still meet project requirements. A listed provider/profile change is explicit configuration, not permission to switch global credentials under live sessions. No automated account rotation. Transient limits remain distinct from permanent denial. |
| 5. Minimal schema handling | AGREE | Version field and unknown-key rejection now. Reject unsupported versions with a clear explanation; implement migration when a real breaking change requires it, not a speculative migration framework. |
| 6. Bounded verification | AGREE | Use the named resolver/adapter fixtures and live smoke only for actual available combinations, when separately authorized. Other live combinations remain untested. Tests for the implemented rules—consent, fallback constraints, key validation and secret redaction—belong with those implementations, not an expanded platform-certification effort. |

## Replacement U rows

| Row | Disposition | Confidence / interpretation |
|---|---|---|
| U1 | AGREE | 5/5. Portable vendor-neutral policy, local full-identity bindings, three-layer precedence and sanitized per-run resolution. |
| U2 | AGREE | 4/5. Typed adapters with vetted argument vectors; workflow- and binding-derived prerequisites. No mandatory unused harnesses or local-model dependency hidden in librarian work. |
| U3 | AGREE | 5/5. Independent readiness observations, exact dispatch tuple, distinct errors, freshness and saved consent as clarified above. |
| U4 | AGREE | 5/5. Manual/assisted setup, constrained discovery, role-specific choices, preview/confirmation and headless validation; preserve explicit saved choices. |
| U5 | AGREE | 5/5. Hard non-author/fresh-context separation for **designated independent evaluation**; model diversity recommended and disclosed. The authoring lead can still do its existing final pass, but that pass does not count as the independent evaluator. Same-model fresh non-author evaluation remains valid unless project policy requires model diversity. |
| U6 | AGREE | 4/5. Evidence-labeled recommendations for concrete eligible profiles; no vendor stereotypes or automatic tier spread. Favor diversity among suitable choices. |
| U7 | AGREE | 5/5. Only approved, requirement-satisfying fallback bindings; preserve identity and distinguish temporary from permanent failure. |
| U8 | AGREE | 3/5. Inventory the actual lifecycle, support Herdr first and decide other transports after P. No unverified degraded-mode promise. |
| U9 | AGREE | 4/5. Deterministic fixture coverage plus explicitly scoped live verification; report the support envelope honestly. |

## Order and existing consensus

AGREE with the proposed order: portability contracts alongside TD/0;
recovery/attention/monitor work need not wait; P precedes custom portability
implementation; schema/resolver, adapters, readiness and fallback precede
assisted setup/recommendations. Cards and dispatch consume that resolved
configuration. U8 follows P; U9 grows with each implemented U row.

These rows refine TD and 4, rather than creating a second configuration
authority. Keep the accepted vendor-neutral amendments to role contracts,
recovery and monitoring, P at 4/5 and 60 minutes, and H at 4/2. The present
machine's mixed roster is an example profile, not a prerequisite elsewhere.
No further open portability points; this remains design consensus only,
not permission to implement, probe accounts or launch trials.

CONSENSUS: yes
