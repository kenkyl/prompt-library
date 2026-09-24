# prompt-library

One canonical file per prompt, compiled into every surface I actually use:
Claude Code skills (which are also slash commands), claude.ai Project
instructions and knowledge files, and the clipboard.

The problem it solves: the same prompt text was living in two or three places
at once and drifting. Now there is exactly one copy, and the others are built
from it.

## How it works

One canonical file goes in; a variable layer resolves it; a surface emitter
shapes it for wherever it's consumed:

```
prompts/<id>.md, references/<id>.md          <- the only thing you hand-edit
        |
        |  frontmatter `vars:` is the contract: {{NAME}} tokens in the body
        |  must match declared vars exactly, in both directions
        v
+- variable resolution (lib/envfile.py) -------------------------------------+
|                                                                            |
|  frontmatter          private/env/         private/env/      --var K=V /   |
|  example:/default:  > _shared.env       >  <id>.env       >  CLI args      |
|  (check's smoke        (shared secrets)     (per-prompt        (highest    |
|   test values)                               values)            priority)  |
|                                                                            |
+----------------------------------------------------------------------------+
        |
        |  {{VAR}} substitution + {{#IF_VAR}} section guards (lib/template.py)
        v
+- surface emitters (lib/surfaces.py) ---------------------------------------+
|                                                                            |
|   skill              instructions           knowledge           cli        |
|     |                     |                      |                |        |
|     v                     v                      v                v        |
|  build/plugin/       build/instructions/    build/knowledge/   stdout /    |
|   .claude-plugin/    <id>.md                <id>.md            pbcopy      |
|     plugin.json       (paste into            (upload as         (`prompt   |
|   skills/<id>/         a Project's or a       Project              fill`)  |
|     SKILL.md           scheduled task's       knowledge file)              |
|     references/        Instructions box)                                   |
|       <ref>.md                                                             |
|     |                                                                      |
|     |  the reference doc is BUNDLED, so the skill carries its own spec     |
|     |  and never has to find it by name                                    |
|     v                                                                      |
|  `install` copies the whole plugin to ~/.claude/skills/pl/, where a        |
|  folder with .claude-plugin/plugin.json loads as `pl@skills-dir` and       |
|  namespaces its skills /pl:<id>. Each file is tagged with a managed        |
|  marker (content-sha256) so a later hand-edit there is detected instead    |
|  of silently overwritten.                                                  |
|                                                                            |
|  That root is INTERACTIVE ONLY. A scheduled task cannot see it -- see      |
|  the Surfaces table below.                                                 |
|                                                                            |
+----------------------------------------------------------------------------+
        |
        |  every declared var is also written out as env/<id>.env.example
        v  (public, documents the contract, never holds real values)

