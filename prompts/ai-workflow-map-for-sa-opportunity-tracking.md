---
id: ai-workflow-map-for-sa-opportunity-tracking
title: AI Workflow Map for SA Opportunity Tracking
description: Design answers for an SA opportunity-tracking dashboard -- roster
  and scope, default views and toggles, the fields to show, technical
  "needs attention" flags, and delivery. Use as the build brief when creating or
  revising a forecast dashboard for an SA team's territory.
kind: prompt
status: draft
surfaces: [skill]
vars:
  - name: TERRITORIES
    required: true
    private: true
    describe: The territory or subregion the dashboard tracks, as the CRM names
      it.
    example: Northern Europe
  - name: SA_TEAM
    required: true
    private: true
    describe: Comma-separated architect names on the roster.
    example: A. Architect, B. Engineer, C. Consultant
  - name: SA_TEAM_LEAD
    required: true
    private: true
    describe: The SA team lead -- the person this dashboard is built for.
    example: A. Architect
  - name: SA_MANAGER
    required: true
    private: true
    describe: The SA manager for the territory.
    example: D. Manager
  - name: AE_TEAM
    required: true
    private: true
    describe: Comma-separated account executive names on the roster.
    example: E. Seller, F. Seller, G. Seller
source: evernote
source-id: 2d6001e84823
source-created: 2026-09-22
source-updated: 2026-09-23
---

great! notes for the claude-training-hub are complete for now. after we complete the AI workflow exercise, you should summarize the activity, context, info, and outcomes, and add them to (1) the claude-training-hub, and (2) prompt-library-best-practices-review, where and how it makes sense to do so. for now, back to the AI workflow map:

Roster & scope:
1. Is the team just {{TERRITORIES}} ({{SA_TEAM}}), or does it also pull in neighbouring subregions? If an SA shows up on your opportunities but isn't in this roster, are they in an adjacent territory or a different territory working one of your accounts?

- Territory = Account Team Subregion: {{TERRITORIES}}; current personnel:
  - AEs = {{AE_TEAM}}
  - SA Manager = {{SA_MANAGER}}
  - SAs = {{SA_TEAM}} ({{SA_TEAM_LEAD}} is team lead, has some accounts mapped, still updates SA Manager notes for some opps)
  - include all opps assigned to any AEs or SAs in the roster; like a union of the 2 sets (e.g. you would include an opp assigned to a rostered AE that has an off-roster SA; you would NOT show an opp whose AE and SA are both off the roster)

2. Default view: your opps only, or the whole team's, with a toggle?

- default view and view options:
  - visual/chart views of forecasted opportunities based on toggles/selections, team progress in Q and FY to-date (i.e. deal wins, FY to-date should be default with toggle for Q-by-Q and previous FY),
    - you should derive the types of charts and visual, and how they are presented, from your context and intuition and this project's goals
  - table view of opportunities:
    - full team opps (named SA = anyone in {{SA_TEAM}}, or {{SA_MANAGER}}), with a toggle
    - current quarter (QN, e.g. Q3FY27), with toggle for: QN+1, QN+2, QN+3, current FY, previous FY, and each of the previous three quarters
    - forecast category = Best Case and Commit, with multi-select/toggle for Best Case, Commit, Pipeline, Closed Won, Closed Lost
    - fields (default, groupable and sortable unless noted):
      - Account Name
      - Opportunity Name (sortable, but not groupable)
      - Short Description (not groupable/sortable)
      - Opportunity Stage
      - Forecast Category
      - Fiscal Period (i.e. quarter)
      - Close Date
      - New ARR
      - Opportunity Owner
      - Account Owner
      - SA Name
      - Next Step
      - Technical Next Steps
      - SA Manager Notes
      - NBM Status
      - NBM Date
      - Tech Win Status
      - TDD Status
      - TDD Date
      - POC Status
      - POC Details aggregate (plan link, start date, end date; does not need to be groupable/sortable)
      - SFDC opportunity link

"Needs attention" logic — the actual value-add:
3. What should trigger a flag — no Next Step update in N days (what's N), Tech Win still "Undecided" close to close date, POC Status blank/"Unknown," or something only you'd know from how forecast calls actually go?

- I am an SA leader, so actions should lean towards technical forecasting; here are some examples in order of priority, and you should additionally reference the slide deck shared below; think of these as a starting point:
- tech forecast details are not aligned with deal stage (e.g. deal in Commit, but Tech Win is Undecided; TDD held without date; TDD held but not NBM; dates of key meetings do not make sense; TDD not held or scheduled but in advanced deal stage, i.e. we need to confirm that we have a "real" scope; etc. ...)
- POC flags: POC running for more than 2 weeks; POC planning phase for more than 1 week; POC started but no documentation; POC marked as complete but no end date; etc.
- inferred or noted technical risk
-
- tech next steps not updated in past 7 days

4. How should "Omitted" and other edge-case forecast categories be handled — included, excluded, or shown separately?
Augmentation beyond Salesforce
5. Which sources actually add signal for you day to day — Gmail, Slack, Drive, something else? (Same pattern as your own account-intelligence prompt's Evernote handling — first-class source, but labeled as unverified/personal.)
Write-back & delivery
6. Any fields you'd trust the dashboard to write back to (e.g. Next Step) versus fields that stay human-only (forecast category, amount, close date)?
7. Just a Shared Artifact you open on demand, or also a Scheduled Task pushing a digest before your weekly forecast call?
8. Single-player (you) first, or team-ready (each SA on the roster seeing their own slice) from day one — changes how we handle per-user connector auth.

- Behavior and functionality notes and requests:
  - there should be the ability to add/remove/edit the territory and roster names; when the skill is invoked, the user's territory and team should be extracted from available info, and the user should be asked to confirm the: territory/subregion and roster of AEs/SAs for the dashboard to track; note - this can use a different approach if you think something else is more feasible or user-friendly
  - use this SA Opportunity tracking doc, and any relevant other SA/Sales-leader explicit directions and requirements to influence your build:
the team's "Opportunity Technical Update Details" deck (attach it, or link it when running this)
