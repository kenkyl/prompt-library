"""Compile one canonical file into each consumption surface.

Surfaces:
  skill        ~/.claude/skills/<id>/SKILL.md -- gives BOTH /<id> and
               model-invocation. Claude Code merged custom commands into
               skills, so these are one artifact, not two. .claude/commands/
               still works but is the legacy format. A `reference:` doc is
               BUNDLED into <id>/references/ so the skill is self-contained.
  instructions build/instructions/<id>.md -- paste into a claude.ai Project's
               "Custom instructions" box. Flat, no frontmatter. No bundling
               channel, so a `reference:` doc stays a Project knowledge file.
  knowledge    build/knowledge/<id>.md -- upload as a Project knowledge file.
  cli          rendered to stdout / pbcopy by `prompt fill`.

Install writes a managed marker so a hand-edit in ~/.claude is detected
rather than silently destroyed. See MARKER_RX.

Targets Python 3.9. Stdlib only.
"""

import hashlib
import json
import re
from typing import Dict, List, Optional, Tuple

from . import frontmatter as FM
from . import template as T

SURFACES = ("skill", "instructions", "knowledge", "cli")

MARKER_PREFIX = "<!-- prompt-library:managed"

# Deliberately carries NO timestamp. A `built=` field made every build differ
# from the last even when content was identical, which cost real debugging
# twice: once as a false "the installed copy does not match the build" scare,
# and once by making every bundled sidecar look changed on every install --
# burying the single sidecar that had actually changed. The content hash is
# the identity that matters; provenance comes from git. Keeping this stable
# makes `diff -r` between two builds a meaningful test.
# `built=` is read-tolerated but never written. Markers installed before the
# timestamp was dropped would otherwise stop matching, which would make every
# already-installed file look foreign and make `install` refuse it -- breaking
# working setups for a cosmetic format change.
MARKER_RX = re.compile(
    r"^<!-- prompt-library:managed id=(?P<id>\S+) surface=(?P<surface>\S+) "
    r"content-sha256=(?P<sha>[0-9a-f]{64})(?: built=(?P<built>\S+))? -->$",
    re.MULTILINE)

# Canonical keys that are ours, not Claude Code's -- never passed through.
_OURS = {"id", "kind", "status", "surfaces", "vars", "source", "reference",
         "title"}


def content_sha(text: str) -> str:
    """Hash of the content with any managed marker line removed.

    Must exclude the marker, or the hash could never match what it records.
    """
    stripped = MARKER_RX.sub("", text).rstrip() + "\n"
    return hashlib.sha256(stripped.encode("utf-8")).hexdigest()


def add_marker(text: str, prompt_id: str, surface: str) -> str:
    body = MARKER_RX.sub("", text).rstrip() + "\n"
    return "%s\n%s id=%s surface=%s content-sha256=%s -->\n" % (
        body, MARKER_PREFIX, prompt_id, surface, content_sha(body))


def read_marker(text: str) -> Optional[re.Match]:
    return MARKER_RX.search(text)


def skill_values(meta: dict, values: Dict[str, str]) -> Dict[str, str]:
    """For the skill surface, `from-arg` vars become $argname placeholders so
    the value arrives at invocation time instead of being frozen at build."""
    out = dict(values)
    for v in (meta.get("vars") or []):
        if isinstance(v, dict) and v.get("from-arg"):
            out[v["name"]] = "$" + str(v["from-arg"])
    return out


BUNDLED_REF_DIR = "references"


def reference_pointer(meta: dict, bundled: bool = False) -> str:
    """The line that sends the model to its reference doc.

    Two forms, because the two delivery routes really are different. The
    `skill` surface ships the doc inside its own directory, so it can name an
    exact relative path -- and it must forbid looking anywhere else. A
    scheduled run of this prompt that could not find its knowledge file did
    not fail: it searched the enterprise connector and Drive, found an older
    copy of the same spec by name, and read that instead. Naming the path is
    only half the fix; closing the fallback is the other half.

    The `instructions` surface has no bundling channel -- it is text pasted
    into a box -- so there the doc stays a Project knowledge file.
    """
    ref = meta.get("reference")
    if not ref:
        return ""
    if bundled:
        return ("Read `%s/%s.md`, which ships inside this skill's own "
                "directory,\nfor all queries, field mappings and rules. Do not "
                "re-derive them.\n\n"
                "That bundled file is the only authoritative copy. If it is "
                "missing,\nsay so and stop. Do not search Drive, the enterprise "
                "search\nconnector, or anywhere else for a file with a similar "
                "name --\nolder copies of this spec exist, and reading one "
                "silently produces\na brief built on stale field mappings.\n\n"
                % (BUNDLED_REF_DIR, ref))
    return ("Reference the project knowledge file `%s` for all queries, field\n"
            "mappings and rules. Do not re-derive them.\n\n" % ref)


