# Walkthrough — testing the toolchain by hand

A copy-pasteable test pass over `./bin/prompt`, organised by the two axes that
actually vary: **where a value comes from** (frontmatter, `_shared.env`,
`<id>.env`, `--var`) and **where the rendered prompt goes** (skill,
instructions, knowledge, cli).

Every command below was run against this repo at `v0.3.0`. Each step states
what to run, what you should see, and what it proves. Steps marked **[writes
outside the repo]** touch `~/.claude/`; steps marked **[destructive]** modify
tracked files and are undone in the cleanup section.

Run everything from the repo root.

```bash
cd ~/Workspace/prompt-library
```

---

## Conventions

- **Always `./bin/prompt`, never `python3 bin/prompt`.** The shebang ignores the
  `python3` shell alias; `doctor` explains why this matters.
- **Read exit codes directly, not through a pipe.** `./bin/prompt check | tail`
  reports the exit code of `tail`, not of `check`. When a step below cares about
  the exit code, run the command bare and then `echo $?`.
- Expected output is abridged where it is long; the lines shown are the ones to
  look for.

---

## Part 0 — Is the environment sane?

### 0.1 Diagnose

```bash
./bin/prompt doctor
```

Expect `doctor: 12 ok, ...` with `0 failures`, including:

```
  ok    core.hooksPath = .githooks
  ok    private/ gitignored
  ok    inbox/ gitignored
  ok    build/ gitignored
  ok    plugin `pl` v0.3.0 manifest valid
  ok    17 pattern families loaded (13 blocking, 4 review)
```

**Proves:** the sanitization gate is wired, the three private directories are
contained, and the built plugin agrees with its manifest.

If `core.hooksPath` is not `.githooks`, the gate is **not active**. Fix it:

```bash
./bin/prompt doctor --fix
```

A `warn` about "pre-plugin loose install still present" is expected if you ever
installed before the plugin form landed — it tells you the `rm -rf` to run.

### 0.2 Inventory

```bash
./bin/prompt list
```

```
id                             kind       status  surfaces                vars  installed
-----------------------------  ---------  ------  ----------------------  ----  ---------
customer-account-intelligence  prompt     ready   instructions,cli        6     -
sa-forecast-brief              prompt     ready   skill,instructions,cli  5     managed
smoke-test                     prompt     ready   skill                   2     managed
sa-forecast-job-spec           reference  ready   knowledge               8     -
```

The `installed` column is the interesting one. It reads
`~/.claude/skills/pl/skills/<id>/SKILL.md` and reports:

| Value | Meaning |
|---|---|
| `-` | not installed (or no `skill` surface, so it never will be) |
| `managed` | installed, and the file's content still matches its own marker |
| `HAND-EDITED` | installed, but someone changed it in place — `install` will refuse |
| `foreign` | a file is there with no marker at all — not ours, `install` will refuse |

**Proves:** the four canonical files load, and the managed-marker round-trip works.

### 0.3 Validate everything

```bash
./bin/prompt check
```

```
  warn  prompts/sa-forecast-brief.md: no Role section (house style)
check: 0 errors, 1 warning, 0 info

worktree scan: 0 blocking, 0 review, 0 allowed
```

That one warning is a known house-style nag, not a failure. Confirm the exit
code is clean:

```bash
./bin/prompt check; echo "exit=$?"
```

Expect `exit=0`.

**Proves:** `check` does all four of its jobs — frontmatter validation, the
body-token ↔ `vars:` set comparison, a smoke-render against *example* values
only, and a full worktree scan.

---

## Part 1 — Sources: where each value comes from

Resolution order, later wins:

1. frontmatter `default:`
2. `private/env/_shared.env`
3. `private/env/<id>.env`
4. `--var KEY=VALUE` on the command line

`env` is the command that shows this applied to one real prompt.

### 1.1 Frontmatter defaults and per-invocation values

```bash
./bin/prompt env smoke-test
```

```
variable    value came from       state
----------  --------------------  -----
TOPIC       -                     per-invocation (pass it as $topic)
FACT_COUNT  frontmatter default:  set (1 chars)

Per-invocation values are not stored. To see this filled in:
  ./bin/prompt env smoke-test '<topic>'
```

Note `TOPIC` is reported as **per-invocation**, not as missing — it is declared
`from-arg: topic`, so the value arrives when the skill is invoked.

### 1.2 A positional argument overriding it

```bash
./bin/prompt env smoke-test "the Dutch tulip mania" --resolved
```

```
TOPIC       command line          set (21 chars)
            the Dutch tulip mania
FACT_COUNT  frontmatter default:  set (1 chars)
            3
```

`--resolved` prints a one-line preview of each value. **Careful: that means it
prints private overlay values too.** Don't paste its output anywhere.

