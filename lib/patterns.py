"""Committed regex families for the sanitization gate.

INVARIANT: this file must never contain a customer name, a colleague name, or
any other denylisted literal. Those live in private/denylist.txt, which is
gitignored because the list of Redis customers is itself confidential.

Because this file necessarily contains literal fragments that its own patterns
match (credential prefixes, cluster-name prefixes), the scanner skips it by
path. See scan.SELF_EXCLUDED.

Targets Python 3.9. Stdlib only, no third-party imports -- see README.
"""

import re
from typing import List, NamedTuple

BLOCK = "block"
REVIEW = "review"


class Pattern(NamedTuple):
    id: str          # stable id; what scan/allow.txt suppresses
    severity: str    # BLOCK or REVIEW
    rx: "re.Pattern"
    why: str         # why this is a problem
    fix: str         # what to do about it


def _p(pid, severity, pattern, why, fix, flags=0):
    return Pattern(pid, severity, re.compile(pattern, flags), why, fix)


PATTERNS: List[Pattern] = [
    # ---- credentials: always block, never allowable -----------------------
    _p("cred-prefix", BLOCK,
       r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
       r"|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,})",
       "Looks like a live API key or token.",
       "Remove it. Rotate the credential if it was ever real."),
    _p("cred-jwt", BLOCK,
       r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
       "Looks like a JWT.",
       "Remove it. Rotate if real."),
    _p("cred-pem", BLOCK,
       r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
       "Private key block.",
       "Remove it. Rotate immediately."),

    # ---- Redis-internal identifiers ---------------------------------------
    _p("redis-email", BLOCK,
       r"\b[A-Za-z0-9._%+-]+@redis\.com\b",
       "Internal employee email address (PII).",
       "Replace with a variable, or drop the attribution entirely."),
    _p("redis-host", BLOCK,
       r"\b[A-Za-z0-9-]+\.(?:redislabs\.com|redis\.cloud)\b",
       "Internal or customer-specific Redis hostname.",
       "Replace with a variable such as {{CLUSTER_FQDN}}."),
    _p("sfdc-host", BLOCK,
       r"\b[A-Za-z0-9-]+\.(?:lightning\.force\.com|my\.salesforce\.com)\b",
       "Salesforce org URL -- identifies the internal CRM instance.",
       "Drop the link. Reference the record by variable instead."),

    # ---- Salesforce schema -------------------------------------------------
    # The single highest-volume family. 97 unique hits in the forecast spec,
    # where the field map IS the prompt -- that is what the private overlay
    # and scan/allow.txt exist for. Do not soften this to REVIEW.
    _p("sfdc-field", BLOCK,
       r"\b[A-Za-z][A-Za-z0-9_]*__[cr]\b",
       "Salesforce custom field or relationship -- internal CRM schema.",
       "Move the field map into a private overlay variable, or allow this "
       "path in scan/allow.txt if the prompt is useless without it."),
    _p("sfdc-id", BLOCK,
       r"\b(?:00[1-9A-Za-z]|a[0-9A-Za-z]{2}|500|701|00Q|00D)"
       r"[0-9A-Za-z]{12}(?:[0-9A-Za-z]{3})?\b",
       "Looks like a Salesforce record ID.",
       "Remove it. Reference the record by variable."),

    # ---- infrastructure ----------------------------------------------------
    _p("cluster-kaas", BLOCK,
       r"\b(?:kaas|dcaas)-[a-z0-9-]{4,}\b",
       "Managed-cluster hostname -- identifies a specific deployment.",
       "Replace with a variable such as {{CLUSTER_NAME}}."),
    _p("cluster-region-shape", REVIEW,
       r"\b[a-z0-9]+(?:-[a-z0-9]+){2,}-(?:westus\d?|eastus\d?|centralus"
       r"|us-(?:east|west|central)-?\d|[a-z]{2,}-[a-z]+-\d)\b",
       "Shaped like a cloud-region-suffixed hostname.",
       "Confirm it is not a real host. If it is, use a variable."),
    _p("private-ip", REVIEW,
       r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b",
       "Private IP address from a real environment.",
       "Replace with a documentation-range address or a variable."),

    # ---- record references -------------------------------------------------
    # Jira keys are REVIEW, not BLOCK: the pattern also matches UTF-8,
    # SHA-256, ISO-8601, RFC-2119, GPT-4 and friends. Blocking would fire
    # constantly on ordinary prose and teach Kyle to use --no-verify.
    _p("jira-key", REVIEW,
       r"\b[A-Z]{2,10}-\d{1,6}\b",
       "Possible Jira issue key (also matches UTF-8, SHA-256, ISO-8601).",
       "If it is a real ticket, drop it or use a variable."),
    _p("support-case", BLOCK,
       r"\b(?:case|ticket|sf)[\s#:-]{0,3}\d{5,}\b",
       "Support case number -- ties the prompt to a specific customer issue.",
       "Drop it, or generalise to 'a support case'.",
       re.IGNORECASE),

    # ---- commercial figures and PII ---------------------------------------
    _p("money-grouped", BLOCK,
       r"\$\s?\d{1,3}(?:,\d{3})+(?:\.\d+)?\b",
       "Specific dollar figure -- likely deal or contract value.",
       "Generalise, or move the threshold into a variable."),
    _p("money-suffixed", BLOCK,
       r"\$\s?\d+(?:\.\d+)?\s?[KMB]\b",
       "Specific dollar figure -- likely deal or contract value.",
       "Generalise, or move the threshold into a variable."),
    _p("phone-us", BLOCK,
       r"(?<!\d)\+?1?[\s.-]?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)",
       "Phone number (PII).",
       "Remove it."),
    _p("email-generic", REVIEW,
       r"\b[A-Za-z0-9._%+-]+@(?!redis\.com|example\.(?:com|org|net))"
       r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
       "Email address (PII) on a non-Redis, non-example domain.",
       "Remove it, or use an example.com address."),
]

PATTERNS_BY_ID = {p.id: p for p in PATTERNS}
