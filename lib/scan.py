"""The sanitization gate.

Reports EVERY finding at once, never just the first. A gate that surfaces one
problem per commit attempt trains you to reach for --no-verify, at which point
the gate is decorative.

Two independent detection layers:

  1. Pattern families (lib/patterns.py, committed, no literals).
     Suppressible per-path via scan/allow.txt, by pattern id.

  2. Denylist (private/denylist.txt, gitignored, hand-curated).
     NOT suppressible via allow.txt -- an allow entry naming a customer would
     publish the very term the denylist exists to hide. Resolve a denylist
     false positive by re-tiering it in private/denylist.txt instead.

Targets Python 3.9. Stdlib only.
"""

import fnmatch
import os
import re
import subprocess
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from . import patterns as P

# lib/patterns.py necessarily contains literal fragments its own patterns match
# (credential prefixes, cluster prefixes). Scanning it would always self-fire.
SELF_EXCLUDED = {"lib/patterns.py"}

# Paths that must never be committed, independent of .gitignore -- a `git add -f`
# defeats gitignore, so this guard is enforced separately.
FORBIDDEN_PATH_GLOBS = [
    "private/*", "private/**", "inbox/*", "inbox/**",
    "build/*", "build/**", "*.enex",
]


class Finding(NamedTuple):
    path: str
    line: int
    severity: str          # "block" | "review"
    source: str            # "pattern" | "denylist" | "path"
    rule: str              # pattern id, or denylist tier
    matched: str
    why: str
    fix: str
    suppression: Optional[str] = None   # reason text when allowed


class AllowEntry(NamedTuple):
    path_glob: str
    pattern_id: str
    reason: str
    added: str


class DenyEntry(NamedTuple):
    tier: str              # "strict" | "word" | "review"
    term: str
    note: str


# --------------------------------------------------------------------------
# config loading
# --------------------------------------------------------------------------

def load_allow(root: str) -> List[AllowEntry]:
    """scan/allow.txt -- path-scoped, pattern-id-scoped, reason MANDATORY."""
    path = os.path.join(root, "scan", "allow.txt")
    out: List[AllowEntry] = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [c.strip() for c in line.split("|")]
            if len(parts) != 4 or not all(parts[:3]):
                raise ValueError(
                    "scan/allow.txt:%d malformed. Expected exactly:\n"
                    "  path-glob | pattern-id | reason | YYYY-MM-DD\n"
                    "Got: %s" % (n, line))
            if parts[1] not in P.PATTERNS_BY_ID:
                raise ValueError(
                    "scan/allow.txt:%d unknown pattern id %r. Known ids: %s"
                    % (n, parts[1], ", ".join(sorted(P.PATTERNS_BY_ID))))
            out.append(AllowEntry(*parts))
    return out


