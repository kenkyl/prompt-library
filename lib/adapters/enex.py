"""Evernote .enex export -> markdown.

An .enex file is an XML envelope of <note> elements. Each note's <content> is
itself a second XML document (ENML, an XHTML subset) wrapped in CDATA, so there
are two parses: ElementTree for the envelope, HTMLParser for the body. The body
goes through HTMLParser rather than ElementTree because ENML written by older
clients is not reliably well-formed, and a note that fails to parse strictly is
better converted loosely than dropped.

The conversion is tuned for how Evernote actually lays text out, not for HTML
in general: every line is its own <div>, and a blank line is <div><br/></div>.
Treating <div> as a paragraph, the HTML-generic reading, double-spaces every
note and destroys the numbered-list and heading structure prompts depend on.

Attachments (<en-media>) and encrypted sections (<en-crypt>) are not carried
over. Each leaves a visible marker in the output instead, so a note that relied
on one cannot be promoted without someone noticing the gap.

Targets Python 3.9. Stdlib only.
"""

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Dict, List, NamedTuple, Optional


class Note(NamedTuple):
    title: str
    created: str       # YYYY-MM-DD, or "" if the export omits it
    updated: str
    tags: List[str]
    body: str          # markdown
    omitted: List[str]  # human-readable notes on what was not carried over


class EnexError(ValueError):
    pass


def _date(raw: Optional[str]) -> str:
    # Evernote writes 20230314T091500Z. Only the date is worth keeping: it is
    # provenance for a human, and a time-of-day adds nothing but noise.
    m = re.match(r"(\d{4})(\d{2})(\d{2})T", (raw or "").strip())
    return "%s-%s-%s" % m.groups() if m else ""


def parse(path: str) -> List[Note]:
    try:
        # Evernote exports carry a DOCTYPE naming a remote DTD. ElementTree
        # never fetches external entities, so this reads offline and cannot be
        # made to reach the network by a crafted export.
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise EnexError("%s: not a readable .enex export (%s)" % (path, exc))
    root = tree.getroot()
    if root.tag != "en-export":
        raise EnexError("%s: root element is <%s>, expected <en-export>"
                        % (path, root.tag))
    notes = []
    for el in root.findall("note"):
        conv = _ENML()
        conv.feed(el.findtext("content") or "")
        conv.close()
        notes.append(Note(
            title=(el.findtext("title") or "").strip() or "untitled",
            created=_date(el.findtext("created")),
            updated=_date(el.findtext("updated")),
            tags=[t.text.strip() for t in el.findall("tag")
                  if t.text and t.text.strip()],
            body=conv.markdown(),
            omitted=conv.omitted))
    return notes


# --------------------------------------------------------------------------
# ENML -> markdown
# --------------------------------------------------------------------------

_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
# Elements that start and end a line of their own. <p> and headings also get a
# blank line around them; <div> does not -- see the module docstring.
_BLOCK = {"div", "p", "blockquote", "pre", "table", "tr", "ul", "ol", "li",
          "hr", "en-note"} | set(_HEADINGS)


def _style(attrs: Dict[str, str]) -> str:
    return (attrs.get("style") or "").replace(" ", "")


def _is_codeblock(attrs: Dict[str, str]) -> bool:
    # Evernote's code block is a styled div, not <pre>. Older clients write
    # -en-codeblock, current ones --en-codeblock; this matches both.
    return "-en-codeblock:true" in _style(attrs)


