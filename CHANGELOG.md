# Changelog

## Phases 0-1 — 2026-09-21

One canonical file per prompt, compiled into the surfaces I actually use,
behind a gate that makes sensitive content structurally unable to reach a
commit.

**Added**

- `bin/prompt` — the single interface: `list` `show` `check` `build`
  `install` `fill` `env` `init` `new` `scan` `doctor`.
- Sanitization gate: 17 committed regex families plus a gitignored,
  hand-curated denylist. `pre-commit` scans staged blobs, `pre-push` scans
  every commit being pushed, so `--no-verify` gets nothing out. Every
  finding is reported at once.
- Surface emitters: skill (which is also the slash command), claude.ai
  Project instructions, Project knowledge.
- `{{VAR}}` substitution with indentation-preserving multi-line values, and
  one conditional construct for optional sections.
- Variable contract in frontmatter, values in `.env`, `env/*.env.example`
  generated — so a renamed variable fails `check` instead of silently
  rendering as literal text.
- Private overlay: `private: true` variables resolve from outside the repo at
  build time, with committed example fragments showing the expected shape.
- `prompts/customer-account-intelligence.md` — account-dedicated project
  instructions. Company methodology and an optional price book both resolve
  from the overlay.
- `prompts/smoke-test.md` — the only thing exercising the skill surface.
- MIT license.

**Fixed during verification**

- `new` accepted ids that discovery then silently skipped.
- `install` crashed instead of reporting an unwritable target.
- `env` reported per-invocation variables as `MISSING` and exited nonzero.

**Known gaps**

- `private/denylist.txt` is a 3-entry stub. Populate it before importing real
  prompts — the regex families alone do not catch account names.
- No `ingest` / `promote` yet. Imports are a manual paste into
  `inbox/staged/`.
- The gate catches named entities it has been told about. It will not catch
  paraphrase, a pasted verbatim quote, or re-identification by combination.

## Initial — 2026-09-15

Repo created: `.gitignore` and a placeholder README. No tooling yet.
