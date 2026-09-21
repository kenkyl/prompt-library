<!-- EXAMPLE shape for QUERY_AND_SIGNAL_RULES -- sections 2 through 6 of the
     reference doc. This is the largest and most organisation-specific fragment:
     your CRM field map, the primary query, the completeness score, the signal
     tiers, and the write constraint. Keep the real one in
     private/fragments/sa-forecast-query-and-rules.md

     Only the SHAPE is shown. Substitute your own field names and thresholds. -->

## 2. Field mapping — resolved against a live record

Placeholders below are written `<like-this>` rather than as real API names, so the
sanitization gate stays armed on this path -- if real field names are ever pasted
here by accident the commit is blocked rather than suppressed by an allow rule.

Most CRMs suffix custom fields and custom relationships distinctly (in one common
platform, a doubled underscore plus `c` for a field and `r` for a relationship).
Write them out in full in your private fragment; the convention is what matters here,
not the spelling.

| Label | API name | Notes |
|---|---|---|
| Architect | `<architect lookup>` | Lookup to a user; query through the relationship, not the id |
| Technical next steps | `<next steps field>` | Paired with a last-updated timestamp |
| Days since next step | `<pre-computed day count>` | Pre-computed — read it, do not recompute from timestamps |
| Next step | `<next step field>` | A custom field may carry the real content while the standard one is near-useless. Verify against a live record. |

Record which fields you checked and found *unusable*, not just the ones you use.
That list is what stops the next person re-litigating the same dead ends.

## 3. Primary query

The query, its coverage counter-query, and any separate rollups. Use relative
date literals for the quarter window; never hardcode a fiscal year.

Run the counter-query every time and state its result even when zero, so records
excluded by an equality test on a nullable field are reported rather than lost.

## 4. Technical completeness — computed, stage-gated

A score over the technical fields that should be populated *by the current stage*,
so an early-stage deal is not penalised for fields it cannot have yet.

## 5. Signals

Three tiers, ordered by the action they demand rather than by severity:

- **Tier 1 — act today.** A concrete, dated problem on a near-term deal.
- **Tier 2 — forecast governance.** Stage, category and technical state disagree.
- **Tier 3 — hygiene and coverage.** Staleness and missing-field patterns.

Every signal is a field comparison. Report the values that triggered it; do not
interpret them.

## 6. Write constraint

Which fields the assistant may propose changes to, and which are never its
business — typically stage, amount, close date and forecast category. If the
connector is read-only, say so and emit a proposal queue instead.
