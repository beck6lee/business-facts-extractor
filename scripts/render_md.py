#!/usr/bin/env python3
"""Render mechanical Markdown sections from facts.json.

Keeps BUSINESS_FACTS.md and facts.json in sync: the agent writes prose
(overview, user-task narratives) and embeds output of this script for the
mechanical parts (ER diagram, rule/constraint/edge-case lists).

Usage:
  python3 render_md.py <facts.json> --section er     # Mermaid ER diagram
  python3 render_md.py <facts.json> --section rules  # rules grouped by domain

Entity names that are not valid Mermaid identifiers are sanitized
(non-alphanumeric chars become "_", leading digits get a "_" prefix).
"""
import argparse
import json
import re
from collections import defaultdict

CARD_MAP = {"1-1": "||--||", "1-N": "||--o{", "N-1": "}o--||", "N-N": "}o--o{"}
RULE_TYPES = ("rule", "constraint", "edge_case", "discrepancy")
MERMAID_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize_ident(name):
    """Make name a valid Mermaid entity identifier (stable per input)."""
    if MERMAID_IDENT.match(name):
        return name
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if cleaned and cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned


def render_er(facts):
    lines = ["```mermaid", "erDiagram"]
    named = set()
    for f in facts:
        if f.get("type") != "relationship":
            continue
        r = f.get("relation")
        if not isinstance(r, dict):
            continue
        frm, to = r.get("from"), r.get("to")
        if not (frm and to):
            continue
        frm, to = sanitize_ident(frm), sanitize_ident(to)
        arrow = CARD_MAP.get(r.get("cardinality"), "||--o{")
        label = r.get("label", "relates to").replace('"', "'")
        lines.append('  %s %s %s : "%s"' % (frm, arrow, to, label))
        named.add(frm)
        named.add(to)
    for f in facts:
        if f.get("type") != "entity":
            continue
        for e in f.get("entities", []):
            e = sanitize_ident(e)
            if e not in named:
                lines.append("  %s" % e)
                named.add(e)
    lines.append("```")
    return "\n".join(lines) + "\n"


def render_rules(facts):
    by_domain = defaultdict(list)
    for f in facts:
        if f.get("type") in RULE_TYPES:
            by_domain[f.get("domain", "general")].append(f)
    if not by_domain:
        return ""
    out = []
    for domain in sorted(by_domain):
        out.append("### %s" % domain)
        out.append("")
        for f in by_domain[domain]:
            srcs = "; ".join("`%s:%s`" % (s.get("file", "?"), s.get("lines", "?")) for s in f.get("sources", []))
            tag = " **[DISCREPANCY]**" if f.get("type") == "discrepancy" else ""
            conf = " ⚠️" if f.get("confidence") == "low" else ""
            out.append("- [%s]%s %s%s" % (f.get("id", "?"), tag, f.get("statement", ""), conf))
            out.append("  - 出处: %s · enforcement: %s" % (srcs, f.get("enforcement", "?")))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts_json")
    ap.add_argument("--section", choices=["er", "rules"], required=True)
    args = ap.parse_args()
    try:
        with open(args.facts_json, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print("ERROR: cannot load %s: %s" % (args.facts_json, e))
        return 1
    facts = data.get("facts", [])
    print(render_er(facts) if args.section == "er" else render_rules(facts), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