### 1.3 The two .env layers

```bash
./bin/prompt env sa-forecast-brief
```

```
variable               value came from          state
---------------------  -----------------------  -----
TERRITORIES            private/env/_shared.env  set (13 chars)
SA_TEAM                private/env/_shared.env  set (38 chars)
CRM_TOOL               private/env/<id>.env     set (26 chars)
EVIDENCE_SOURCES       private/env/<id>.env     set (617 chars)
MIN_CONSUMPTION_DELTA  private/env/<id>.env     set (6 chars)
```

**Proves:** shared values resolve from `_shared.env`, per-prompt values from
`<id>.env`, and the `value came from` column attributes each one.

### 1.4 `--var` beating both

```bash
./bin/prompt env sa-forecast-brief --var TERRITORIES="Test Region"
```

```
TERRITORIES            --var                    set (11 chars)
SA_TEAM                private/env/_shared.env  set (38 chars)
```

**Proves:** the command line is the highest-priority layer.

### 1.5 A multi-line value loaded from a file

`private/env/<id>.env` supports `KEY=@relative/path.md`, resolved relative to
the .env file's own directory. `EVIDENCE_SOURCES` above is 617 chars because it
comes from a fragment file, not an inline value:

```bash
grep -n "EVIDENCE_SOURCES" private/env/sa-forecast-brief.env
```

Expect a line of the form `EVIDENCE_SOURCES=@../fragments/<name>.md`.

**Proves:** the `@file` indirection works, which is what keeps large private
fragments out of the .env files themselves.

> **Gotcha found while testing:** within a single .env file, a later assignment
> to the same key silently wins. If you uncomment a suggested
> `KEY=@../../env/fragments/...` pointer but leave the original blank `KEY=`
> line below it, the blank wins and the variable reads as MISSING. Delete the
> blank line.

### 1.6 A missing required value

```bash
./bin/prompt env sa-forecast-brief --var CRM_TOOL=""; echo "exit=$?"
```

An unset **required** non-`from-arg` variable reports `MISSING (required)` and
`env` exits 1. This is the state a fresh clone starts in for every private
variable.

---

## Part 2 — Outputs: one canonical file, four surfaces

`surfaces:` in frontmatter says what gets **built**. The four emitters:

| Surface | Built to | Consumed by |
|---|---|---|
| `skill` | `build/plugin/skills/<id>/SKILL.md` | Claude Code, as `/pl:<id>` |
| `instructions` | `build/instructions/<id>.md` | pasted into a Project's or scheduled task's Instructions box |
| `knowledge` | `build/knowledge/<id>.md` | uploaded as a Project knowledge file |
| `cli` | stdout / clipboard | `prompt fill` |

### 2.1 Build everything

```bash
./bin/prompt build
```

```
  skip  customer-account-intelligence:
          supplied per use: {{CUSTOMER_NAME}}
          ./bin/prompt build customer-account-intelligence --var CUSTOMER_NAME='...'
  wrote build/plugin/skills/sa-forecast-brief/SKILL.md
  wrote build/plugin/skills/sa-forecast-brief/references/sa-forecast-job-spec.md
  wrote build/instructions/sa-forecast-brief.md
  wrote env/sa-forecast-brief.env.example
  wrote build/plugin/skills/smoke-test/SKILL.md
  wrote env/smoke-test.env.example
  wrote build/knowledge/sa-forecast-job-spec.md
  wrote env/sa-forecast-job-spec.env.example
  wrote build/plugin/.claude-plugin/plugin.json
build: 9 files, 1 skipped
```

Two behaviours to notice:

- A bare sweep **skips** a prompt needing a per-invocation value, with the
  reason and the exact fix. It does not fail the sweep.
- `env/*.env.example` is regenerated on every build. It is generated output —
  never hand-edit it.

```bash
find build -type f | sort
```

```
build/instructions/sa-forecast-brief.md
build/knowledge/sa-forecast-job-spec.md
build/plugin/.claude-plugin/plugin.json
build/plugin/skills/sa-forecast-brief/SKILL.md
build/plugin/skills/sa-forecast-brief/references/sa-forecast-job-spec.md
build/plugin/skills/smoke-test/SKILL.md
```

### 2.2 Naming a skipped prompt is a hard error, not a skip

```bash
./bin/prompt build customer-account-intelligence; echo "exit=$?"
```

Expect `exit=1` and a `FAIL` naming `{{CUSTOMER_NAME}}`, because you asked for
that one specifically. Supply the value and it succeeds:

```bash
./bin/prompt build customer-account-intelligence --var CUSTOMER_NAME="Northwind Airlines"
```

```
  wrote build/instructions/customer-account-intelligence.md
  wrote env/customer-account-intelligence.env.example
  wrote build/plugin/.claude-plugin/plugin.json
build: 3 files
```

