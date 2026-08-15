import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "validate_facts.py")

VALID_FACT = {
    "id": "F-0001",
    "type": "rule",
    "domain": "onboarding",
    "statement": "身份证号必填且须通过 18 位校验",
    "entities": ["Employee"],
    "actors": ["新员工"],
    "sources": [{"file": "api/employee.py", "lines": "1-2", "kind": "backend"}],
    "enforcement": "backend",
    "confidence": "high",
}


def make_doc(**fact_overrides):
    fact = dict(VALID_FACT, **fact_overrides)
    return {"version": "1", "project": {"name": "demo", "stack": ["FastAPI"]}, "facts": [fact]}


class ValidateFactsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, "api"))
        with open(os.path.join(self.root, "api", "employee.py"), "w") as fh:
            fh.write("line1\nline2\nline3\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_validator(self, doc):
        facts_path = os.path.join(self.root, "facts.json")
        with open(facts_path, "w") as fh:
            json.dump(doc, fh)
        return subprocess.run(
            [sys.executable, SCRIPT, facts_path, "--root", self.root],
            capture_output=True, text=True,
        )

    def test_valid_fact_passes(self):
        r = self.run_validator(make_doc())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    def test_missing_sources_fails(self):
        r = self.run_validator(make_doc(sources=[]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("sources", r.stdout)

    def test_bad_type_fails(self):
        r = self.run_validator(make_doc(type="summary"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("type", r.stdout)

    def test_duplicate_id_fails(self):
        doc = make_doc()
        doc["facts"].append(dict(VALID_FACT))
        r = self.run_validator(doc)
        self.assertEqual(r.returncode, 1)
        self.assertIn("duplicate", r.stdout)

    def test_bad_lines_format_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": "api/employee.py", "lines": "abc", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("lines", r.stdout)

    def test_lines_beyond_file_length_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": "api/employee.py", "lines": "1-99", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("1-99", r.stdout)

    def test_reversed_range_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": "api/employee.py", "lines": "3-1", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("start > end", r.stdout)

    def test_unhashable_id_fails(self):
        r = self.run_validator(make_doc(id=["F-1"]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("id must be a string", r.stdout)

    def test_non_string_source_file_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": ["x"], "lines": "1", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("file must be a non-empty string", r.stdout)

    def test_path_escape_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": "../../etc/hosts", "lines": "1", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("escapes", r.stdout)

    def test_lines_zero_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": "api/employee.py", "lines": "0", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("lines", r.stdout)

    def test_missing_sources_key_fails(self):
        doc = make_doc()
        del doc["facts"][0]["sources"]
        r = self.run_validator(doc)
        self.assertEqual(r.returncode, 1)
        self.assertIn("sources", r.stdout)

    def test_non_dict_fact_fails(self):
        doc = make_doc()
        doc["facts"] = ["nope"]
        r = self.run_validator(doc)
        self.assertEqual(r.returncode, 1)

    def test_missing_file_fails(self):
        r = self.run_validator(make_doc(sources=[{"file": "api/nope.py", "lines": "1-2", "kind": "backend"}]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("file not found", r.stdout)

    def test_relationship_needs_relation_object(self):
        r = self.run_validator(make_doc(type="relationship"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("relation", r.stdout)

    def test_relationship_with_relation_passes(self):
        r = self.run_validator(make_doc(
            type="relationship",
            relation={"from": "Department", "to": "Employee", "cardinality": "1-N", "label": "employs"},
        ))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_discrepancy_needs_two_sources(self):
        r = self.run_validator(make_doc(type="discrepancy"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("discrepancy", r.stdout)


if __name__ == "__main__":
    unittest.main()
