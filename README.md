# prompt-library

One canonical file per prompt, compiled into every surface I actually use:
Claude Code skills (which are also slash commands), claude.ai Project
instructions and knowledge files, and the clipboard.

The problem it solves: the same prompt text was living in two or three places
at once and drifting. Now there is exactly one copy, and the others are built
from it.

## The five commands that matter

```bash
./bin/prompt list                      # what exists, and what is installed
./bin/prompt check                     # validate + smoke-render + scan
./bin/prompt build <id>                # compile to build/
./bin/prompt install <id>              # copy into ~/.claude/skills/
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