```bash
head -6 build/instructions/customer-account-intelligence.md
```

The generated header names the source file and tells you not to edit the output.
The `--var` value is baked into the body:

```bash
grep -n "CUSTOMER_NAME:" build/instructions/customer-account-intelligence.md
```

Expect `- CUSTOMER_NAME: Northwind Airlines`.

**Proves:** the `instructions` surface has no argument channel, so a `from-arg`
value must be baked in at build time — and the build enforces that.

### 2.3 The `skill` surface keeps `from-arg` as a runtime placeholder

```bash
cat build/plugin/skills/smoke-test/SKILL.md
```

```
---
name: smoke-test
description: Verify the prompt-library toolchain end to end. Use when the user asks to smoke-test the prompt library, or says "run the smoke test".
arguments: [topic]
---
...
State 3 verifiable facts about $topic. One line each.
...
<!-- prompt-library:managed id=smoke-test surface=skill content-sha256=031652c2... -->
```

Three things at once: `{{TOPIC}}` compiled to `$topic` (runtime), `{{FACT_COUNT}}`
resolved to `3` (build time, from the frontmatter default), and a managed marker
carrying a content hash.

**Proves:** the same variable layer serves two different timing models depending
on the surface.

### 2.4 The `cli` surface

```bash
./bin/prompt fill smoke-test "the Dutch tulip mania" --stdout
```

```
## Role

You are a terse reference assistant. No preamble.

## Method

State 3 verifiable facts about the Dutch tulip mania. One line each.
...
```

Without `--stdout` it goes to the clipboard instead:

```bash
./bin/prompt fill smoke-test "the Dutch tulip mania"
```

```
smoke-test: 20 chars copied to the clipboard.
```

If `pbcopy` is unreachable the command falls back to stdout and tells you to
pipe it yourself — it does not silently succeed.

**Proves:** positional args map onto `from-arg` vars via the `arguments:` order,
and the same ordering serves both the `skill` and `cli` surfaces.

### 2.5 `show` — canonical vs rendered

```bash
./bin/prompt show smoke-test | head -5
```

The raw canonical file, frontmatter included.

```bash
./bin/prompt show smoke-test --rendered --var TOPIC="bridge engineering" | head -8
```

Fully substituted, frontmatter stripped.

> `show` takes `--var` only — **not** positional arguments. `./bin/prompt show
> smoke-test "bridge engineering" --rendered` fails with `show takes exactly one
> id`. Use `fill` when you want positional args.

Run it with nothing supplied and it renders the literal token and exits 1:

```bash
./bin/prompt show smoke-test --rendered >/dev/null; echo "exit=$?"
```

Expect `exit=1` and `unresolved: TOPIC` on stderr.

### 2.6 The bundled reference doc — two pointer forms

`sa-forecast-brief` declares `reference: sa-forecast-job-spec`. The two delivery
routes get deliberately different instructions.

```bash
sed -n '7,16p' build/plugin/skills/sa-forecast-brief/SKILL.md
```

```
Read `references/sa-forecast-job-spec.md`, which ships inside this skill's own directory,
for all queries, field mappings and rules. Do not re-derive them.

That bundled file is the only authoritative copy. If it is missing,
say so and stop. Do not search Drive, the enterprise search
connector, or anywhere else for a file with a similar name --
older copies of this spec exist, and reading one silently produces
a brief built on stale field mappings.
```

```bash
sed -n '6,8p' build/instructions/sa-forecast-brief.md
```

```
Reference the project knowledge file `sa-forecast-job-spec` for all queries, field
mappings and rules. Do not re-derive them.
```

**Proves:** the `skill` surface bundles the doc and closes the fallback search;
the `instructions` surface, having no bundling channel, points at a Project
knowledge file instead.

Confirm the doc actually travels:

```bash
ls build/plugin/skills/sa-forecast-brief/references/
```

Expect `sa-forecast-job-spec.md`.

### 2.7 Build output is reproducible

```bash
shasum build/plugin/skills/smoke-test/SKILL.md
./bin/prompt build smoke-test >/dev/null && shasum build/plugin/skills/smoke-test/SKILL.md
```

Both hashes must match. The managed marker deliberately carries **no
timestamp**, so `diff -r` between two builds means "the templates differ" and
nothing else.

---

## Part 3 — Install **[writes outside the repo]**

`install` builds, then copies the plugin into
`~/.claude/skills/pl/`. A folder there containing
`.claude-plugin/plugin.json` loads as `pl@skills-dir` and namespaces its skills
as `/pl:<id>`.

### 3.1 Preview without writing

```bash
./bin/prompt install --dry-run
```

