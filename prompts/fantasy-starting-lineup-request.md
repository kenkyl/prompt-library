---
id: fantasy-starting-lineup-request
title: Original request that produced the fantasy-starting-lineup skill
description: The original claude.ai request that created the fantasy-starting-lineup
  skill (weekly fantasy football start/sit with own projections, ranges, waiver
  analysis and a visual board). Use as a reference or starting point when asking
  Claude to build or rebuild a similar per-league analysis skill.
kind: prompt
status: ready
surfaces: [cli]
source:
  system: claude.ai
  origin: Project "Football Picks & Fantasy" chat
  imported: 2026-10-31
---

Review, analyze, and confirm or adjust starting lineup for espn league. Also, create a fantasy-starting-lineup or similar skill that I can reuse for every league that:
- does deep player-by-player research and analysis, focusing on all relevant key facts, stats, news, trends, game setting, etc.
- creates its own projected points per player, based on research of reliable sources and independent research and calculations, includes a comparison and explains the discrepancy if any
- provides a clear, concise lineup recommendation
- uses colors, visuals, diagrams for an easy to read output
- cites sources
- asks clarifying questions if needed
- expects screenshots or input list of roster
- otherwise uses latest roster in memory/context/project knowledge/most recent relevant sessions for same team
- first run for a new team expects or asks for (if not found in memory/context/project knowledge/most recent relevant sessions for same team) league, scoring/league rules, and any other relevant/required details for the skill
- user can also include available players on waivers/free agency, and the skill should analyze all available players individually in the same manner; then recommend any adds/drops if recommended to increase win %
- never make anything up, always state when unsure
- always give a backup or secondary option with a brief explanation of trade offs (when it makes sense; not needed for an easy lineup lock)
- include in visuals a likely scoring range for each player and the team
- always be clear and concise in your outputs; user will ask for verbosity or deeper explanations if needed
