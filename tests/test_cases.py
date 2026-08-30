import csv
import unittest
from collections import Counter
from pathlib import Path


class CasesDatasetValidationTestCase(unittest.TestCase):
    REQUIRED_COLUMNS = {
        "case_id",
        "title",
        "symptom",
        "topology_note",
        "show_outputs",
        "expected_fault",
        "osi_layer",
        "concept",
        "severity",
    }
    REQUIRED_CATEGORIES = {
        "VLAN",
        "Default gateway",
        "DHCP",
        "DNS",
        "Routing",
        "ACL",
        "NAT",
        "Wireless",
    }
    VALID_SEVERITIES = {"SEV-1", "SEV-2", "SEV-3"}
    VALID_OSI_LAYERS = {"L1", "L2", "L3", "L4", "L5", "L6", "L7"}

    @classmethod
    def setUpClass(cls):
        cls.csv_path = Path(__file__).resolve().parents[1] / "data" / "cases.csv"
        with cls.csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            cls.fieldnames = set(reader.fieldnames or [])
            cls.rows = list(reader)

    def test_required_columns_exist(self):
        missing = self.REQUIRED_COLUMNS - self.fieldnames
        self.assertFalse(missing, f"Missing required columns: {sorted(missing)}")

    def test_minimum_case_count(self):
        self.assertGreaterEqual(len(self.rows), 30, "Dataset must include at least 30 cases")

    def test_case_ids_are_unique(self):
        case_ids = [row.get("case_id", "").strip() for row in self.rows]
        self.assertEqual(len(case_ids), len(set(case_ids)), "case_id values must be unique")

    def test_required_categories_are_present_and_balanced(self):
        counts = Counter(row.get("concept", "").strip() for row in self.rows)
        missing = [category for category in self.REQUIRED_CATEGORIES if counts.get(category, 0) == 0]
        self.assertFalse(missing, f"Missing required categories: {missing}")

        for category in self.REQUIRED_CATEGORIES:
            self.assertGreaterEqual(
                counts[category],
                3,
                f"Category '{category}' should have at least 3 cases",
            )
            self.assertLessEqual(
                counts[category],
                5,
                f"Category '{category}' should have at most 5 cases",
            )

    def test_required_fields_not_empty(self):
        for index, row in enumerate(self.rows, start=2):
            for column in self.REQUIRED_COLUMNS:
                value = (row.get(column) or "").strip()
                self.assertTrue(value, f"Row {index} has empty required field '{column}'")

    def test_severity_values_valid(self):
        for index, row in enumerate(self.rows, start=2):
            severity = (row.get("severity") or "").strip()
            self.assertIn(
                severity,
                self.VALID_SEVERITIES,
                f"Row {index} has invalid severity '{severity}'",
            )

    def test_osi_layer_values_valid(self):
        for index, row in enumerate(self.rows, start=2):
            osi_layer = (row.get("osi_layer") or "").strip()
            self.assertIn(
                osi_layer,
                self.VALID_OSI_LAYERS,
                f"Row {index} has invalid osi_layer '{osi_layer}'",
            )


if __name__ == "__main__":
    unittest.main()