A pre-commit/pre-push scan (lib/scan.py + lib/patterns.py + private/denylist.txt)
gates every commit and push regardless of which command produced the change,
so a private value can never reach a committed file through any path above.
```

Reading it top to bottom: `check` validates the top box and smoke-renders it
with example values only; `build` runs the full pipeline down to `build/`;
`install` additionally copies the plugin into `~/.claude/skills/pl/`;
`fill` shortcuts straight to the `cli` branch. `env <id>` prints which layer
supplied each variable's value, which is the fastest way to see this diagram
applied to one real prompt.

## Quickstart — clone to working

Nothing private is committed, so a fresh clone builds against *your* values, not
anyone else's.

```bash
./bin/prompt doctor --fix      # wire the pre-commit/pre-push gate
```

```bash
./bin/prompt init              # private/env/ from the committed examples
```

Fill in the blanks in `private/env/*.env`. Each generated `.env.example` documents
every variable, and `env/fragments/*.example.md` shows the expected shape of the
multi-line ones. Then:

```bash
./bin/prompt build && ./bin/prompt install
```

Restart your session and the skills appear as `/pl:<id>`.

`smoke-test` needs no configuration at all — build and install it first to confirm
the toolchain works end to end before filling anything in. Prompts that need values
you haven't supplied are **skipped with the reason**, not treated as failures, so a
partial setup still gives you a working subset.

## Surfaces — where each artifact has to end up

This is the table to read before wiring anything to a schedule. `surfaces:` in a
prompt's frontmatter says what gets **built**; `distribute:` says where it must be
**installed** to be reachable. They are different axes, and conflating them cost a
silently-wrong scheduled run.

| Surface | Built to | Reachable from | Installed by |
|---|---|---|---|
| `skill` | `build/plugin/skills/<id>/` | Claude Code, interactively, as `/pl:<id>` | `prompt install` |
| `skill` (same file) | — | **a scheduled task** | **you, by saving it to the account catalog** |
| `instructions` | `build/instructions/<id>.md` | a Project's or a scheduled task's Instructions box | you, by pasting |
| `knowledge` | `build/knowledge/<id>.md` | Project knowledge | you, by uploading |
| `cli` | stdout / clipboard | anywhere | `prompt fill` |

**`~/.claude/skills/` is interactive only.** A scheduled task resolves skills from
your account catalog and cannot see it. This is not documented anywhere and it is not
guessable: a scheduled task told to run a skill that isn't in that catalog does **not
fail** — it picks the closest name it can see and proceeds. That happened here, and
the run produced a brief from the wrong skill.

So a prompt declaring `distribute: account` is not finished by `install`. The command
says so on every run and names the directory to save — the whole directory, because
the bundled `references/` has to travel with it.

**Bundle a reference doc rather than uploading it.** A skill that names a knowledge
file it doesn't carry is only as reliable as whatever the runtime finds under that
name. A scheduled run here searched Drive, found an older copy of the same spec, and
read that — without complaint. `reference:` in frontmatter renders the doc into the
skill's own `references/` directory, and the generated pointer both names the exact
relative path and forbids searching elsewhere for a similar name. Naming the path is
only half the fix.

## Turning a prompt into a scheduled job

This is the one flow the repo deliberately does **not** automate, so here is the
procedure. A scheduled task is scheduler *configuration* — a cron expression, a
model, a permission mode, approved tool permissions — living in the desktop app's
own registry. This repo cannot write it, cannot read it back, and cannot verify it,
so it does not pretend to.

What the repo does own is the artifact the task runs. The task's own instructions
are one line.

1. **Build and save the skill to your account.** `prompt install` puts it in
   `~/.claude/skills/pl/`, which a scheduled task cannot see. Save the whole
   directory it names — `build/plugin/skills/<id>/` — including `references/`.
2. **Create the scheduled task** with its instructions set to little more than:
   `Run the` \`<id>\` `skill, following its instructions exactly.` Add any
   unattended-run notes there rather than in the prompt, since the same skill is
   also used interactively where someone *is* at the keyboard.
3. **Run it manually once** and read the progress panel, specifically confirming it
   loaded *your* skill.

**The warning that is not guessable, and the reason step 3 exists:** a scheduled
task told to run a skill that is not in the account catalog **does not fail.** It
picks the closest name it can see and proceeds. That happened here — a run grabbed a
different skill with a similar name and produced output from the wrong one. Nothing
errored. So "the task ran and produced a brief" is not evidence it ran *your* prompt.

After any prompt change: `build`, `install`, and **re-save to the account**. A local
install alone leaves the scheduled copy stale, and a stale copy still runs.

### Non-goals

Deliberately absent, so they don't get re-added:

- **No `scheduled:` frontmatter.** It existed briefly and was wrong — it wrote files
  the app generates rather than reads.
- **Nothing writes the scheduler registry.** Cron expressions, permission modes and
  tool grants stay where the app owns them. Putting them in frontmatter would create
  a second source of truth that silently drifts from the real task.
- **No automated reachability check.** The only local view of the account catalog is
  a mirror that lags by hours; a check against it would report correctly-published
  skills as missing. `distribute: account` drives a reminder, not an assertion — a
  gate that cannot verify should not exist.

## The five commands that matter

```bash
./bin/prompt list                      # what exists, and what is installed
./bin/prompt check                     # validate + smoke-render + scan
./bin/prompt build <id>                # compile to build/
./bin/prompt install <id>              # install the plugin locally
./bin/prompt fill <id> "<arg>"         # render one and copy it to the clipboard
```

`./bin/prompt help` lists the rest. Run `./bin/prompt doctor --fix` once after
cloning.

> Always `./bin/prompt`, never `python3 bin/prompt`. My shell aliases `python3`
> to a `python3.11` that isn't installed, so the latter fails confusingly. A
> shebang ignores shell aliases.

## Layout

| Path | What | In git? |
|---|---|---|
| `prompts/`, `references/` | canonical files — **the only thing you edit** | yes |
| `env/*.env.example` | generated variable documentation | yes |
| `env/fragments/` | public example fragments showing expected shapes | yes |
| `scan/allow.txt` | path-scoped scanner overrides, with reasons | yes |
| `private/` | real values, private fragments, the customer denylist | **no** |
| `inbox/` | raw imports and staging scratch | **no** |
| `build/` | compiled output | **no** |

`build/` is gitignored unconditionally. Rendered output contains private
overlay values by design, so gitignoring it makes "committed files never
contain overlay content" a property of the layout rather than a flag that can
be misconfigured.

## One writer

Nothing in this toolchain writes to `prompts/` or `references/`. `ingest`
writes to `inbox/staged/` and stops; `build` writes to `build/`; `install`
writes to `~/.claude/`. So re-importing from an upstream source can never
clobber a local edit, and `promote` refuses to overwrite an existing canonical
file. Once a prompt is here, this repo is the source of truth and the original
is an archive.

## Variables

The variable **contract** lives in the canonical file's frontmatter; `.env`
holds only **values**. That split is what makes drift detectable — `check`
set-compares `{{VAR}}` tokens in the body against `vars:` declarations and
errors in both directions, so a renamed variable fails the build instead of
silently rendering as literal text. `env/*.env.example` is generated; never
hand-edit it.

Syntax is `{{NAME}}`, uppercase only. `{{{{` escapes to a literal `{{`.
`$ARGUMENTS` and `$1` are reserved — the compiler emits those; declare a var
with `from-arg:` instead.

### Optional sections

A variable declared without `required: true` resolves to empty when nothing
supplies it. Wrap a whole section in a guard and it disappears cleanly —
heading and all — rather than leaving an empty stub:

```markdown
{{#IF_PRICING_REFERENCE}}
## 13. Pricing and commercial reference

{{PRICING_REFERENCE}}
{{/IF_PRICING_REFERENCE}}
```

Both tags must sit alone on their own lines. There is no `else`, no
expressions, and no nesting — one construct, deliberately. Put an optional
section **last** so the section numbering stays contiguous whether or not it
renders.

`check` verifies every guard is balanced, that it names a declared variable,
and warns if it guards a `required: true` variable (that block could never be
dropped).

### Adding a price book, or any other company-specific reference

`customer-account-intelligence` ships with an optional `PRICING_REFERENCE`
variable as the worked example of this pattern. It is unset by default, so the
prompt carries no commercial data at all until you opt in.

To add one:

1. Write your real figures to `private/fragments/pricing-reference.md` —
   gitignored, never committed.
2. Uncomment the pointer in `private/env/customer-account-intelligence.env`:
   `PRICING_REFERENCE=@../fragments/pricing-reference.md`
3. `./bin/prompt build customer-account-intelligence --var CUSTOMER_NAME="..."`

`env/fragments/pricing-reference.example.md` is the committed template showing
the expected shape: list pricing and units, packaging and commit tiers,
professional-services thresholds, discount authority, marketplace and partner
economics, and an explicit instruction on what to do when a figure is missing.
Every placeholder in it is written `<like-this>` with **no digits and no
currency symbols**, specifically so the money patterns stay armed on that
path — if a real figure ever lands there by accident, the commit is blocked
rather than suppressed by an allow rule.

Keep such a section short and current. A wrong number is worse than no number,
which is why the section text tells the assistant to name the figure it needs
rather than interpolate or recall one.

The same pattern works for anything else that is company-specific and
sensitive: a competitive battlecard, a partner matrix, a support-escalation
ladder, or an internal naming decoder. Declare an optional `private: true`
variable, guard a section with it, and commit an example fragment showing the
shape.

A variable marked `private: true` never has its value written into a committed
file. Its real value lives in `private/`, and a committed
`env/fragments/*.example.md` shows the expected shape so the template is
usable by someone who doesn't have my overlay.

## The gate

A pre-commit hook scans staged blob content; a pre-push hook scans every commit
being pushed, so `--no-verify` doesn't get anything out. Two layers: regex
families in `lib/patterns.py` (committed, contains no customer names) and a
hand-curated denylist in `private/denylist.txt` (gitignored, because a list of
customers is itself confidential). `scan/allow.txt` can suppress a pattern
family for a given path with a stated reason; it deliberately **cannot**
suppress a denylist hit, since naming the term in a committed file would
publish the thing the denylist exists to hide.

## No dependencies, on purpose

Stdlib only, targeting Python 3.9 — `/usr/bin/python3` is 3.9.6 and has
neither PyYAML nor `tomllib`. That constraint is why `lib/frontmatter.py`
vendors a small restricted-YAML reader. Please don't "simplify" it by adding a
dependency: the point is that `./bin/prompt` runs on a fresh clone with no
setup step.