class _ENML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: List[str] = []
        self.omitted: List[str] = []
        self.lists: List[List] = []      # stack of [kind, counter]
        self.pre = 0                     # depth inside <pre> or a code block
        self.div_kinds: List[bool] = []  # per open <div>: is it a code block?
        self.quote = 0
        self.href: List[Optional[str]] = []
        self.cells: Optional[List[str]] = None
        self.rows_done = 0
        self.skip = 0                    # inside <en-crypt>, whose text is ciphertext
        # True between a list marker and the item's first text. Current
        # Evernote wraps every item's text in a <div>, and without this the
        # div's line break lands between "- " and the text it belongs to.
        self.item_open = False

    # -- output helpers ----------------------------------------------------

    def _text(self) -> str:
        return "".join(self.out)

    def _at_line_start(self) -> bool:
        t = self._text()
        return not t or t.endswith("\n")

    def _newline(self):
        if not self._at_line_start():
            self.out.append("\n")

    def _blank_line(self):
        self._newline()
        if not self._text().endswith("\n\n") and self._text():
            self.out.append("\n")

    def _emit(self, s: str):
        if self.cells is not None:
            self.cells[-1] += s
            return
        if self._at_line_start() and not self.pre:
            prefix = "> " * self.quote
            s = prefix + s
        self.out.append(s)

    # -- parser callbacks --------------------------------------------------

    def handle_starttag(self, tag, attrs_list):
        attrs = dict(attrs_list)
        if self.skip:
            return
        if tag == "en-crypt":
            self.skip += 1
            self.omitted.append("an encrypted section")
            self._emit("<!-- ingest: encrypted section omitted -->")
            return
        if tag == "en-media":
            kind = attrs.get("type") or "unknown type"
            self.omitted.append("an attachment (%s)" % kind)
            self._emit("<!-- ingest: attachment omitted (%s) -->" % kind)
            return
        if tag == "en-todo":
            self._emit("[x] " if attrs.get("checked") == "true" else "[ ] ")
            return
        if tag == "br":
            if self.cells is not None:
                self.cells[-1] += " "
            else:
                self.out.append("\n")
            return
        if tag == "hr":
            self._blank_line()
            self.out.append("---\n\n")
            return
        if tag == "div":
            code = _is_codeblock(attrs)
            self.div_kinds.append(code)
            if code:
                self._blank_line()
                self.out.append("```\n")
                self.pre += 1
            elif self.cells is None and not self.item_open:
                self._newline()
            return
        if tag == "pre":
            self._blank_line()
            self.out.append("```\n")
            self.pre += 1
            return
        if tag in _HEADINGS:
            self._blank_line()
            self._emit("#" * _HEADINGS[tag] + " ")
            return
        if tag == "p":
            self._blank_line()
            return
        if tag == "blockquote":
            self._blank_line()
            self.quote += 1
            return
        if tag in ("ul", "ol"):
            if not self.lists:
                self._blank_line()
            # Current Evernote writes a checklist as a styled <ul>, not as
            # <en-todo> elements, so the checkbox state lives on each <li>.
            todo = "--en-todo:true" in _style(attrs)
            self.lists.append(["todo" if todo else tag, 0, 2])
            return
        if tag == "li":
            self._newline()
            # A nested item must be indented to its parent's CONTENT column,
            # which is 3 under "1. " but 2 under "- ". A fixed two spaces
            # un-nests every sublist of a numbered list.
            indent = " " * sum(lv[2] for lv in self.lists[:-1])
            kind = self.lists[-1][0] if self.lists else "ul"
            if kind == "ol":
                self.lists[-1][1] += 1
                marker = "%d. " % self.lists[-1][1]
            else:
                marker = "- "
            if self.lists:
                self.lists[-1][2] = len(marker)
            if kind == "todo":
                marker += ("[x] " if "--en-checked:true" in _style(attrs)
                           else "[ ] ")
            self._emit(indent + marker)
            self.item_open = True
            return
        if tag == "table":
            self._blank_line()
            self.rows_done = 0
            return
        if tag == "tr":
            self.cells = []
            return
        if tag in ("td", "th") and self.cells is not None:
            self.cells.append("")
            return
        if tag in ("b", "strong"):
            self._emit("**")
            return
        if tag in ("i", "em"):
            self._emit("*")
            return
        if tag == "code" and not self.pre:
            self._emit("`")
            return
        if tag == "a":
            self.href.append(attrs.get("href"))
            if attrs.get("href"):
                self._emit("[")
            return

    def handle_startendtag(self, tag, attrs):
        # <br/>, <en-media/>, <en-todo/>, <hr/> -- none of which have a body.
        self.handle_starttag(tag, attrs)
        if tag == "div":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "en-crypt":
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "div":
            code = self.div_kinds.pop() if self.div_kinds else False
            if code:
                self._newline()
                self.out.append("```\n\n")
                self.pre -= 1
            elif self.cells is None:
                self._newline()
            return
        if tag == "pre":
            self._newline()
            self.out.append("```\n\n")
            self.pre -= 1
            return
        if tag in _HEADINGS or tag == "p":
            self._blank_line()
            return
        if tag == "blockquote":
            self.quote = max(0, self.quote - 1)
            self._blank_line()
            return
        if tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            if not self.lists:
                self._blank_line()
            return
        if tag == "li":
            self._newline()
            return
        if tag == "tr" and self.cells is not None:
            cells = [re.sub(r"\s+", " ", c).strip().replace("|", "\\|")
                     for c in self.cells]
            self.cells = None
            if cells:
                self.out.append("| %s |\n" % " | ".join(cells))
                if self.rows_done == 0:
                    self.out.append("|%s\n" % ("---|" * len(cells)))
                self.rows_done += 1
            return
        if tag == "table":
            self._blank_line()
            return
        if tag in ("b", "strong"):
            self._emit("**")
            return
        if tag in ("i", "em"):
            self._emit("*")
            return
        if tag == "code" and not self.pre:
            self._emit("`")
            return
        if tag == "a":
            href = self.href.pop() if self.href else None
            if href:
                self._emit("](%s)" % href)
            return

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre:
            self._emit(data)
            return
        # HTML whitespace rules outside preformatted text: runs collapse, and
        # the newlines between tags in the source mean nothing.
        text = re.sub(r"\s+", " ", data)
        if self.cells is None and self._at_line_start():
            text = text.lstrip()
        if text:
            self._emit(text)
            self.item_open = False

    # -- result ------------------------------------------------------------

    def markdown(self) -> str:
        text = self._text().replace(" ", " ")
        lines = [ln.rstrip() for ln in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
        return text + "\n" if text else ""
