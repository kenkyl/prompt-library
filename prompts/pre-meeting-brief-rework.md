---
id: pre-meeting-brief-rework
title: Rework a pre-meeting brief with full account context
description: Rebuild an earlier AI-generated pre-meeting brief and its
  customer-facing deck using deep internal research on the account and
  opportunity. Use when a brief for an upcoming customer call was produced
  without the full account history and needs to be checked, corrected and
  regenerated, with a meeting run book and the questions to ask.
kind: prompt
status: draft
surfaces: [skill, cli]
arguments: [account]
argument-hint: "[account name]"
vars:
  - name: CUSTOMER_NAME
    required: true
    from-arg: account
    describe: The customer or prospect the meeting is with. Spell it as the CRM
      does.
    example: Northwind Airlines
source: evernote
source-id: f90f3b21a7a8
source-created: 2026-08-18
source-updated: 2026-08-18
---

<instructions>
I used Claude to generate a pre-meeting brief for an upcoming call with {{CUSTOMER_NAME}}. Short descriptions of the attached context files are included in the original_prompt section below. Ask clarifying questions if needed.

Your goal is to analyze and recreate the brief, with the new context, instructions, and goals:

- the original report was built without the full context of the account, Redis's relationship with {{CUSTOMER_NAME}}, etc.: in order to improve the report, do deep research on all internal info available to you about Redis's work with {{CUSTOMER_NAME}} and this specific project and opportunity, including but not limited to: account and opportunity research, notes, call transcripts, documentation, slide decks, email and slack conversations, etc.
- you should review the entire report for accuracy, clarity, correctness, etc.
- the original prompt used to generate the attached brief is included below for context, but does not need to be followed exactly; instead use the original prompt, the new context, and your understanding of the situation to recreate and execute an optimized prompt to complete the task at hand
- final outputs: generate new, upgraded versions of (1) the internal-facing report document, and (2) the customer-facing slide deck
- ask clarifying questions if needed

</instructions>

<original_prompt>
[Replace this block with the prompt that produced the original brief, if you have it. The version below is the one this template was written from.]

Below are additional notes and emails from the SA and others regarding the {{CUSTOMER_NAME}} project and account summarizing current understanding, among other things. {{CUSTOMER_NAME}} is the prospective customer for whom we have been crafting a sizing script. Here are the next context details: - summary notes from the SA (pasted, auto-attached as text file) - the sizing script; the final version of the script sent to {{CUSTOMER_NAME}} (attached) - the {{CUSTOMER_NAME}} team's outputs after running the script (attached) - the Redis and {{CUSTOMER_NAME}} email thread discussing the topic (attached as PDF) - the Redis team's planned proposal deck (attached as PDF) - the meeting agenda for today's call (pasted below)
Analyze, research, and deep dive on all of the above, and provide me the following: - 5-10 bullet point summary of the opportunity highlights and details - highlight the technical and commercial risks of the project (note: specifically answer if "this is a good fit for Redis and the proposed Redis products") - list of specific questions we should or must ask the {{CUSTOMER_NAME}} team to confirm we are on the right track - based on the agenda and broader context, provide a recommended run book for the meeting for the Redis team - based on the context of the project and request and other prompt details, include any other information or sections you deem useful or pertinent - if needed, provide recommendations for improving the presentation deck: e.g. slides to add, change, remove, etc.
Create a high quality, clean, concise, and clear 2-page report output to be shared and used by the Redis team before the meeting for prep and execution.
<today_meeting_agenda> [paste today's agenda] </today_meeting_agenda>
</original_prompt>
