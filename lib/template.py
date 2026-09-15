"""{{VAR}} substitution with a deliberately strict token grammar.

Grammar:  {{NAME}}  where NAME is ^[A-Z][A-Z0-9_]{0,63}$

Why not ${VAR}: prompt bodies legitimately contain shell snippets, and a body
documenting ${CLUSTER_FQDN} as literal text to type would be silently
rewritten. Disqualifying.

Why not $1 / $ARGUMENTS: Claude Code owns those in the skill surface. Using
them as the canonical syntax would write canonical files in one surface's
dialect, and a bare $1 inside a bash snippet would collide. They are
RESERVED, never authored -- the compiler emits them, and `check` rejects a
canonical body that contains one.

The strict grammar neutralises the real collision hazards on its own:
{{ account }}, {{foo}}, {{#each x}} and GitHub Actions' ${{ inputs.name }}
all fail to match and pass through untouched. Because silently passing
through is also the confusing failure mode, near_misses() reports them.

Escape: {{{{ renders as a literal {{.

Targets Python 3.9. Stdlib only.
"""

import re
from typing import Dict, List, NamedTuple, Tuple

NAME = r"[A-Z][A-Z0-9_]{0,63}"
TOKEN_RX = re.compile(r"\{\{(" + NAME + r")\}\}")

# Anything {{...}}-shaped, to find tokens the strict grammar rejects.
SHAPED_RX = re.compile(r"\{\{[^{}\n]{0,120}\}\}")

# A line whose only non-whitespace content is a single token.
BLOCK_LINE_RX = re.compile(r"^([ \t]*)\{\{(" + NAME + r")\}\}[ \t]*$")

# Reserved because the compiler emits them into the skill surface.
RESERVED_RX = re.compile(r"\$ARGUMENTS(?:\[\d+\])?|\$[0-9]\b")

_ESCAPE_SENTINEL = "\x00PL_OPEN\x00"


class Hit(NamedTuple):
    text: str
    line: int


def _lineno(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def tokens(body: str) -> List[str]:
    """Distinct variable names referenced by the body, in first-seen order."""
    seen, out = set(), []
    for m in TOKEN_RX.finditer(body.replace("{{{{", _ESCAPE_SENTINEL)):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def token_hits(body: str) -> List[Hit]:
    src = body.replace("{{{{", _ESCAPE_SENTINEL)
    return [Hit(m.group(1), _lineno(src, m.start())) for m in TOKEN_RX.finditer(src)]


def near_misses(body: str) -> List[Hit]:
    """{{...}}-shaped tokens the strict grammar rejects.

    Reported as info, not errors: {{ inputs.name }} in a GitHub Actions
    example is legitimate. But {{account}} or {{ACCOUNT }} is a typo that
    would otherwise ship as literal text in the rendered output, which is
    an hour of confusion. Surfacing both is cheaper than guessing.
    """
    src = body.replace("{{{{", _ESCAPE_SENTINEL)
    out = []
    for m in SHAPED_RX.finditer(src):
        if not TOKEN_RX.fullmatch(m.group(0)):
            out.append(Hit(m.group(0), _lineno(src, m.start())))
    return out


def reserved(body: str) -> List[Hit]:
    return [Hit(m.group(0), _lineno(body, m.start()))
            for m in RESERVED_RX.finditer(body)]


def _reindent(value: str, indent: str) -> str:
    """Re-indent every line of a multi-line value to `indent`.

    This is the whole reason block substitution exists. Injecting a markdown
    table into an indented context without it produces broken markdown --
    the table renders as a paragraph. Leading and trailing blank lines are
    dropped so the value sits flush where the token was.
    """
    lines = value.replace("\r\n", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    # Strip the value's own common indentation before applying ours.
    common = min((len(l) - len(l.lstrip()) for l in lines if l.strip()),
                 default=0)
    return "\n".join((indent + l[common:]) if l.strip() else "" for l in lines)


def render(body: str, values: Dict[str, str]) -> Tuple[str, List[str]]:
    """Substitute tokens. Returns (text, sorted list of unresolved names).

    Unresolved tokens are left in place verbatim so the caller can decide
    whether that is an error; nothing is ever silently replaced with "".
    """
    src = body.replace("{{{{", _ESCAPE_SENTINEL)
    missing = set()

    out_lines = []
    for line in src.split("\n"):
        m = BLOCK_LINE_RX.match(line)
        if m and m.group(2) in values:
            out_lines.append(_reindent(str(values[m.group(2)]), m.group(1)))
            continue
        if m and m.group(2) not in values:
            missing.add(m.group(2))
            out_lines.append(line)
            continue

        def sub(mt):
            name = mt.group(1)
            if name not in values:
                missing.add(name)
                return mt.group(0)
            v = str(values[name])
            if "\n" in v:
                # An inline token cannot carry a multi-line value without
                # wrecking the surrounding line. Flatten rather than corrupt.
                v = " ".join(x.strip() for x in v.split("\n") if x.strip())
            return v

        out_lines.append(TOKEN_RX.sub(sub, line))

    return "\n".join(out_lines).replace(_ESCAPE_SENTINEL, "{{"), sorted(missing)
