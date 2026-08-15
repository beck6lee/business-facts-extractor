#!/usr/bin/env python3
"""Render mechanical Markdown sections from facts.json.

Keeps BUSINESS_FACTS.md and facts.json in sync: the agent writes prose
(overview, user-task narratives) and embeds output of this script for the
mechanical parts (ER diagram, rule/constraint/edge-case lists).

Usage:
  python3 render_md.py <facts.json> --section er     # Mermaid ER diagram
  python3 render_md.py <facts.json> --section rules  # rules grouped by domain
"""
import argparse
import json
from collections import defaultdict

CARD_MAP = {"1-1": "||--||", "1-N": "||--o{", "N-1": "}o--||", "N-N": "}o--o{"}
RULE_TYPES = ("rule", "constraint", "edge_case", "discrepancy")


def render_er(facts):
    lines = ["```mermaid", "erDiagram"]
    named = set()
    for f in facts:
        if f.get("type") != "relationship":
            continue
        r = f.get("relation")
        if not isinstance(r, dict):
            continue
        arrow = CARD_MAP.get(r.get("cardinality"), "||--o{")
        lines.append('  %s %s %s : "%s"' % (r["from"], arrow, r["to"], r.get("label", "relates to")))
        named.add(r["from"])
        named.add(r["to"])
    for f in facts:
        if f.get("type") != "entity":
            continue
        for e in f.get("entities", []):
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
    out = []
    for domain in sorted(by_domain):
        out.append("### %s" % domain)
        out.append("")
        for f in by_domain[domain]:
            srcs = "; ".join("`%s:%s`" % (s["file"], s["lines"]) for s in f.get("sources", []))
            tag = " **[DISCREPANCY]**" if f.get("type") == "discrepancy" else ""
            conf = " ⚠️" if f.get("confidence") == "low" else ""
            out.append("- [%s]%s %s%s" % (f["id"], tag, f["statement"], conf))
            out.append("  - 出处: %s · enforcement: %s" % (srcs, f.get("enforcement", "?")))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts_json")
    ap.add_argument("--section", choices=["er", "rules"], required=True)
    args = ap.parse_args()
    with open(args.facts_json, encoding="utf-8") as fh:
        data = json.load(fh)
    facts = data.get("facts", [])
    print(render_er(facts) if args.section == "er" else render_rules(facts), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
