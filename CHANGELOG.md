# Changelog

## Phase 4 — 2026-09-25

The import path: Evernote export in, canonical prompt out, with the gate
run at the stage where a mistake is still private.

**Added**

- `lib/adapters/enex.py`: stdlib `.enex`/ENML → markdown. It follows
  Evernote's actual layout (one `<div>` per line, `<div><br/></div>` for a
  blank line) rather than generic HTML, and handles code blocks, nested
  lists, todos, tables and links. Attachments and encrypted sections leave an
  `<!-- ingest: ... -->` marker.
- `ingest`: stages each note into `inbox/staged/` with a draft frontmatter,
  pre-declaring any `{{NAME}}` tokens the note already uses. It scans
  everything it staged and writes `inbox/denylist-candidates.txt`. It never
  overwrites a staged file you have edited, and it skips notes already
  promoted.
- `promote`: the one door into `prompts/`/`references/`. It moves the file
  rather than copying it, never overwrites, and refuses a TODO description,
  a leftover omission marker, or anything the gate would block.
- **The Evernote import.** Twelve notes became prompts, with every account,
  person and territory name replaced by a variable, an argument, or a role.
  Two one-off engagement prompts were rewritten as general templates.
- **`customer-account-intelligence` is now a skill:** give it an account name
  and it researches the account's entire history with the company, unless the
  request narrows the scope, and returns a cited internal brief. The standing
  Project instructions it grew from are unchanged in content, renamed
  `customer-account-intelligence-project` to free the id. The values both use
  (`COMPANY`, `PRODUCT_TERMS`, `SALES_METHODOLOGY`) moved to `_shared.env`.

**Fixed**

- **Two customer account names reached the public repo, in Phase 2.** A
  styling note in the forecast reference doc used real deal counts to explain
  account chips, and the gate passed it because the denylist was still a stub.
  Both `source.origin:` fields also carried the internal territory code. All
  three lines were rewritten out of every commit and the branches
  force-pushed; the populated denylist now blocks them. The old commits stay
  reachable on GitHub through the merged PRs' refs until GitHub purges them.
- **Denylist terms were missed when joined by underscores.** `\b` counts `_`
  as a word character, so a term inside an attachment name like
  `<account>_weekly_sync.pdf` never matched, and a multi-word term matched
  only with a single space. Terms are now bounded by letters and digits, and
  the space in a multi-word term also matches `_`, `-` or a line break.
  Matching is still case-sensitive.
- **The gate was blind to filenames.** Denylist matching is case-sensitive
  and content-only, so a lowercase id containing an account name passed
  every hook, and that id is also the skill name and slash command. Paths
  are now matched against each term as a slug, in every scan mode.
- Found while re-verifying before the real import, and fixed before it ran:
  - Current Evernote wraps each list item's text in a `<div>` and writes
    checklists as a styled `<ul>`. Every bullet came out as a bare `-` with
    its text on the next line, and checkboxes were lost.
  - `ingest` matched staged files to notes by filename. A renamed staged
    file (which the path check forces whenever an id contains an account
    name) was re-staged under its old name. Worse, a note whose slug matched
    a hand-made staged file was taken to *be* that file, and `--force` would
    have overwritten it. Staged files are now matched by `source-id`.

**Known gaps**

- **The two account-intelligence prompts share their research rules by
  copy.** There is no include mechanism, and a bundled `reference:` cannot
  carry the Project text: it is rendered on its own and fails on the
  per-invocation `CUSTOMER_NAME`. Both files say so in their frontmatter;
  keeping them in step is manual until an include exists.
- **Skills that take an argument assume Claude Code.** A `from-arg` value
  compiles to a placeholder (`$account`, `$product`) that only a Claude Code
  invocation fills. Uploaded to the account catalog, where claude.ai chats and
  scheduled tasks pass no argument, it would arrive empty or literal.
  `customer-account-intelligence` falls back to the account named in the
  conversation; the other eight do not yet, so reword them before giving any
  of them `distribute: account`.
- **`WALKTHROUGH.md`'s expected output predates the import.** Its commands
  still run, but `list` now shows seventeen entries, not four, and `build`
  reports different file counts.
- Of the 16 exported notes, 12 are promoted. One was the Evernote copy of the
  Project instructions' original source, twice over, with nothing the
  canonical file lacks; its `source-id:` is on that file, so `ingest` skips it.
  Three are not reusable prompts and are deliberately not promoted.
- **`ingest` has no way to decline a note.** A note you choose not to promote
  is re-staged by every `ingest` of the same export, so the only way to be rid
  of it is to delete the export once the import is finished.
- **`init` never creates `private/env/_shared.env`.** Territory and roster
  values resolve from there, so they are set once and fill in automatically,
  but a fresh clone only gets the per-prompt files and has to repeat
  `TERRITORIES`, `SA_TEAM`, `COMPANY` and the rest in each. `init` should also generate
  `_shared.env`, listing every variable declared by two or more prompts.
- The `cluster-kaas` pattern in `lib/patterns.py` names one customer's
  hostname prefix. The file is excluded from its own scan, so the gate cannot
  see this. That prefix belongs in the denylist, which already has it.
- Denylist matching is case-sensitive, so a customer name written in
  lowercase in prose is not caught unless that casing is listed too, and some
  names collide with English words in lowercase.
- The candidate list is a heuristic. It misses a name written in lowercase,
  inside a URL or hostname, or appearing only at a sentence start alongside
  many ordinary verbs.

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