def load_denylist(root: str) -> List[DenyEntry]:
    """private/denylist.txt -- gitignored. Absent is fine (Phase 0)."""
    path = os.path.join(root, "private", "denylist.txt")
    out: List[DenyEntry] = []
    if not os.path.exists(path):
        return out
    valid = {"strict", "word", "review"}
    with open(path, "r", encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [c.strip() for c in line.split("|")]
            if len(parts) < 2 or parts[0] not in valid or not parts[1]:
                raise ValueError(
                    "private/denylist.txt:%d malformed. Expected:\n"
                    "  tier | term | optional note      (tier: strict|word|review)\n"
                    "Got: %s" % (n, line))
            out.append(DenyEntry(parts[0], parts[1],
                                 parts[2] if len(parts) > 2 else ""))
    # Multi-word / strict terms first so their spans mask shorter overlaps:
    # a two-word account name must consume its own span, so that a one-word
    # entry for the same company does not fire a second time inside it.
    return sorted(out, key=lambda e: (-len(e.term), e.term))


# --------------------------------------------------------------------------
# scanning
# --------------------------------------------------------------------------

def _is_allowed(path: str, pattern_id: str,
                allow: List[AllowEntry]) -> Optional[AllowEntry]:
    for e in allow:
        if e.pattern_id == pattern_id and fnmatch.fnmatch(path, e.path_glob):
            return e
    return None


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_path(path: str) -> Optional[Finding]:
    norm = path.replace(os.sep, "/")
    for glob in FORBIDDEN_PATH_GLOBS:
        if fnmatch.fnmatch(norm, glob):
            return Finding(
                path=norm, line=0, severity=P.BLOCK, source="path",
                rule="forbidden-path", matched=norm,
                why="This path must never be committed (it holds private "
                    "values, staging scratch, or derived output).",
                fix="Unstage it: git restore --staged %s" % norm)
    return None


def scan_text(path: str, text: str, allow: List[AllowEntry],
              denylist: List[DenyEntry]) -> List[Finding]:
    norm = path.replace(os.sep, "/")
    if norm in SELF_EXCLUDED:
        return []

    findings: List[Finding] = []

    for pat in P.PATTERNS:
        for m in pat.rx.finditer(text):
            allowed = _is_allowed(norm, pat.id, allow)
            findings.append(Finding(
                path=norm, line=_line_of(text, m.start()),
                severity=pat.severity, source="pattern", rule=pat.id,
                matched=m.group(0), why=pat.why, fix=pat.fix,
                suppression=("%s (scan/allow.txt, %s)" % (allowed.reason, allowed.added)
                             if allowed else None)))

    # Denylist, case-SENSITIVE and word-anchored. Case-insensitive substring
    # matching is unusable: on the forecast spec, /[a-z]*ally[a-z]*/i matches
    # technically, materially, manually, individually -- while \bAlly\b
    # matches nothing at all.
    masked: Set[Tuple[int, int]] = set()
    for entry in denylist:
        rx = re.compile(r"\b%s\b" % re.escape(entry.term))
        for m in rx.finditer(text):
            if any(m.start() < e and m.end() > s for s, e in masked):
                continue   # inside an already-matched longer term
            if entry.tier in ("strict", "word"):
                masked.add((m.start(), m.end()))
            findings.append(Finding(
                path=norm, line=_line_of(text, m.start()),
                severity=P.BLOCK if entry.tier in ("strict", "word") else P.REVIEW,
                source="denylist", rule=entry.tier, matched=m.group(0),
                why="On the denylist (%s tier)." % entry.tier,
                fix=entry.note or "Replace with a variable, or re-tier it in "
                                  "private/denylist.txt if this is a false positive."))

    findings.sort(key=lambda f: (f.path, f.line, f.rule))
    return findings


# --------------------------------------------------------------------------
# git plumbing
# --------------------------------------------------------------------------

def _git(root: str, *args: str) -> str:
    return subprocess.run(("git",) + args, cwd=root, check=True,
                          stdout=subprocess.PIPE).stdout.decode("utf-8", "replace")


def _git_names(root: str, *args: str) -> List[str]:
    raw = subprocess.run(("git",) + args + ("-z",), cwd=root, check=True,
                         stdout=subprocess.PIPE).stdout
    return [n.decode("utf-8", "replace") for n in raw.split(b"\0") if n]


def _blob(root: str, ref: str) -> Optional[str]:
    """Content at a git ref (e.g. ':path' for the index). None if binary."""
    r = subprocess.run(("git", "show", ref), cwd=root,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if r.returncode != 0:
        return None
    try:
        return r.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan_staged(root: str) -> List[Finding]:
    """Scan STAGED BLOB CONTENT, not the worktree.

    Scanning the worktree would miss partially-staged files and mishandle
    `git commit -a`. The index is what is actually about to be committed.
    """
    allow, deny = load_allow(root), load_denylist(root)
    names = _git_names(root, "diff", "--cached", "--name-only",
                       "--diff-filter=ACM")
    findings: List[Finding] = []
    for name in names:
        guard = check_path(name)
        if guard:
            findings.append(guard)
            continue
        text = _blob(root, ":" + name)
        if text is not None:
            findings.extend(scan_text(name, text, allow, deny))
    return findings


def scan_worktree(root: str) -> List[Finding]:
    allow, deny = load_allow(root), load_denylist(root)
    names = _git_names(root, "ls-files", "--cached", "--others",
                       "--exclude-standard")
    findings: List[Finding] = []
    for name in names:
        full = os.path.join(root, name)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        findings.extend(scan_text(name, text, allow, deny))
    return findings


ZERO = "0" * 40


def scan_push(root: str, stdin_lines: List[str]) -> List[Finding]:
    """Scan every commit being pushed -- the real disclosure boundary.

    A `git commit --no-verify` bypasses pre-commit but is still caught here.
    git feeds pre-push: <local ref> <local sha> <remote ref> <remote sha>
    """
    allow, deny = load_allow(root), load_denylist(root)
    findings: List[Finding] = []
    seen: Set[Tuple[str, str]] = set()

    for line in stdin_lines:
        parts = line.split()
        if len(parts) != 4:
            continue
        _, local_sha, _, remote_sha = parts
        if local_sha.startswith("0" * 8):
            continue                      # branch deletion
        if remote_sha.startswith("0" * 8):
            names = _git_names(root, "ls-tree", "-r", "--name-only", local_sha)
        else:
            names = _git_names(root, "diff", "--name-only",
                               "--diff-filter=ACM", remote_sha, local_sha)
        for name in names:
            if (local_sha, name) in seen:
                continue
            seen.add((local_sha, name))
            guard = check_path(name)
            if guard:
                findings.append(guard)
                continue
            text = _blob(root, "%s:%s" % (local_sha, name))
            if text is not None:
                findings.extend(scan_text(name, text, allow, deny))
    return findings


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def report(findings: List[Finding], stage: str) -> int:
    """Print all findings. Return the exit code (1 if anything blocks)."""
    blocking = [f for f in findings if f.severity == P.BLOCK and not f.suppression]
    warned = [f for f in findings if f.severity == P.REVIEW and not f.suppression]
    allowed = [f for f in findings if f.suppression]

    def emit(group: List[Finding], label: str) -> None:
        if not group:
            return
        print("\n%s (%d)" % (label, len(group)))
        explained: Set[Tuple[str, str]] = set()
        for f in group:
            print("  %s:%d  %-22s %s" % (f.path, f.line, f.rule,
                                         f.matched[:60].replace("\n", " ")))
            key = (f.path, f.rule)
            if key in explained:
                continue
            explained.add(key)
            if f.suppression:
                print("      allowed: %s" % f.suppression)
            else:
                print("      why: %s" % f.why)
                print("      fix: %s" % f.fix)

    emit(blocking, "BLOCKING")
    emit(warned, "REVIEW (does not block)")
    emit(allowed, "ALLOWED by scan/allow.txt")

    print("\n%s: %d blocking, %d review, %d allowed"
          % (stage, len(blocking), len(warned), len(allowed)))
    if blocking:
        halted = {"pre-commit scan": "Nothing was committed.",
                  "pre-push scan": "NOTHING WAS PUSHED.",
                  "worktree scan": "Not blocking anything -- this was a manual scan."}
        print("\n%s Fix the blocking findings above, or -- if one is a false\n"
              "positive -- add a path-scoped entry to scan/allow.txt with a reason,\n"
              "or re-tier the term in private/denylist.txt."
              % halted.get(stage, "Blocked."))
        return 1
    return 0
