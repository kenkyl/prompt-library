# Changelog

## Phase 3 — 2026-09-23

Packaged as a plugin, and wrote down two things about Claude's surfaces that
cost live failures to learn.

**Added**

- The build produces a real plugin: `build/plugin/.claude-plugin/plugin.json`
  (name `pl`, version from a committed `VERSION`) plus `skills/<id>/` with the
  bundled `references/`. `install` copies the whole tree to
  `~/.claude/skills/pl/`, where it loads as `pl@skills-dir` and namespaces its
  skills `/pl:<id>`. Loose skills are the "quick experiments" tier per the
  docs; plugins are the tier for versioned, reusable libraries.
- `distribute:` frontmatter, separate from `surfaces:`. What gets *built* and
  where it must *land to be reachable* are different axes.
- `doctor` validates the built plugin and reports pre-plugin loose installs
  with the command to remove them.

**Fixed**

- Builds are reproducible. The managed marker carried a timestamp, so no two
  builds were byte-identical even with identical content. That produced a
  false "installed copy doesn't match" scare, and made every bundled sidecar
  look changed on every install — burying the one that had actually changed.
- Bare `./bin/prompt build` could never succeed, because one prompt needs a
  per-invocation value and that failed the whole run. A sweep now skips and
  reports; naming a prompt explicitly still errors.
- `install` counted SKILL.md writes but not bundled sidecars, so replacing a
  stale reference doc could report "0 written".
- Removed the dead `scheduled: true` install target.

**Learned the hard way — neither is in any documentation**

- **`~/.claude/skills/` is interactive only.** A scheduled task resolves skills
  from the account catalog and cannot see it. Worse, a task told to run a skill
  absent from that catalog does not fail: it picks the closest name it can see
  and proceeds. A run here executed the wrong skill and produced output.
- **A skill that names a knowledge file it does not carry will find the wrong
  one.** A scheduled run searched Drive, found an older copy of the same spec,
  and read it without complaint. Bundling the doc inside the skill fixes it —
  and the pointer must also *forbid* searching elsewhere, because naming the
  path is only half the fix.

**Known gaps**

- No automated reachability check for `distribute: account`. The only local
  view of the account catalog is a mirror that lags by hours, so a check
  against it would report correctly-published skills as missing. Declared
  intent drives a reminder instead.
- **`private/` has no version history.** It is gitignored by design, which is
  correct for secrets — but operationally critical content now lives there
  with no history and no backup, including a CRM field map validated against a
  live org. "Not in the public repo" and "not backed up anywhere" collapsed
  into the same thing, and they should not have.
- `private/denylist.txt` is still a 3-entry stub.

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
