---
id: sales-account-transition-report-prompt
title: Sales Account Transition Report Prompt
description: Research every open opportunity on a list of accounts moving to
  the team with a seller who is transferring in, and produce a Google Doc with a
  one-page summary, a per-opportunity section and a composite priority score.
  Use when accounts change hands and the team needs to triage and prioritise
  the inherited pipeline.
kind: prompt
status: draft
surfaces: [skill]
vars: []
source: evernote
source-id: be4ccaf15d69
source-created: 2026-08-12
source-updated: 2026-08-12
---

<prompt> A seller is moving to our sales/SA team, and is bringing over a handful of active accounts with opportunities. Given the attached list of accounts, generate a report for each of the opporuntities that includes but is not limited to:

- what does the company do? who are their customers, how would they use redis?
- account history with Redis
- what is the identified use case? (if there is no specific use case, note that)
- how many meetings we've had, what the deal stage is
- size and scope of each deal
- what the current and suggested next steps are
- what are the risks
- have we completed?: NBM, TDD, POC; if so, status of each
- key customer personas involved
- chance of success based on similar deals
- any outstanding technical requests or tech risks
- recommended internal documentation links to useful resources for the account

Do deep research based on all available notes, decks, call transcripts, internal documentation, and any other relevant sources. where applicable, augment with external/public information about the company their performance, their tech stack, Redis/other database usage, etc.
Output a google doc report that includes a concise, table or otherwise easy-to-read one-page summary of all of the opps in one view; then have sections following the same template with all details requested above and any additional details. Provide a composite score ranking of each of the opps based on % chance to close, $ scoped, account upside, fit for Redis, etc. to help us prioritize (include a breakdown of how you generate this composite score in an appendix).
use all of the above to design an optimized prompt for yourself first. then, execute your optimized prompt to generate the report. ask clarifying questions if needed.
</prompt>
