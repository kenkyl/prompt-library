---
id: sa-forecast-job-spec
title: SA forecast job spec
description: Reference document for the SA technical and deal forecast brief --
  CRM field mapping, primary query, stage-gated completeness scoring, signal
  tiers, write constraints, and HTML output conventions. Loaded as project
  knowledge alongside the prompt, not invoked on its own.
kind: reference
status: ready
surfaces: [knowledge]
vars:
  - name: TERRITORIES
    required: true
    describe: Territory or comma-separated territories this book covers.
    example: Northern Europe
  - name: SA_TEAM_LEAD
    required: true
    private: true
    describe: Name of the team lead who owns this job.
    example: A. Architect
  - name: SA_TEAM
    required: true
    private: true
    describe: Comma-separated architect names whose book this covers.
    example: A. Architect, B. Engineer, C. Consultant
  - name: FISCAL_CALENDAR
    required: true
    private: true
    describe: One-line fiscal-year definition, e.g. "FY2030 = 2029-02-01 to
      2030-01-31". Drives relative date literals; never hardcode a year in a query.
    example: FY2030 = 2029-02-01 to 2030-01-31
  - name: SCOPE_FILTERS
    required: true
    multiline: true
    private: true
    describe: The CRM clauses that scope the book to this team and territory.
      Internal schema.
    example-file: env/fragments/sa-forecast-scope-filters.example.md
  - name: QUERY_AND_SIGNAL_RULES
    required: true
    multiline: true
    private: true
    describe: Sections 2 through 6 -- field map, primary query, completeness
      score, signal tiers, write constraint. The largest and most
      organisation-specific fragment.
    example-file: env/fragments/sa-forecast-query-and-rules.example.md
  - name: LINK_TEMPLATE
    required: true
    multiline: true
    private: true
    describe: Link-construction patterns for record references. Contains the CRM
      org host, which identifies the instance.
    example-file: env/fragments/sa-forecast-link-template.example.md
  - name: OPEN_ITEMS
    multiline: true
    private: true
    describe: Optional. Unresolved questions about CRM schema, permissions and
      integrations. Leave unset and section 11 renders empty.
    example-file: env/fragments/sa-forecast-open-items.example.md
source:
  system: local
  origin: tola-forecast-job-spec.md sections 1-7 and 9-11
  imported: 2026-09-21
---

# {{TERRITORIES}} SA Technical & Deal Forecast — Scheduled Job Spec

**Owner:** {{SA_TEAM_LEAD}} — SA Team Lead, {{TERRITORIES}}
**Team:** {{SA_TEAM}}
**Surface:** Claude Project → Scheduled Tasks
**Validated against production.** Every query in the rules section below was executed
against a live org and returned the documented results.

This is the reference document. The prompt that consumes it lives separately, at
`prompts/sa-forecast-brief.md`, so the two cannot drift apart.

---

## 1. Scope

| Dimension | Value |
|---|---|
| Fiscal year | {{FISCAL_CALENDAR}} |
| Current quarter (Q) | Resolved at run time from the fiscal calendar. Never written into the query. |
| Query window | Q through Q+3, via relative date literals — **never hardcode years**. Hardcoding is the single most common way this job silently goes stale. |
| Signal scope | **Q and Q+1 only.** Q+2 and Q+3 appear in the pipeline reference table so the HTML quarter toggle has data, but generate no signals — a Qualification deal closing three quarters out needs no action today. |
| Amount filter | **None.** Territory scoping is sufficient. |

Scoping filters, which name the team and the territory, come from the private overlay:

{{SCOPE_FILTERS}}

**Deal counts move, so never assert one.** During validation the count dropped by
roughly a tenth inside a single working session as deals closed and got reassigned.
Never treat a specific number as a pass/fail check — see §9 for what to validate instead.

**The territory filter may remove nothing, and that is fine.** It is a guard, not a
noise filter. Because an equality test also excludes nulls, run the coverage
counter-query each time so anything dropped is reported rather than silently lost.

---

## 2-6. Field mapping, queries, completeness, signals, write constraints

