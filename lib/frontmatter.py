"""A deliberately restricted YAML reader/writer for canonical prompt files.

Why not PyYAML: no interpreter on this machine has it (/usr/bin/python3 is
3.9.6; homebrew 3.14 and asdf 3.13 are equally bare), and adding a dependency
means a venv, which means `./bin/prompt` stops being runnable on a fresh
clone. Why not TOML: tomllib is 3.11+, and canonical files would then look
nothing like the YAML frontmatter they compile into.

So: a small subset, parsed strictly, with line numbers in every error. The
subset is chosen to be small enough to parse CORRECTLY rather than to be
generally useful. `check` validates against it, so a malformed file fails
loudly instead of being silently mis-parsed.

Supported:
    key: scalar
    key: a folded scalar that continues
      on more-indented lines
    key: [inline, flow, list]
    key: {inline: map, of: scalars}
    key:
      - block list item
      - name: mapping in a list
        field: second key of that mapping
    key: |
      literal block
      preserving newlines

NOT supported (and rejected with an error): anchors, aliases, tags, multiple
documents, '>' folded blocks, nested flow collections, comments after a
value on a block-scalar line.

Targets Python 3.9. Stdlib only.
"""

from typing import Any, Dict, List, Optional, Tuple

DELIM = "---"


class FrontmatterError(ValueError):
    """Raised with a line number the user can act on."""


class _Line:
    __slots__ = ("indent", "text", "no")

    def __init__(self, indent: int, text: str, no: int):
        self.indent = indent
        self.text = text
        self.no = no


# --------------------------------------------------------------------------
# scalars
# --------------------------------------------------------------------------

def _scalar(raw: str, lineno: int) -> Any:
    s = raw.strip()
    if not s:
        return ""
    if s[0] in "&*!":
        raise FrontmatterError(
            "line %d: anchors, aliases and tags are not supported (%r)" % (lineno, s))
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        inner = s[1:-1]
        return inner.replace('\\"', '"') if s[0] == '"' else inner
    # strip a trailing comment only when it is clearly separated
    if " #" in s:
        s = s.split(" #", 1)[0].strip()
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", "none"):
        return None
    if s.lstrip("-").isdigit():
        try:
            return int(s)
        except ValueError:
            pass
    return s


def _split_flow(body: str, lineno: int) -> List[str]:
    """Split a flow collection body on commas. Rejects nesting."""
    for ch in "[]{}":
        if ch in body:
            raise FrontmatterError(
                "line %d: nested flow collections are not supported" % lineno)
    parts, cur, quote = [], "", ""
    for ch in body:
        if quote:
            cur += ch
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
            cur += ch
        elif ch == ",":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return [p for p in parts if p.strip()]


def _flow(s: str, lineno: int) -> Any:
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(p, lineno) for p in _split_flow(s[1:-1], lineno)]
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for part in _split_flow(s[1:-1], lineno):
            if ":" not in part:
                raise FrontmatterError(
                    "line %d: flow map entry %r has no colon" % (lineno, part.strip()))
            k, v = part.split(":", 1)
            out[k.strip()] = _scalar(v, lineno)
        return out
    return None


# --------------------------------------------------------------------------
# block structure
# --------------------------------------------------------------------------

def _parse_block(lines: List[_Line], i: int, indent: int) -> Tuple[Any, int]:
    if i >= len(lines):
        return None, i
    if lines[i].text.startswith("- ") or lines[i].text == "-":
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_list(lines: List[_Line], i: int, indent: int) -> Tuple[List[Any], int]:
    out: List[Any] = []
    while i < len(lines) and lines[i].indent == indent and \
            (lines[i].text.startswith("- ") or lines[i].text == "-"):
        head = lines[i].text[2:] if lines[i].text.startswith("- ") else ""
        child_indent = indent + 2
        # Gather this item's continuation lines.
        sub: List[_Line] = []
        if head.strip():
            sub.append(_Line(child_indent, head.strip(), lines[i].no))
        j = i + 1
        while j < len(lines) and lines[j].indent >= child_indent:
            sub.append(lines[j])
            j += 1
        if not sub:
            out.append(None)
        elif len(sub) == 1 and ":" not in _strip_quoted(sub[0].text):
            out.append(_scalar(sub[0].text, sub[0].no))
        else:
            value, _ = _parse_block(sub, 0, child_indent)
            out.append(value)
        i = j
    return out, i