```
  skip  customer-account-intelligence: no skill surface (surfaces: instructions,cli). Its build/ output is for manual upload.
  ok    sa-forecast-brief -> /Users/<you>/.claude/skills/pl/skills/sa-forecast-brief/SKILL.md (unchanged)
  ok    smoke-test -> /Users/<you>/.claude/skills/pl/skills/smoke-test/SKILL.md (unchanged)
  skip  sa-forecast-job-spec: no skill surface (surfaces: knowledge). Its build/ output is for manual upload.

install: 0 written, 0 pruned, 0 refused

  sa-forecast-brief also needs an ACCOUNT save -- install does not and cannot do this.
  ...
```

**Proves:** `install` only handles the `skill` surface; `instructions` and
`knowledge` output is for you to paste or upload. And `distribute: account`
triggers a reminder on every run, because a local install alone leaves any
scheduled copy stale.

### 3.2 Install for real

```bash
./bin/prompt install
```

On a first install you should see `ok` lines for the plugin manifest, each
SKILL.md, and each bundled reference doc, then:

```
Restart your Claude Code session to pick these up -- skills are read at session start.
```

Verify the tree:

```bash
find ~/.claude/skills/pl -type f | sort
```

```
~/.claude/skills/pl/.claude-plugin/plugin.json
~/.claude/skills/pl/skills/sa-forecast-brief/SKILL.md
~/.claude/skills/pl/skills/sa-forecast-brief/references/sa-forecast-job-spec.md
~/.claude/skills/pl/skills/smoke-test/SKILL.md
```

### 3.3 The end-to-end test

Restart your Claude Code session, then run:

```
/pl:smoke-test the Dutch tulip mania
```

Expect exactly three `- ` lines about tulip mania, no preamble. That is the
whole point of `smoke-test`: it needs no configuration, so it isolates "is the
toolchain working" from "is my overlay filled in".

Confirm `list` now agrees:

```bash
./bin/prompt list
```

`smoke-test` and `sa-forecast-brief` should both read `managed`.

### 3.4 Hand-edit detection **[writes outside the repo]**

This is the guard that stops `install` from silently destroying a local edit.

```bash
printf '\n<!-- hand edit -->\n' >> ~/.claude/skills/pl/skills/smoke-test/SKILL.md
```

```bash
./bin/prompt list
```

`smoke-test` should now read `HAND-EDITED`.

```bash
./bin/prompt install smoke-test; echo "exit=$?"
```

```
  REFUSED smoke-test -> /Users/<you>/.claude/skills/pl/skills/smoke-test/SKILL.md
          that file was hand-edited since install
          --adopt  copy it to inbox/staged/ so you can merge the edit back into canonical
          --force  discard it and overwrite
```

Expect `exit=1`. Now rescue the edit:

```bash
./bin/prompt install smoke-test --adopt
```

```
  adopt /Users/<you>/.claude/skills/pl/skills/smoke-test/SKILL.md -> inbox/staged/smoke-test.adopted.md
          now reconcile it into prompts/smoke-test.md, then re-run install
```

```bash
ls inbox/staged/smoke-test.adopted.md
```

> `--adopt` copies the edit out and **stops** — it does not install. The target
> is still hand-edited afterwards, so once you have reconciled the edit into
> `prompts/smoke-test.md` you need `--force` to overwrite the stale copy.

Restore the managed state:

```bash
./bin/prompt install smoke-test --force
```

```bash
./bin/prompt list
```

Back to `managed`. Clean up the adopted scratch file:

```bash
rm -f inbox/staged/smoke-test.adopted.md
```

**Proves:** a file's marker records the hash of its own content, so an in-place
edit is detected rather than overwritten, and there is a non-destructive way out.

### 3.5 Stale bundled-doc pruning

A rename of a `reference:` would otherwise leave the old doc readable in the
install directory — the exact failure the bundling exists to prevent. Simulate
an orphan by copying a marked doc under a second name:

```bash
cp ~/.claude/skills/pl/skills/sa-forecast-brief/references/sa-forecast-job-spec.md \
   ~/.claude/skills/pl/skills/sa-forecast-brief/references/old-spec.md
```

```bash
./bin/prompt install sa-forecast-brief
```

```
  pruned stale bundled doc /Users/<you>/.claude/skills/pl/skills/sa-forecast-brief/references/old-spec.md
```

An **unmarked** file placed there is left alone — only files carrying this
repo's own marker are pruned. Verify:

```bash
echo "not ours" > ~/.claude/skills/pl/skills/sa-forecast-brief/references/mine.md
./bin/prompt install sa-forecast-brief
ls ~/.claude/skills/pl/skills/sa-forecast-brief/references/
```

`mine.md` should survive. Remove it yourself:

```bash
rm ~/.claude/skills/pl/skills/sa-forecast-brief/references/mine.md
```

---

