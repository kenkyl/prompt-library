---
id: account-forecast-report
title: One-page account forecast report
description: Turn an account handover document plus CRM, forecast, notes and
  deck research into a one-page forecast report for the current quarter, with a
  key-contacts column per opportunity. Use when a regional director and SA
  leader need to present one account's forecast to an area sales director.
kind: prompt
status: draft
surfaces: [skill, cli]
arguments: [account]
argument-hint: "[account name]"
vars:
  - name: CUSTOMER_NAME
    required: true
    from-arg: account
    describe: The customer account to forecast. Spell it as the CRM does.
    example: Northwind Airlines
source: evernote
source-id: 647fb4844685
source-created: 2026-08-20
source-updated: 2026-08-20
---

You are a Redis AE/SA expert assistant. Analyze the attached handover document for the {{CUSTOMER_NAME}} opportunities, and do additional deep research of all available SFDC, forecast, notes, decks, and other info to generate a:

- one page forecast report of {{CUSTOMER_NAME}} forecast for this quarter
- audience: RD and SA leader will be presenting to area sales director
- include key deal details, including but not limited to:
  - close date
  - deal size
  - last meeting
  - next steps
  - risks: tech and commercial
  - brief history
  - key contacts on customer side
  - what we need to close

--
Add a specific column for the key contacts at {{CUSTOMER_NAME}} for the accounts. For each opp list the key {{CUSTOMER_NAME}} employees involved, including at least:

- name
- title
- email
- role in opp
- linkedin profile link (if available)
- are they a current or potential: coach, champion, influencer, other?
