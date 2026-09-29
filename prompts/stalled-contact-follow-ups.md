---
id: stalled-contact-follow-ups
title: Follow-up sweep on stalled contacts
description: Sweep sent mail, meetings and CRM records for external contacts who
  have gone quiet, and save a tailored follow-up draft in Gmail for each one that
  is genuinely stalled -- never sending. Use when the user wants to find
  prospects or customers who stopped replying, clear a follow-up backlog, or
  asks which contacts they owe a nudge.
kind: prompt
status: draft
surfaces: [skill, cli]
vars:
  - name: LOOKBACK
    default: "the past six months"
    describe: How far back to pull sent mail and meetings. Keep it relative
      ("the past six months") so the prompt never goes stale.
  - name: QUIET_DAYS
    default: "5"
    describe: Days without a touch before a contact counts as stalled. Anything
      touched more recently is still mid-cadence and is left alone.
source: evernote
source-id: 5fd65e492689
source-created: 2026-09-23
source-updated: 2026-09-23
---

## Task

Dig into Gmail, your calendar, and Salesforce (via Glean, app: salescloud) to find contacts who've gone quiet, and draft follow-up emails for the ones that are genuinely stalled.

## Steps

1. Pull sent emails and calendar meetings with external contacts from {{LOOKBACK}}. For meetings, treat the meeting date itself as a touch, note who attended and whether there was a follow-up email after it.
2. For each thread or meeting where you reached out or met and never got a reply or next step since, identify the contact and account.
3. Cross-reference each contact in Salesforce: are they tied to an open opportunity, and what's the last activity date on the account or contact record.
4. Compute days since your last touch, whether that's an email or a meeting, on each contact. Drop anything touched in the last {{QUIET_DAYS}} days, that's still mid an active cadence and another note would pile on. Also drop anything that bounced, was explicitly declined, or already got a reply or a next meeting on the books since your last touch.
5. For everything left (last touch more than {{QUIET_DAYS}} days ago, no reply or next step since, not bounced or declined), check your Gmail drafts for that thread first. If an unsent draft is already sitting there, skip it, don't stack a second one on the same contact.
6. For each remaining contact, draft a short follow-up in your own voice that doesn't repeat the last note. Vary the angle (a different question, a lower-friction ask, referencing what you covered in the meeting, or just closing the loop) rather than a generic "checking in." Reply within the existing email thread where one exists; otherwise start a new one referencing the meeting.
7. Never fabricate a price, quote, deal detail, or anything about what was discussed in a meeting. If something isn't in Salesforce, the email thread, or the meeting record, flag it instead of guessing.
8. Save the drafts in Gmail rather than sending them, and list who got a fresh draft, with a one-line reason each, so it's easy to review and send.