## Part 4 — Package for the account catalog

`~/.claude/skills/` is **interactive only**. A scheduled task resolves skills
from your account catalog and cannot see it. `package` produces the upload
artifact in the one shape the catalog accepts.

### 4.1 Sweep

```bash
./bin/prompt package
```

```
  skip  customer-account-intelligence: no skill surface (surfaces: instructions,cli)
  ok    sa-forecast-brief -> build/upload/sa-forecast-brief.zip  (2 files, 15.7 KB)
          sa-forecast-brief/SKILL.md
          sa-forecast-brief/references/sa-forecast-job-spec.md
  skip  smoke-test: no `distribute: account`, so it needs no account save
  skip  sa-forecast-job-spec: no skill surface (surfaces: knowledge)

package: 1 written, 3 skipped
```

**Proves:** only a prompt with both the `skill` surface **and**
`distribute: account` gets a zip. Everything else is skipped with its reason.

### 4.2 The zip shape

```bash
unzip -l build/upload/sa-forecast-brief.zip
```

```
     5060  01-01-1980 00:00   sa-forecast-brief/SKILL.md
    33988  01-01-1980 00:00   sa-forecast-brief/references/sa-forecast-job-spec.md
```

Two properties to check:

- **Every entry is under a top-level `<id>/` folder.** A `SKILL.md` at the zip
  root is rejected by the catalog.
- **The bundled `references/` travelled with it.** A skill that arrives naming a
  file it does not carry is worse than one that never bundled, because the
  generated pointer also forbids the fallback search.

The fixed `1980-01-01` timestamps are deliberate.

### 4.3 Reproducibility — the "do I need to re-upload?" test

```bash
shasum build/upload/sa-forecast-brief.zip
./bin/prompt package sa-forecast-brief >/dev/null && shasum build/upload/sa-forecast-brief.zip
```

Both hashes must match. That is what makes `shasum` a reliable answer to
"has this changed since I last uploaded it?".

### 4.4 A custom output directory

```bash
./bin/prompt package sa-forecast-brief --out "$TMPDIR/pl-zips"
ls "$TMPDIR/pl-zips"
```

```bash
rm -rf "$TMPDIR/pl-zips"
```

### 4.5 What `package` deliberately will not do

It does not upload. There is no API for the catalog. After any prompt change the
full sequence is `build` → `install` → `package` → **re-upload by hand**, then
run the scheduled task once manually and confirm from the progress panel that it
loaded *your* skill. A scheduled task pointed at a skill that is not in the
catalog does **not** fail — it picks the closest name it can see and proceeds.

---

## Part 5 — Failure paths: prove the guards actually fire

`check` is only worth running if it catches things. These steps create a
throwaway prompt, break it six ways, and confirm each break is reported.

### 5.1 Scaffold

```bash
./bin/prompt new walkthrough-demo
```

```
created prompts/walkthrough-demo.md
Edit it, then: ./bin/prompt check walkthrough-demo
```

Invalid ids are rejected up front, because the id becomes a filename, a skill
directory and a slash command:

```bash
./bin/prompt new Bad_Id; echo "exit=$?"
```

Expect `exit=2` and an explanation.

### 5.2 Write a deliberately broken version

```bash
cat > prompts/walkthrough-demo.md <<'EOF'
---
id: walkthrough-demo
title: Walkthrough demo
description: A throwaway prompt used to exercise the toolchain's error paths.
kind: prompt
status: draft
surfaces: [skill, cli]
arguments: [subject]
vars:
  - name: SUBJECT
    required: true
    from-arg: subject
    describe: What to write about.
    example: bridge engineering
  - name: TONE
    default: neutral
    describe: Voice to use.
---

## Role

Demo prompt.

## Method

Write about {{SUBJECT}} in a {{TONE}} tone. Also mention {{UNDECLARED}}.

## Output contract

One paragraph.
EOF
```

### 5.3 A body token with no declaration

```bash
./bin/prompt check walkthrough-demo; echo "exit=$?"
```

```
  FAIL  prompts/walkthrough-demo.md: body uses {{UNDECLARED}} but it is not declared under `vars:`
check: 1 error, 0 warnings, 0 info
exit=1
```

### 5.4 A declaration with no body token (the renamed-variable case)

```bash
sed -i '' 's/ Also mention {{UNDECLARED}}\.//; s/in a {{TONE}} tone/in a plain tone/' prompts/walkthrough-demo.md
./bin/prompt check walkthrough-demo; echo "exit=$?"
```

```
  FAIL  prompts/walkthrough-demo.md: `vars:` declares TONE but the body never uses {{TONE}} (renamed it?)
exit=1
```

**Proves:** the set comparison errors in **both** directions. This is the whole
argument for frontmatter-as-contract — a renamed variable fails the build
instead of rendering as literal text.

