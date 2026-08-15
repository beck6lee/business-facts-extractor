import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import render_md

FACTS = [
    {
        "id": "F-0001", "type": "entity", "domain": "org",
        "statement": "Employee 代表一名员工",
        "entities": ["Employee"], "actors": [],
        "sources": [{"file": "models.py", "lines": "10-30", "kind": "backend"}],
        "enforcement": "database", "confidence": "high",
    },
    {
        "id": "F-0002", "type": "relationship", "domain": "org",
        "statement": "一个部门有多个员工",
        "entities": ["Department", "Employee"], "actors": [],
        "sources": [{"file": "models.py", "lines": "31-35", "kind": "backend"}],
        "enforcement": "database", "confidence": "high",
        "relation": {"from": "Department", "to": "Employee", "cardinality": "1-N", "label": "employs"},
    },
    {
        "id": "F-0003", "type": "rule", "domain": "onboarding",
        "statement": "身份证号必填且 18 位",
        "entities": ["Employee"], "actors": ["新员工"],
        "sources": [{"file": "api.py", "lines": "85-92", "kind": "backend"}],
        "enforcement": "backend", "confidence": "high",
    },
    {
        "id": "F-0004", "type": "edge_case", "domain": "onboarding",
        "statement": "重复提交相同身份证号返回 409",
        "entities": ["Employee"], "actors": [],
        "sources": [{"file": "api.py", "lines": "95-99", "kind": "backend"}],
        "enforcement": "backend", "confidence": "low",
    },
    {
        "id": "F-0005", "type": "discrepancy", "domain": "onboarding",
        "statement": "前端限制姓名 20 字，后端无限制",
        "entities": ["Employee"], "actors": [],
        "sources": [
            {"file": "Form.tsx", "lines": "40-42", "kind": "frontend"},
            {"file": "api.py", "lines": "80-84", "kind": "backend"},
        ],
        "enforcement": "frontend", "confidence": "high",
    },
]


class RenderErTest(unittest.TestCase):
    def test_relationship_renders_mermaid_edge(self):
        out = render_md.render_er(FACTS)
        self.assertIn("```mermaid", out)
        self.assertIn("erDiagram", out)
        self.assertIn('Department ||--o{ Employee : "employs"', out)

    def test_orphan_entity_renders_standalone(self):
        facts = FACTS + [dict(FACTS[0], id="F-0006", entities=["AuditLog"])]
        out = render_md.render_er(facts)
        self.assertIn("  AuditLog\n", out)


class RenderRulesTest(unittest.TestCase):
    def test_groups_by_domain_sorted(self):
        out = render_md.render_rules(FACTS)
        self.assertIn("### onboarding", out)
        self.assertNotIn("### org", out)  # org has no rule-type facts

    def test_rule_line_contains_source_and_enforcement(self):
        out = render_md.render_rules(FACTS)
        self.assertIn("[F-0003] 身份证号必填且 18 位", out)
        self.assertIn("`api.py:85-92`", out)
        self.assertIn("enforcement: backend", out)

    def test_low_confidence_marked(self):
        out = render_md.render_rules(FACTS)
        line = [l for l in out.splitlines() if "F-0004" in l][0]
        self.assertIn("⚠️", line)

    def test_discrepancy_tagged(self):
        out = render_md.render_rules(FACTS)
        line = [l for l in out.splitlines() if "F-0005" in l][0]
        self.assertIn("[DISCREPANCY]", line)


class CliTest(unittest.TestCase):
    def test_cli_er_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "facts.json")
            with open(p, "w") as fh:
                json.dump({"version": "1", "project": {"name": "d", "stack": []}, "facts": FACTS}, fh)
            r = subprocess.run([sys.executable, render_md.__file__, p, "--section", "er"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("erDiagram", r.stdout)


if __name__ == "__main__":
    unittest.main()
