#!/usr/bin/env python3
"""Validate facts.json produced by the business-facts-extractor skill.

Checks schema structure and that every source file:lines reference actually
exists under the target project root. Content *relevance* of a source is the
agent's responsibility during review — this script enforces everything
machine-checkable.

Usage: python3 validate_facts.py <facts.json> [--root <project_root>]
Exit code 0 = valid, 1 = problems found (printed to stdout).
"""
import argparse
import json
import os
import re
import sys

FACT_TYPES = {"entity", "relationship", "user_flow", "rule", "constraint", "edge_case", "discrepancy"}
ENFORCEMENT = {"frontend", "backend", "database", "multiple"}
CONFIDENCE = {"high", "medium", "low"}
SOURCE_KIND = {"frontend", "backend", "database", "config", "other"}
LINES_RE = re.compile(r"^[1-9]\d*(-[1-9]\d*)?$")


def validate_structure(data):
    errors = []
    if not isinstance(data, dict):
        return ["root must be an object"]
    proj = data.get("project")
    if not isinstance(proj, dict) or not proj.get("name"):
        errors.append("project.name is required")
    facts = data.get("facts")
    if not isinstance(facts, list) or not facts:
        errors.append("facts must be a non-empty list")
        return errors
    ids = set()
    for i, f in enumerate(facts):
        where = "facts[%d]" % i
        if not isinstance(f, dict):
            errors.append("%s: must be an object" % where)
            continue
        fid = f.get("id") or where
        if not f.get("id"):
            errors.append("%s: id is required" % where)
        elif not isinstance(f["id"], str):
            errors.append("%s: id must be a string" % where)
        elif f["id"] in ids:
            errors.append("%s: duplicate id" % fid)
        else:
            ids.add(f["id"])
        if f.get("type") not in FACT_TYPES:
            errors.append("%s: type must be one of %s" % (fid, sorted(FACT_TYPES)))
        if not f.get("statement"):
            errors.append("%s: statement is required" % fid)
        if not f.get("domain"):
            errors.append("%s: domain is required" % fid)
        if f.get("enforcement") not in ENFORCEMENT:
            errors.append("%s: enforcement must be one of %s" % (fid, sorted(ENFORCEMENT)))
        if f.get("confidence") not in CONFIDENCE:
            errors.append("%s: confidence must be one of %s" % (fid, sorted(CONFIDENCE)))
        for key in ("entities", "actors"):
            if key in f and not isinstance(f[key], list):
                errors.append("%s: %s must be a list" % (fid, key))
        sources = f.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("%s: sources must be a non-empty list" % fid)
            sources = []
        for j, s in enumerate(sources):
            sw = "%s.sources[%d]" % (fid, j)
            if not isinstance(s, dict):
                errors.append("%s: must be an object" % sw)
                continue
            if not isinstance(s.get("file"), str) or not s["file"]:
                errors.append("%s: file must be a non-empty string" % sw)
            lines = str(s.get("lines", ""))
            if not LINES_RE.match(lines):
                errors.append("%s: lines must look like '12' or '12-40', got %r" % (sw, lines))
            elif "-" in lines:
                a, b = lines.split("-")
                if int(a) > int(b):
                    errors.append("%s: line range start > end" % sw)
            if s.get("kind") not in SOURCE_KIND:
                errors.append("%s: kind must be one of %s" % (sw, sorted(SOURCE_KIND)))
        if f.get("type") == "relationship":
            rel = f.get("relation")
            if not isinstance(rel, dict) or not all(rel.get(k) for k in ("from", "to", "cardinality")):
                errors.append("%s: relationship facts need relation.from/to/cardinality" % fid)
        if f.get("type") == "discrepancy" and len(sources) < 2:
            errors.append("%s: discrepancy needs sources from both sides (>= 2)" % fid)
    return errors


def _line_count(path, upto):
    n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for _ in fh:
            n += 1
            if n >= upto:
                break
    return n


def validate_sources_exist(data, root):
    root = os.path.realpath(root)
    errors = []
    counts = {}  # resolved path -> exact line count (only complete counts are cached)
    for f in data.get("facts", []):
        fid = f.get("id", "?")
        for j, s in enumerate(f.get("sources") or []):
            if not isinstance(s, dict):
                continue
            path = s.get("file")
            if not isinstance(path, str) or not path:
                continue
            full = os.path.realpath(os.path.join(root, path))
            if os.path.commonpath((root, full)) != root:
                errors.append("%s.sources[%d]: path escapes --root: %s" % (fid, j, path))
                continue
            if not os.path.isfile(full):
                errors.append("%s.sources[%d]: file not found: %s" % (fid, j, path))
                continue
            lines = str(s.get("lines", ""))
            if LINES_RE.match(lines):
                end = int(lines.split("-")[-1])
                if full in counts:
                    n = counts[full]
                else:
                    n = _line_count(full, end)
                    if n < end:  # loop ran to EOF -> exact count, safe to cache
                        counts[full] = n
                if end > n:
                    errors.append("%s.sources[%d]: %s has only %d lines, but lines=%s" % (fid, j, path, n, lines))
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts_json")
    ap.add_argument("--root", default=".", help="project root that source paths are relative to")
    args = ap.parse_args()
    try:
        with open(args.facts_json, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print("ERROR: cannot load %s: %s" % (args.facts_json, e))
        return 1
    errors = validate_structure(data)
    if not errors:
        errors = validate_sources_exist(data, os.path.abspath(args.root))
    if errors:
        print("FAILED: %d problem(s)" % len(errors))
        for e in errors:
            print(" -", e)
        return 1
    print("OK: %d facts validated" % len(data["facts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