### 5.5 An unbalanced section guard

```bash
sed -i '' 's/in a plain tone/in a {{TONE}} tone/' prompts/walkthrough-demo.md
printf '\n{{#IF_TONE}}\n## Optional block\nTone was supplied.\n' >> prompts/walkthrough-demo.md
./bin/prompt check walkthrough-demo; echo "exit=$?"
```

```
  FAIL  prompts/walkthrough-demo.md: line 14: {{#IF_TONE}} has no matching {{/IF_TONE}}
exit=1
```

### 5.6 A reserved token

```bash
printf '{{/IF_TONE}}\n\nHandle $ARGUMENTS directly.\n' >> prompts/walkthrough-demo.md
./bin/prompt check walkthrough-demo; echo "exit=$?"
```

```
  FAIL  prompts/walkthrough-demo.md: line 19: $ARGUMENTS is reserved -- the compiler emits it. Declare a var with `from-arg:` instead
exit=1
```

`$1` is reserved for the same reason.

> **False positive worth knowing about:** a literal grouped dollar figure like
> `$1,2NN,NNN` in a body also trips the reserved-`$1` check, because the match
> starts at `$1`. Move figures into a variable — which the money patterns in
> Part 6 want anyway.

### 5.7 A clean version, and the guard rendering

```bash
cat > prompts/walkthrough-demo.md <<'EOF'
---
id: walkthrough-demo
title: Walkthrough demo
description: A throwaway prompt used to exercise the toolchain's error paths.
kind: prompt
status: draft
surfaces: [skill, cli]
arguments: [subject]
vars:
  - name: SUBJECT
    required: true
    from-arg: subject
    describe: What to write about.
    example: bridge engineering
  - name: TONE
    default: neutral
    describe: Voice to use.
---

## Role

Demo prompt.

## Method

Write about {{SUBJECT}} in a {{TONE}} tone.

{{#IF_TONE}}
## Tone note

Tone was supplied, so this block renders.
{{/IF_TONE}}

## Output contract

One paragraph.
EOF
./bin/prompt check walkthrough-demo; echo "exit=$?"
```

Expect `0 errors` and `exit=0`.

```bash
./bin/prompt build walkthrough-demo
cat build/plugin/skills/walkthrough-demo/SKILL.md
```

`TONE` has a default, so the `{{#IF_TONE}}` block renders. Drop it to see the
block disappear — heading and all:

```bash
./bin/prompt build walkthrough-demo --var TONE=
grep -c "Tone note" build/plugin/skills/walkthrough-demo/SKILL.md
```

Expect `0`.

### 5.8 Generated variable documentation

```bash
cat env/walkthrough-demo.env.example
```

```
# GENERATED by ./bin/prompt build -- do not edit.
# Edit the `vars:` block in prompts/walkthrough-demo.md instead.
...
# What to write about.
#   [REQUIRED; supplied at invocation as $subject in the skill surface]
SUBJECT=bridge engineering

# Voice to use.
# default: neutral
TONE=
```

**Proves:** `env/*.env.example` is derived from frontmatter, so it cannot drift
from the contract.

> **Worth knowing:** a **non-private** variable with an `example:` is written
> into the example file *pre-filled with that example value*, and `init` copies
> it verbatim into `private/env/`. So a variable can read as "set" on a fresh
> clone while holding placeholder data. `private: true` variables are always
> written blank. When testing a new clone, skim the generated .env files rather
> than assuming a `set` state means you supplied the value.

---

## Part 6 — The sanitization gate

Two independent layers: 17 committed regex families in `lib/patterns.py`, and a
gitignored `private/denylist.txt`. `scan/allow.txt` can suppress a pattern
family for a given path with a stated reason; it deliberately **cannot**
suppress a denylist hit.

### 6.1 Plant a finding

The command below assembles the offending string at runtime so this guide file
itself stays scan-clean.

```bash
printf '\nRead the field Account_Tier%s.\n' '__c' >> prompts/walkthrough-demo.md
```

### 6.2 Manual scan

```bash
./bin/prompt scan --all; echo "exit=$?"
```

```
BLOCKING (1)
  prompts/walkthrough-demo.md:NN  sfdc-field             <matched text>
      why: Salesforce custom field or relationship -- internal CRM schema.
      fix: Move the field map into a private overlay variable, or allow this path in scan/allow.txt if the prompt is useless without it.

worktree scan: 1 blocking, 0 review, 0 allowed

Not blocking anything -- this was a manual scan. ...
exit=1
```

The finding names the pattern family, the matched text, why it matters, and the
fix. Your real output echoes the offending string in the `<matched text>`
column; it is masked here so that **this guide file itself passes the
scan** — which is the gate working, on this very file.