These sections are the internal core: the CRM field map resolved against a live
record, the primary query and its counter-queries, the stage-gated completeness
score, the three signal tiers, and the write constraint. They are organisation-
specific schema and live in the private overlay.

The method that matters, and that survives a change of CRM:

- **Resolve every field against a live record before trusting a label.** API names
  and labels diverge; several in this map are actively misleading.
- **Prefer pre-computed fields to arithmetic.** Where the org already maintains a
  day-count or completion field, read it rather than recomputing from timestamps.
- **Never scope by record owner.** Opportunities carry a seller as owner with a
  separate architect assigned, so owner-scoping silently drops the book.
- **Signals are field comparisons, not judgements.** Report the values that
  triggered them and let the reader interpret.
- **Tier signals by the action they demand** — act today, forecast governance,
  hygiene — not by severity.

{{QUERY_AND_SIGNAL_RULES}}

---

## 7. Output format — interactive HTML

The brief renders as a single self-contained HTML file. Content, ordering and signal logic are unchanged from §5 and §6 — this section governs presentation only.

### Link construction

{{LINK_TEMPLATE}}

### Visual system

Do not reach for a generic dashboard kit. This is a forecast-inspection document read once each morning by one person who already knows the accounts — dense, scannable, print-legible, no hero panel and no decorative gradients.

**Palette** — five values, each carrying meaning rather than decoration:

| Token | Hex | Use |
|---|---|---|
| `--ink` | `#14181F` | Body text, table rules |
| `--paper` | `#FBFAF7` | Page background |
| `--commit` | `#1B4D3E` | Commit forecast category |
| `--bestcase` | `#8A6A1F` | Best Case forecast category |
| `--alert` | `#A32B1C` | Tier 1 signals, negative New ARR, overdue dates |
| `--muted` | `#6E7681` | Pipeline, Omitted, secondary metadata |

Pipeline and Omitted stay in `--muted` deliberately — 28 of 53 deals sit there and colouring them competes with the signals.

**Typography** — one family. A humanist sans at 15px/1.5 for body, tabular figures for all currency and day counts so columns align. Deal names at normal weight; the only bold in a table row is the thing that triggered a signal.

**Badges and markers**

- Forecast category renders as a filled pill in its palette colour, always in the row.
- Stage renders as an outlined pill in `--muted` — present on every row, never a grouping key.
- Account gets a consistent colour-coded chip so the eleven American Airlines deals and six HPE deals read as clusters at a glance. Derive the colour from a hash of the account name, capped at a muted range so it never competes with `--alert`.
- `★` marks a deal you should open first: any Tier 1 hit in the current quarter.
- `⚑` marks a risk-flagged deal: the at-risk flag set, or a failed technical risk review, negative new ARR, or a past close date. Each flag carries a `title` attribute naming the exact field and value.
- Never use colour alone to carry meaning — every colour pairs with a glyph or a label.

**Interaction** — four behaviours, no more:

1. Signal tiers and pipeline sections collapse and expand. Tier 1 and Upcoming open by default; everything else starts collapsed.
2. Every table sorts by clicking a column header.
3. **Filter bar** — three independent controls, applied together, scoping every section of the page including the signal tiers and the team view. Each shows a live count of matching deals so an empty result is obviously a filter and not a broken query.

   - **Forecast category** — multi-select toggle buttons: Commit, Best Case, Pipeline, Omitted, plus All. Each button carries its palette colour. Default: all selected.
   - **Quarter** — multi-select toggle buttons using **absolute labels only**: `Q3 FY27`, `Q4 FY27`, `Q1 FY28`, `Q2 FY28`. Never render "Q", "Q+1" or "current quarter" in the interface. Derive each label from the `FiscalYear` and `FiscalQuarter` of the rows returned, so it stays correct as quarters roll over. Default: current quarter only, selected. Provide a one-click **"Q3 FY27 + Q4 FY27"** preset as the secondary default, and a **"Next 4 quarters"** preset for all four.
   - **SA** — one entry per configured architect, plus All. Default: All.

   Quarters with no matching deals still render as buttons, disabled, showing zero — a quarter that disappears from the bar is indistinguishable from one you forgot to query.

   Mark the two quarters outside the signal scope (`Q1 FY28`, `Q2 FY28` today) with a small "reference only" note in the bar, because selecting them will populate the pipeline table while the signal sections stay empty. Without that note the page looks broken.