def _strip_quoted(s: str) -> str:
    """Blank out quoted runs so a colon inside a quoted string is ignored."""
    out, quote = [], ""
    for ch in s:
        if quote:
            out.append(" ")
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _parse_map(lines: List[_Line], i: int, indent: int) -> Tuple[Dict[str, Any], int]:
    out: Dict[str, Any] = {}
    while i < len(lines) and lines[i].indent == indent:
        ln = lines[i]
        if ln.text.startswith("- "):
            raise FrontmatterError(
                "line %d: unexpected list item inside a mapping" % ln.no)
        stripped = _strip_quoted(ln.text)
        if ":" not in stripped:
            raise FrontmatterError(
                "line %d: expected 'key: value', got %r" % (ln.no, ln.text))
        cut = stripped.index(":")
        key = ln.text[:cut].strip()
        rest = ln.text[cut + 1:].strip()
        if not key:
            raise FrontmatterError("line %d: empty key" % ln.no)
        if key in out:
            raise FrontmatterError("line %d: duplicate key %r" % (ln.no, key))

        if rest in ("|", "|-", "|+"):
            block, i = _literal_block(lines, i + 1, indent)
            out[key] = block if rest != "|-" else block.rstrip("\n")
            continue
        if rest == ">" or rest.startswith(">"):
            raise FrontmatterError(
                "line %d: '>' folded blocks are not supported; use '|' or a "
                "plain folded scalar" % ln.no)

        if rest:
            flow = _flow(rest, ln.no)
            if flow is not None:
                out[key] = flow
                i += 1
                continue
            # Plain scalar, possibly folded across more-indented lines. A
            # nested block would require `rest` to be empty, so this is
            # unambiguous.
            parts = [rest]
            j = i + 1
            while j < len(lines) and lines[j].indent > indent:
                parts.append(lines[j].text.strip())
                j += 1
            out[key] = _scalar(" ".join(parts), ln.no) if len(parts) == 1 \
                else " ".join(parts)
            i = j
            continue

        # rest empty -> nested block, or an empty value
        j = i + 1
        if j < len(lines) and lines[j].indent > indent:
            out[key], i = _parse_block(lines, j, lines[j].indent)
        else:
            out[key] = None
            i = j
    return out, i


def _literal_block(lines: List[_Line], i: int, indent: int) -> Tuple[str, int]:
    body: List[str] = []
    base: Optional[int] = None
    while i < len(lines) and lines[i].indent > indent:
        if base is None:
            base = lines[i].indent
        body.append(" " * (lines[i].indent - base) + lines[i].text)
        i += 1
    return "\n".join(body) + ("\n" if body else ""), i


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def split(text: str) -> Tuple[str, str, int]:
    """Return (frontmatter_src, body, body_first_lineno). Raises if absent."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != DELIM:
        raise FrontmatterError(
            "line 1: file must start with '---' and a YAML frontmatter block")
    for n in range(1, len(lines)):
        if lines[n].strip() == DELIM:
            return "\n".join(lines[1:n]), "\n".join(lines[n + 1:]), n + 2
    raise FrontmatterError("frontmatter block is never closed with '---'")


def parse(text: str) -> Tuple[Dict[str, Any], str, int]:
    """Parse a canonical file into (metadata, body, body_first_lineno)."""
    src, body, body_line = split(text)
    lines: List[_Line] = []
    for offset, raw in enumerate(src.split("\n")):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            raise FrontmatterError(
                "line %d: tab in indentation; use spaces" % (offset + 2))
        lines.append(_Line(len(raw) - len(raw.lstrip()), raw.strip(), offset + 2))
    if not lines:
        return {}, body, body_line
    meta, consumed = _parse_map(lines, 0, lines[0].indent)
    if consumed != len(lines):
        raise FrontmatterError(
            "line %d: unexpected indentation" % lines[consumed].no)
    return meta, body, body_line


# --------------------------------------------------------------------------
# emitting (for generated SKILL.md frontmatter)
# --------------------------------------------------------------------------

_NEEDS_QUOTE = set(":#{}[]&*!|>'\"%@`,")


def _emit_scalar(v: Any) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return ""
    if isinstance(v, int):
        return str(v)
    s = str(v)
    if not s:
        return '""'
    if s != s.strip() or s[0] in _NEEDS_QUOTE or ": " in s or " #" in s \
            or s.lower() in ("true", "false", "yes", "no", "null", "~") \
            or s.lstrip("-").isdigit():
        return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
    return s


def emit(meta: Dict[str, Any]) -> str:
    """Emit a flat mapping as YAML frontmatter, including the --- delimiters.

    Only the shapes a generated SKILL.md needs: scalars and flat lists.
    """
    out = [DELIM]
    for k, v in meta.items():
        if v is None or v == [] or v == "":
            continue
        if isinstance(v, (list, tuple)):
            if any(isinstance(x, (list, tuple, dict)) for x in v):
                raise FrontmatterError("emit: nested collections unsupported (%r)" % k)
            out.append("%s: [%s]" % (k, ", ".join(_emit_scalar(x) for x in v)))
        elif isinstance(v, dict):
            raise FrontmatterError("emit: nested mappings unsupported (%r)" % k)
        elif isinstance(v, str) and "\n" in v:
            out.append("%s: |" % k)
            out.extend("  " + line for line in v.rstrip("\n").split("\n"))
        else:
            out.append("%s: %s" % (k, _emit_scalar(v)))
    out.append(DELIM)
    return "\n".join(out) + "\n"