### 6.3 `check` and `build` are gated by it

```bash
./bin/prompt check walkthrough-demo; echo "exit=$?"
```

```
check: 0 errors, 0 warnings, 0 info

BLOCKING (1)
  prompts/walkthrough-demo.md:NN  sfdc-field             <matched text>
...
worktree scan: 1 blocking, 0 review, 0 allowed
exit=1
```

Note `0 errors` — the frontmatter and body are perfectly valid. The scan runs as
`check`'s **last** step and fails it independently.

> **Ordering matters:** if `check` finds any frontmatter or body error it
> returns *before* scanning. So a prompt has to pass validation before the scan
> findings become visible. If you want the scan output, fix the validation
> errors first — or run `./bin/prompt scan --all` directly.

```bash
./bin/prompt build walkthrough-demo; echo "exit=$?"
```

Same findings, then:

```
build aborted: fix check first.
exit=1
```

### 6.4 The pre-commit hook **[modifies git index]**

```bash
git log --oneline -1                       # note this, you will compare against it
```

```bash
git add prompts/walkthrough-demo.md
git commit -m "walkthrough demo (should be blocked)"; echo "exit=$?"
```

```
BLOCKING (1)
  prompts/walkthrough-demo.md:NN  sfdc-field             <matched text>
...
pre-commit scan: 1 blocking, 0 review, 0 allowed

Nothing was committed. Fix the blocking findings above, or -- if one is a false
positive -- add a path-scoped entry to scan/allow.txt with a reason,
or re-tier the term in private/denylist.txt.
exit=1
```

Confirm nothing landed:

```bash
git log --oneline -1
```

The HEAD commit must be identical to the one you noted above. The file stays
**staged** — the hook rejects the commit, it does not unstage your work.

**Proves:** the gate scans **staged blob content**, independently of which
command produced the change.

The pre-push hook scans every commit being pushed, so `--no-verify` on a commit
does not get anything out. Testing that end to end needs a throwaway remote and
is out of scope here; the hook is present and executable per `doctor`.

### 6.5 Unstage and clean up

```bash
git reset -q prompts/walkthrough-demo.md
rm -f prompts/walkthrough-demo.md env/walkthrough-demo.env.example
rm -rf build/plugin/skills/walkthrough-demo
./bin/prompt build >/dev/null && ./bin/prompt check; echo "exit=$?"
```

Expect `0 errors`, `0 blocking`, `exit=0`, and `git status --short` empty.

---

## Part 7 — The fresh-clone test

The hardest claim the repo makes: a clone with **no private overlay at all**
still validates, and still builds the subset it can. Test it in a scratch
directory so your real overlay is not involved.

### 7.1 Clone

```bash
git clone --branch "$(git branch --show-current)" . /tmp/pl-clone && cd /tmp/pl-clone
```

### 7.2 Validate with no overlay

```bash
./bin/prompt check; echo "exit=$?"
```

```
  warn  prompts/sa-forecast-brief.md: no Role section (house style)
check: 0 errors, 1 warning, 0 info

worktree scan: 0 blocking, 0 review, 0 allowed
exit=0
```

**Proves:** `check` smoke-renders against `example:` / `example-file:` values
only, so it passes with no `private/` directory. This is the property that makes
the repo cloneable.

### 7.3 Partial build with no overlay

```bash
./bin/prompt build
```

```
  skip  customer-account-intelligence:
          unset in the overlay: {{COMPANY}}, {{PRODUCT_TERMS}}, {{SALES_METHODOLOGY}}, {{METHODOLOGY_DELIVERABLES}}
          fill private/env/customer-account-intelligence.env (see env/customer-account-intelligence.env.example)
          supplied per use: {{CUSTOMER_NAME}}
          ./bin/prompt build customer-account-intelligence --var CUSTOMER_NAME='...'
  skip  sa-forecast-brief:
          unset in the overlay: {{TERRITORIES}}, {{SA_TEAM}}, {{CRM_TOOL}}, {{EVIDENCE_SOURCES}}, {{MIN_CONSUMPTION_DELTA}}
          fill private/env/sa-forecast-brief.env (see env/sa-forecast-brief.env.example)
  skip  sa-forecast-job-spec:
          unset in the overlay: {{TERRITORIES}}, {{SA_TEAM_LEAD}}, {{SA_TEAM}}, {{FISCAL_CALENDAR}}, {{SCOPE_FILTERS}}, {{QUERY_AND_SIGNAL_RULES}}, {{LINK_TEMPLATE}}
          fill private/env/sa-forecast-job-spec.env (see env/sa-forecast-job-spec.env.example)
  wrote build/plugin/skills/smoke-test/SKILL.md
  wrote env/smoke-test.env.example
  wrote build/plugin/.claude-plugin/plugin.json
build: 3 files, 3 skipped
```

