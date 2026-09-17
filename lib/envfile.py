"""Variable VALUE resolution. The variable CONTRACT lives in frontmatter.

That split is deliberate and it is the one place this design disagrees with
the original brief. .env is the right home for values and the wrong home for
the schema: with a hand-authored .env.example, adding {{REGION}} to a body
and forgetting the .env.example entry is invisible until someone clones the
repo and gets a literal "{{REGION}}" in their output. With frontmatter as the
contract, `check` set-compares body tokens against declarations and errors
both ways. env/*.env.example is GENERATED from frontmatter, never hand-edited.

.env syntax:
    KEY=plain value                    # trailing comments are NOT stripped
    KEY=@relative/path.md              # value is that file's contents
    KEY<<'END'                         # heredoc for short multi-line values
    line one
    END

@-paths resolve relative to the .env file's own directory, so
private/env/x.env can say @../fragments/map.md.

Resolution order, later wins:
    1. frontmatter `default:`
    2. private/env/_shared.env
    3. private/env/<id>.env
    4. explicit --var K=V on the command line

Targets Python 3.9. Stdlib only.
"""

import os
from typing import Dict, List, NamedTuple, Optional, Tuple


class EnvError(ValueError):
    pass


class Resolved(NamedTuple):
    values: Dict[str, str]
    origin: Dict[str, str]     # var name -> where its value came from
    missing: List[str]         # required vars with no value anywhere


def parse_env(path: str) -> Dict[str, str]:
    """Parse one .env file, resolving @file references."""
    base = os.path.dirname(os.path.abspath(path))
    out: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        if not line or line.startswith("#"):
            continue

        # heredoc:  KEY<<'END'
        if "<<" in line and "=" not in line.split("<<", 1)[0]:
            key, rest = line.split("<<", 1)
            key = key.strip()
            delim = rest.strip().strip("'\"")
            if not delim:
                raise EnvError("%s: heredoc for %r has no delimiter" % (path, key))
            body = []
            while i < len(lines) and lines[i].strip() != delim:
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                raise EnvError("%s: heredoc for %r is never closed by %r"
                               % (path, key, delim))
            i += 1
            out[key] = "\n".join(body)
            continue

        if "=" not in line:
            raise EnvError("%s: expected KEY=value or KEY<<'END', got %r"
                           % (path, line))
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("@"):
            ref = os.path.normpath(os.path.join(base, value[1:]))
            if not os.path.exists(ref):
                raise EnvError("%s: %s=@%s -- file not found at %s"
                               % (path, key, value[1:], ref))
            with open(ref, "r", encoding="utf-8") as fh:
                value = fh.read()
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        out[key] = value
    return out


def declared_vars(meta: dict) -> List[dict]:
    """Normalise the `vars:` block into a list of dicts."""
    raw = meta.get("vars") or []
    if isinstance(raw, dict):
        raw = [raw]
    out = []
    for v in raw:
        if not isinstance(v, dict) or not v.get("name"):
            raise EnvError("each entry under `vars:` needs a `name:` (got %r)" % (v,))
        out.append(v)
    return out


def resolve(root: str, prompt_id: str, meta: dict,
            overrides: Optional[Dict[str, str]] = None,
            use_examples: bool = False,
            override_origins: Optional[Dict[str, str]] = None) -> Resolved:
    """Resolve every declared variable. `use_examples` substitutes `example:`
    values instead of real ones -- that is what makes `check` able to smoke-test
    a render on a fresh clone with no private/ directory present."""
    values: Dict[str, str] = {}
    origin: Dict[str, str] = {}
    decls = declared_vars(meta)

    for v in decls:
        if use_examples:
            if v.get("example") is not None:
                values[v["name"]] = str(v["example"])
                origin[v["name"]] = "frontmatter example:"
            elif v.get("example-file"):
                p = os.path.join(root, str(v["example-file"]))
                if os.path.exists(p):
                    with open(p, "r", encoding="utf-8") as fh:
                        values[v["name"]] = fh.read()
                    origin[v["name"]] = v["example-file"]
        if v.get("default") is not None and v["name"] not in values:
            values[v["name"]] = str(v["default"])
            origin[v["name"]] = "frontmatter default:"

    if not use_examples:
        for rel in (os.path.join("private", "env", "_shared.env"),
                    os.path.join("private", "env", prompt_id + ".env")):
            path = os.path.join(root, rel)
            if os.path.exists(path):
                for k, val in parse_env(path).items():
                    values[k] = val
                    origin[k] = rel

    for k, val in (overrides or {}).items():
        values[k] = val
        origin[k] = (override_origins or {}).get(k, "--var")

    missing = [v["name"] for v in decls
               if v.get("required") and not str(values.get(v["name"], "")).strip()]
    return Resolved(values, origin, missing)


def generate_example(prompt_id: str, meta: dict) -> str:
    """Generate env/<id>.env.example FROM frontmatter. Never hand-edit it."""
    lines = [
        "# GENERATED by ./bin/prompt build -- do not edit.",
        "# Edit the `vars:` block in prompts/%s.md instead." % prompt_id,
        "#",
        "# Copy to private/env/%s.env (./bin/prompt init does this) and fill in." % prompt_id,
        "",
    ]
    for v in declared_vars(meta):
        name = v["name"]
        for chunk in str(v.get("describe", "")).split("\n"):
            if chunk.strip():
                lines.append("# %s" % chunk.strip())
        flags = []
        if v.get("required"):
            flags.append("REQUIRED")
        if v.get("private"):
            flags.append("private -- real value is NOT in this repo")
        if v.get("multiline"):
            flags.append("multiline -- use KEY=@path/to/file.md")
        if v.get("from-arg"):
            flags.append("supplied at invocation as $%s in the skill surface"
                         % v["from-arg"])
        if flags:
            lines.append("#   [%s]" % "; ".join(flags))

        if v.get("private"):
            # Never write a private var's resolved value into a committed
            # file. Point at the public example fragment instead.
            if v.get("example-file"):
                lines.append("# %s=@%s   <- shape shown here; substitute your own"
                             % (name, os.path.relpath(
                                 str(v["example-file"]), "private/env")))
            lines.append("%s=" % name)
        elif v.get("example") is not None:
            lines.append("%s=%s" % (name, v["example"]))
        elif v.get("default") is not None:
            lines.append("# default: %s" % v["default"])
            lines.append("%s=" % name)
        else:
            lines.append("%s=" % name)
        lines.append("")
    return "\n".join(lines)
