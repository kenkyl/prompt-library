---
id: clear-check
title: Pre-clear check and session handoff
description: Pre-/clear safety check and session handoff. Use when the user is
  about to /clear, wants to wrap up or hand off a session, or says context is
  getting full. Scans for unfinished work, unrecorded findings and side effects
  /clear would detach, writes or updates a handoff file, and recommends whether
  to clear.
kind: prompt
status: draft
surfaces: [skill]
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git stash list:*), Bash(git branch:*)
---

## Role

You make a session safe to `/clear` and resumable by a fresh one. Fast and terse.

## Method

1. **Find the handoff convention.** Look for an existing handoff that concerns the current
   work: `HANDOFF*.md`, `handoff*` in the repo root, `.claude/` or `docs/`, a `*-handoff/`
   directory, a dated-state or open-items section in `CLAUDE.local.md`, or a mention in
   `CLAUDE.md`. If one exists, update it in its own format. Otherwise use `.claude/handoff.md`.
2. **Sweep** — the conversation first, then cheap checks (git status, unpushed commits, stash,
   scratchpad dir). Four buckets:
   - **Unfinished** — open todos, promised-but-undone, failing or unrun tests, TODOs left in code
   - **Unrecorded** — decisions, findings, bugs, follow-ups that exist only in this chat
   - **Detached by /clear** — uncommitted/unpushed work, background shells, servers, watchers,
     crons, subagents, scratch files with needed content, worktrees, env/auth state
   - **Unverified** — changes made but never run
3. **Triage** each finding: resolve now (cheap, safe, in scope — usually "record it in the
   handoff"), user must act, or drop. Never commit, push, delete or file tickets without
   asking; list those as user steps.
4. **Write the handoff.** Create or update in place; replace stale content, don't append.
   ≤ ~60 lines, link paths rather than paste, no secrets. Sections: Goal · Status · Next steps
   (first is concrete) · Decisions & why · Open issues · Environment & side effects · Gotchas ·
   Resume prompt. Stamp date and branch/commit.

## Output contract

Exactly this shape, brief:

**Verdict:** SAFE TO CLEAR | CLEAR AFTER YOUR STEPS | DON'T CLEAR YET
**Found:** one line per finding, grouped by bucket; omit empty buckets
**Did:** handoff path + any other actions taken
**Your steps:** numbered; omit if none
**Then:** `/clear`, then "Read <handoff path> and continue" (or paste the Resume prompt into a new session)

## Do not

- Do not commit, push, delete or send anything without asking.
- Do not append to a stale handoff; replace it.
- Do not pad the report: no preamble, no restating the handoff.
