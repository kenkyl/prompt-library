---
id: sa-forecast-brief
title: SA technical and deal forecast brief
description: Produce a daily technical and deal forecast brief for a solutions
  architect team from CRM data, call transcripts and recent activity, rendered as
  a self-contained HTML file. Use for a scheduled morning forecast brief, forecast
  inspection, or deal-review prep across a territory.
kind: prompt
status: ready
surfaces: [skill, instructions, cli]
scheduled: true
argument-hint: "[territory or territory list]"
vars:
  - name: TERRITORIES
    required: true
    private: true
    describe: Default territory or comma-separated list to scope the brief to.
      Must match the territory values in the CRM exactly. Baked in at build
      time, NOT taken from an argument -- a scheduled task passes none, so a
      runtime placeholder would arrive empty. An explicit territory in the
      invocation overrides it; see the first line of the body.
    example: Northern Europe
  - name: SA_TEAM
    required: true
    private: true
    describe: Comma-separated architect names whose book this brief covers.
    example: A. Architect, B. Engineer, C. Consultant
  - name: CRM_TOOL
    required: true
    private: true
    describe: The CRM read tool to load, named as the assistant will see it.
    example: the CRM query connector
  - name: EVIDENCE_SOURCES
    required: true
    multiline: true
    private: true
    describe: Bullet list of the evidence sources to search in step 3, one per
      line, each naming the connector and what to look for in it. Local connector
      configuration, so it lives in the private overlay.
    example-file: env/fragments/sa-forecast-evidence-sources.example.md
  - name: MIN_CONSUMPTION_DELTA
    required: true
    private: true
    describe: Absolute consumption change below which a row is suppressed from
      the rollup. Include the currency symbol. Private because a committed
      default would put a currency figure in a public repo.
    example: <minimum amount>
reference: sa-forecast-job-spec
source:
  system: local
  origin: tola-forecast-job-spec.md section 8
  imported: 2026-09-21
---

Produce my daily {{TERRITORIES}} SA technical forecast brief. Read-only. Terse — I read
this in under three minutes. No preamble.

If I named a different territory or territory list when invoking you, scope to that
instead and say which scope you used in the header.

TOOLS — load these first: {{CRM_TOOL}} for all CRM reads; the enterprise search
connector for call transcripts and internal content; mail, calendar, drive, chat
and issue-tracker connectors for activity. CRM access is read-only.

STEP 1 — PIPELINE
Run the primary query (spec §3). It covers the current fiscal quarter plus
the
next three via relative date literals — do not hardcode fiscal years.
Group by ForecastCategoryName in the order Commit, Best Case, Pipeline, Omitted.
Within each, separate by quarter using absolute labels derived at run time
and sort by close date ascending. Show StageName on every row but never group
by it.
Run the coverage counter-query (spec §3) and state the result even if zero.
Run the On-Demand rollup separately. Collapse to one line per account, declines
first, suppressing anything under {{MIN_CONSUMPTION_DELTA}} absolute.

STEP 2 — SIGNALS
Compute signals for the CURRENT QUARTER AND THE NEXT ONE ONLY. Deals in the
third and fourth quarters of the window belong in the pipeline reference table
so the HTML quarter toggle has data, but generate no signals.
Compute every signal in spec §5 and the stage-gated completeness score in §4.
These are field comparisons — do not interpret. Report Tier 1 first, then Tier 2,
then Tier 3. Renewal stage/forecast conflicts go in their own lower-priority
subsection, not mixed with new business.
For each: deal, account, New ARR, close date, SA, AE, and the exact field values
that triggered it.

STEP 3 — EVIDENCE, LAST 7 DAYS
For every Tier 1 signal and every current-quarter deal in Commit, search for
recent activity:
{{EVIDENCE_SOURCES}}

Cite source and date for every assertion. Enterprise search is relevance-ranked,
not exhaustive — it will not reliably return every call on an account. Where
nothing came back, write "no evidence retrieved", never "no activity".

STEP 4 — UPCOMING
Customer meetings in the next 5 business days on these opportunities. What needs
SA prep, and who is covering it.

STEP 5 — PROPOSED UPDATES
The connector is read-only. Attempt no writes and never report a write as done.
Output a queue:
deal | field API name | current value | proposed value | evidence + source | confidence
SA-owned technical and coverage fields only (spec §6 list). Never propose Stage,
Amount, CloseDate or ForecastCategory.
Mark confidence low where the only support is call sentiment rather than a
concrete event, commitment or date.

STEP 6 — TEAM VIEW
One short block per SA ({{SA_TEAM}}): open deal count, Commit New ARR,
count of Tier 1 signals, worst stale-next-step figure.

FORMAT
Output a single self-contained HTML file per spec §7 — inline CSS and JS, no
external requests, no browser storage. Follow spec §7 for links, palette, badges,
star and flag markers, and the four interaction behaviours.
Order: header counts → Tier 1 signals → Upcoming → Tier 2 → Tier 3 → Proposed
updates → Team view → Full pipeline by forecast category → On-Demand rollup.
Signals first. The pipeline table is reference, not the headline.
Save the file and present it. Do not also paste the full brief into chat — give
me a three-line summary and the file.
