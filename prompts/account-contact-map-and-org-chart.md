---
id: account-contact-map-and-org-chart
title: Account contact summary and org chart
description: Summarise the customer contacts involved in an evaluation over the
  past one to two years and build an org chart that marks who is needed to close,
  who we have not met, and any detractors. Use as a follow-up in an account or
  deal conversation when you need a stakeholder map for a specific opportunity
  and its predecessors.
kind: prompt
status: draft
surfaces: [skill, cli]
arguments: [account]
argument-hint: "[account name]"
vars:
  - name: CUSTOMER_NAME
    required: true
    from-arg: account
    describe: The customer account whose contacts to map. Spell it as the CRM
      does.
    example: Northwind Airlines
source: evernote
source-id: e3e521746114
source-created: 2026-08-20
source-updated: 2026-08-20
---

taking a step back, provide a summary report of the key contacts at {{CUSTOMER_NAME}} that have been involved in the evaluation in the past 1-2 years, focusing on this specific opportunity and its predecessor(s) for the same use case and teams. in your list of contacts, include but don't limit your details to:
- name
- title
- role
- which team or group are they in
- email
- linkedin profile link
- relationship to Redis evaluation/poc
- are they a current or potential?: champion, coach, influencer, etc. (and if so, why)
- few bullet point of relevant notes: e.g. things to remember, risk factors or detractors,

additionally, based on deep internal and external research, construct a detailed org chart that's included in the report in addition to the per-employee information table. for the org chart:
- highlight key individuals needed to get the deal done, who we still need to meet, any potential detractors, etc.
- a short snapshot of key details from the full individuals report (i.e. the info that makes sense to include based on space for a small box in an org chart that should fit on the 2nd page of a 2 page report)

ask clarifying questions if needed.