def emit_skill(meta: dict, body: str, values: Dict[str, str],
               prompt_id: str) -> Tuple[str, List[str]]:
    fmatter = {"name": prompt_id,
               "description": meta.get("description") or meta.get("title") or ""}
    for key in ("when_to_use", "argument-hint", "arguments", "allowed-tools",
                "disallowed-tools", "model", "effort", "paths",
                "disable-model-invocation", "user-invocable"):
        if meta.get(key) is not None:
            fmatter[key] = meta[key]
    rendered, missing = T.render(
        reference_pointer(meta, bundled=True) + body.lstrip("\n"),
        skill_values(meta, values))
    return FM.emit(fmatter) + "\n" + rendered.lstrip("\n"), missing


def emit_instructions(meta: dict, body: str, values: Dict[str, str],
                      prompt_id: str) -> Tuple[str, List[str]]:
    header = (
        "<!-- %s -- generated by ./bin/prompt build.\n"
        "     Paste into whichever instructions field consumes it: a Project's\n"
        "     custom instructions, or a scheduled task's Instructions.\n"
        "     Do not edit here; edit prompts/%s.md and rebuild. -->\n\n"
        % (meta.get("title") or prompt_id, prompt_id))
    rendered, missing = T.render(reference_pointer(meta) + body, values)
    return header + rendered.lstrip("\n"), missing


def emit_knowledge(meta: dict, body: str, values: Dict[str, str],
                   prompt_id: str) -> Tuple[str, List[str]]:
    title = meta.get("title") or prompt_id
    rendered, missing = T.render(body, values)
    head = rendered.lstrip("\n")
    if not head.startswith("# "):
        head = "# %s\n\n%s" % (title, head)
    return head, missing


PLUGIN_NAME = "pl"


def plugin_manifest(version: str, skill_ids) -> str:
    """The `.claude-plugin/plugin.json` for the built plugin.

    Why a plugin at all: loose skills under ~/.claude/skills/<id>/ are, per the
    Claude Code docs, the "quick experiments" tier. Plugins are the tier for
    "versioned releases, reusable across projects" -- which is what this library
    is. A plugin also namespaces its skills as /<plugin>:<skill>, and the lack
    of a namespace has already cost a real failure: an account-saved skill
    landed in a shared bucket and a scheduled run picked a
    similarly-named neighbour instead, silently.

    Why the plugin is a BUILD OUTPUT rather than a distribution channel: a
    marketplace ships what is committed, and what is committed here is
    deliberately templated, because real values live in the gitignored overlay.
    A plugin repo would ship unresolved placeholders. Built locally from each
    person's own overlay, the same templates produce a working plugin for
    whoever cloned them.

    Kept short on purpose. Only `name` is required; every extra field is one
    more thing to drift.
    """
    payload = {
        "name": PLUGIN_NAME,
        "displayName": "Prompt Library",
        "description": "Prompts built from canonical templates in "
                       "kenkyl/prompt-library.",
        "version": version,
        "repository": "https://github.com/kenkyl/prompt-library",
        "license": "MIT",
        "metadata": {"skills": sorted(skill_ids)},
    }
    # No build timestamp and no git describe. Either would make the manifest
    # depend on something other than the templates, which is exactly what
    # dropping `built=` from the marker was meant to stop: `diff -r` between
    # two builds should mean "the templates differ", nothing else. The commit
    # a build came from is already in `git log`.
    # sort_keys so two builds of the same content are byte-identical.
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


EMITTERS = {"skill": emit_skill,
            "instructions": emit_instructions,
            "knowledge": emit_knowledge}