**Proves the two claims that matter most:** `smoke-test` builds with zero
configuration, and the three prompts that need values are **skipped with the
reason and the fix**, not treated as failures. A partial setup gives a working
subset.

Note the two distinct skip reasons — "unset in the overlay" (fill the .env)
versus "supplied per use" (pass `--var`). They need different fixes.

### 7.4 Seed the overlay

```bash
./bin/prompt init
```

```
  made  private/env/customer-account-intelligence.env
  made  private/env/sa-forecast-brief.env
  made  private/env/sa-forecast-job-spec.env
  made  private/env/smoke-test.env

init: 4 created, 0 kept. Fill in the blanks, then ./bin/prompt check
```

```bash
cat private/env/sa-forecast-job-spec.env
```

Each private multi-line variable carries a commented pointer at the committed
public example:

```
#   SCOPE_FILTERS=@../../env/fragments/sa-forecast-scope-filters.example.md
SCOPE_FILTERS=
```

Uncomment the pointer, **delete the blank `SCOPE_FILTERS=` line below it**
(see the gotcha in 1.5), and fill in the scalar blanks. Then:

```bash
./bin/prompt build
```

With every private variable pointed at its public example fragment, all four
canonical files build:

```
build: 11 files
```

### 7.5 Confirm the overlay is what drives output

```bash
head -4 build/knowledge/sa-forecast-job-spec.md
```

In the clone, built from public examples:

```
# Northern Europe SA Technical & Deal Forecast — Scheduled Job Spec

**Owner:** A. Architect — SA Team Lead, Northern Europe
**Team:** A. Architect, B. Engineer, C. Consultant
```

The same line in your real repo shows your real values.

```bash
./bin/prompt package sa-forecast-brief >/dev/null && shasum build/upload/sa-forecast-brief.zip
```

That hash will **differ** from your real repo's zip hash for the same prompt.

**Proves:** identical committed templates plus a different overlay produce a
different artifact — which is the reason the plugin is a build output rather
than something shipped through a marketplace.

### 7.6 Idempotent init

```bash
./bin/prompt init
```

```
  keep  private/env/customer-account-intelligence.env (already exists)
  ...
init: 0 created, 4 kept. Fill in the blanks, then ./bin/prompt check
```

**Proves:** `init` never clobbers a filled-in overlay.

### 7.7 Clean up

```bash
cd ~/Workspace/prompt-library && rm -rf /tmp/pl-clone
```

---

## Part 8 — Final state check

```bash
git status --short
```

Must be empty.

```bash
./bin/prompt check; echo "exit=$?"
```

Expect `0 errors`, `0 blocking`, `exit=0`.

```bash
./bin/prompt doctor; echo "exit=$?"
```

Expect `0 failures`, `exit=0`.

```bash
./bin/prompt list
```

`smoke-test` and `sa-forecast-brief` should read `managed`.

---

## Exit-code reference

| Command | 0 | 1 | 2 |
|---|---|---|---|
| `check` | no errors, scan clean | errors, or blocking scan findings | — |
| `build` | built (skips are not failures) | check failed, or a **named** prompt has an unset required var | — |
| `install` | all targets written or unchanged | something was refused (hand-edited / foreign / permission error) | — |
| `package` | zips written, skips reported | check failed, or an account-catalog name/shape rule violated | `--out` given with no directory |
| `fill` | rendered | unresolved variable, or clipboard unreachable | no id given |
| `env` | every required var resolves | a required var is `MISSING` | no id given |
| `scan` | nothing blocking | blocking findings | unknown mode |
| `doctor` | no failures | at least one failure | — |
| `new` | created | file already exists | bad id, or wrong arg count |
| `show` | rendered | unresolved variable | not exactly one id |

---

## Notes and caveats found while writing this

- **`install` writes to `~/.claude/skills/`, outside the repo.** If you run
  these commands from a sandboxed agent session, that write is refused with
  `Operation not permitted`. The CLI handles it cleanly — it reports the failure,
  names the built file, and tells you to copy it yourself — but Parts 3 and 3.4–3.5
  need a normal terminal.
- **`--resolved` on `env`, and the whole of `build/`, contain real private
  values by design.** `build/` is gitignored unconditionally for that reason.
  Don't paste either into a ticket or a chat.
- **The README's "One writer" section mentions `ingest` and `promote` commands.**
  Neither exists in `bin/prompt` today; the implemented verbs are `list`, `show`,
  `check`, `build`, `install`, `package`, `fill`, `env`, `init`, `new`, `scan`,
  `doctor`. Worth reconciling one way or the other.
- **`./bin/prompt check` on a fresh clone warns about a missing Role section in
  `sa-forecast-brief`.** It is a house-style nag with no effect on output.