4. Each proposed update in the §6 queue has a copy button that yields `field API name → proposed value` for pasting into Salesforce, since the connector can't write.

Motion only in response to a click. No entrance animations.

**Constraints** — inline all CSS and JS, no external fonts or CDN requests, no browser storage. Must survive being emailed as an attachment and opened offline. Responsive to a phone width, visible keyboard focus, `prefers-reduced-motion` respected, and a print stylesheet that expands all sections and drops the interactive chrome.

### Header

Open with the counts, because the first thing to verify is that the query ran correctly: deals in the current quarter, deals across all four, count in Commit/Best Case, Commit New ARR, count of Tier 1 signals, and the run timestamp. Label every quarter absolutely (`Q3 FY27`), never relatively.

**Validate by internal consistency, not against a remembered total.** The count changes daily as deals close and get reassigned — it moved by roughly a tenth inside one working session. Check instead that: forecast-category counts sum to the total; every row carries a non-null architect name from the configured list and the expected territory value; the coverage counter-query result is stated even when zero; and On-Demand records appear only in the rollup. If any of those fail, say so in the header rather than burying it.

---

## 8. Job prompt

Moved out of this document. It is now the canonical prompt at
`prompts/sa-forecast-brief.md`, and is compiled from there into both the scheduled
skill and this project-knowledge file. It previously lived in both places at once
and drifted; that is what this repository exists to prevent.

Its cross-references to §3 through §7 above remain valid, which is why the section
numbering here is preserved rather than closed up.

---

## 9. Setup

This document and the prompt are two artifacts built from one repository. Neither is
hand-edited: both are generated, and editing a built copy is how the two previously
drifted apart.

**First-time setup**

1. `./bin/prompt build sa-forecast-brief` — produces the knowledge file (this
   document, at `build/knowledge/sa-forecast-job-spec.md`) and the skill
   (`build/skills/sa-forecast-brief/SKILL.md`).
2. Upload the built knowledge file to the project knowledge base, named
   `sa-forecast-job-spec`. The prompt's opening line names that file exactly. If it
   is missing the job does not error — it silently re-derives every query from
   scratch, which is the failure mode to watch for.
3. `./bin/prompt install sa-forecast-brief` — installs the skill locally.
4. Point the scheduled task at the `sa-forecast-brief` skill.
5. Run it manually once. Validate by internal consistency per §7 — never against a
   remembered deal count, which moves daily.
6. Open the field-update request described in the rules section in parallel.

**Scheduling**

Weekdays, 45 minutes before you start. If forecast guidance runs on a weekly cadence,
consider a fuller Monday variant that adds week-over-week movement.

**After any edit to the prompt or this spec**

Edit the canonical file in the repository, never a built copy, then:

1. `./bin/prompt build sa-forecast-brief`
2. `./bin/prompt install sa-forecast-brief` — refuses if a built copy was
   hand-edited, rather than silently discarding the edit. Use `--adopt` to pull that
   edit back into the canonical file.
3. Re-upload the knowledge file **only if this document changed**. The skill and the
   knowledge file are versioned together in git but uploaded separately, so a spec
   change that is not re-uploaded is the one way the two can still fall out of step.

---

## 10. First two weeks

- **Audit the proposed-update queue by hand** before trusting it. Twenty manual applications tells you the false-positive rate; nothing else does.
- **Watch for signals that fire on everything.** Two fields were both caught this way during validation. Any signal hitting more than about a third of the book is measuring a broken field, not a broken deal.
- **Cut unread categories.** If a tier-3 signal goes untouched for two weeks, delete it.
- **Then parameterise on SA name** so each architect runs their own. That is where this
  stops being one person's gain and becomes the team's.

---

## 11. Open items

{{OPEN_ITEMS}}
