---
id: field-guide-update
title: Update a product field guide
description: Review and rewrite an existing product field guide for SAs and
  AEs -- research for accuracy, propose a revised outline with the reason for
  each change, then regenerate the guide once the outline is approved. Use when
  the user attaches or links a field guide, enablement doc or positioning guide
  for a product and asks to update, refresh or improve it.
kind: prompt
status: draft
surfaces: [skill, cli]
arguments: [product]
argument-hint: "[product name]"
vars:
  - name: PRODUCT
    required: true
    from-arg: product
    describe: The product the field guide covers, as it is named publicly.
    example: Redis Query Engine
source: evernote
source-id: cd6603fe0236
source-created: 2026-09-01
source-updated: 2026-09-01
---

<background>
Take this {{PRODUCT}} field guide previously created by Claude. The objective of the field guide is to be an easily sharable guide for {{PRODUCT}} that SAs and AEs can use to assist in discovery, scoping, positioning, etc. It should include enough technical depth for an SA, as that is the primary audience. Your goal is to update this document for accuracy, clarity, content, flow, etc. Do deep research internally and externally on the topics and tools discussed to ensure you are including the most accurate, up-to-date, and impactful information. You can add, remove, or update the layout/flow or any of the content. Use more diagrams and visuals where useful and applicable. Apply any specific changes the user asks for, for example removing sections that only matter when running a demo, or expanding the section on where {{PRODUCT}} fits among cloud platforms, AI development frameworks, and CSPs. Ask clarifying questions if needed.
</background>
<tasks>

1. review the guide, do additional research, and plan an updated outline of the sections and content in each
2. share the outline with me for review; make sure to note any changes and why you're proposing them
3. after my edits and/or confirmation, you will generate the updated report

</tasks>
