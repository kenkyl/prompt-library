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

# The ONE conditional construct. No else, no expressions, no nesting.
# Deferred until a prompt genuinely needed it: an optional section has to
# disappear cleanly when unset rather than leave a dangling heading behind.
# Anything more than this starts becoming a templating language -- don't.
#
# Leading whitespace and the newline after each tag are consumed so a dropped
# block leaves no blank gap and a kept block does not gain one.
# Block style ONLY: each tag must sit alone on its own line. An inline
# conditional would have to guess whether to keep the line's newline, and
# guessing wrong silently mangles the output. A section guard never needs it.
COND_RX = re.compile(
    r"(?:\A|(?<=\n))[ \t]*\{\{#IF_(" + NAME + r")\}\}[ \t]*\n"
    r"(.*?)"
    r"[ \t]*\{\{/IF_\1\}\}[ \t]*(?:\n|\Z)",
    re.DOTALL)

# Marks a removed block so the blank line it leaves behind can be collapsed
# without touching unrelated blank runs (which may be inside a code fence).
_DROPPED = "\x00PL_DROPPED\x00"

# Used to spot an opener with no matching closer.
COND_OPEN_RX = re.compile(r"\{\{#IF_(" + NAME + r")\}\}")
COND_CLOSE_RX = re.compile(r"\{\{/IF_(" + NAME + r")\}\}")

_ESCAPE_SENTINEL = "\x00PL_OPEN\x00"


class Hit(NamedTuple):
    text: str
    line: int


def _lineno(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def tokens(body: str) -> List[str]:
    """Distinct variable names referenced by the body, in first-seen order.

    Includes names referenced only by a {{#IF_X}} guard -- those are a real
    use, and treating them otherwise would make `check` report a declared
    variable as unused.
    """
    src = body.replace("{{{{", _ESCAPE_SENTINEL)
    seen, out = set(), []
    for m in re.finditer(r"\{\{(?:#IF_|/IF_)?(" + NAME + r")\}\}", src):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def conditionals(body: str) -> List[str]:
    """Distinct variable names used as {{#IF_X}} guards."""
    src = body.replace("{{{{", _ESCAPE_SENTINEL)
    return sorted(set(m.group(1) for m in COND_OPEN_RX.finditer(src)))


def unbalanced_conditionals(body: str) -> List[Hit]:
    """Openers without a matching closer, and vice versa."""
    src = body.replace("{{{{", _ESCAPE_SENTINEL)
    opens = [(m.group(1), _lineno(src, m.start())) for m in COND_OPEN_RX.finditer(src)]
    closes = [(m.group(1), _lineno(src, m.start())) for m in COND_CLOSE_RX.finditer(src)]
    out = []
    close_names = [n for n, _ in closes]
    open_names = [n for n, _ in opens]
    for name, line in opens:
        if close_names.count(name) != open_names.count(name):
            out.append(Hit("{{#IF_%s}} has no matching {{/IF_%s}}" % (name, name), line))
    for name, line in closes:
        if name not in open_names:
            out.append(Hit("{{/IF_%s}} has no matching {{#IF_%s}}" % (name, name), line))
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
        tag = m.group(0)
        if TOKEN_RX.fullmatch(tag) or COND_OPEN_RX.fullmatch(tag) \
                or COND_CLOSE_RX.fullmatch(tag):
            continue
        out.append(Hit(tag, _lineno(src, m.start())))
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

    # Conditionals first: a block whose guard is empty is removed entirely,
    # so any {{VAR}} inside it is not reported as unresolved.
    def _cond(m):
        guard = str(values.get(m.group(1), "")).strip()
        return m.group(2) if guard else _DROPPED

    prev = None
    while prev != src:
        prev = src
        src = COND_RX.sub(_cond, src)
    src = re.sub(r"[ \t]*" + _DROPPED + r"\n?", "", src)

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
