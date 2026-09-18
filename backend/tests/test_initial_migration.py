from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    REPOSITORY_ROOT
    / "backend"
    / "migrations"
    / "versions"
    / "20260917_0001_initial_schema.py"
)
SCHEMA = REPOSITORY_ROOT / "database" / "schema.sql"


class InitialMigrationContractTest(unittest.TestCase):
    def test_revision_and_table_set_are_stable(self) -> None:
        source = MIGRATION.read_text(encoding="utf-8")

        self.assertIn('revision: str = "20260917_0001"', source)
        self.assertIn("down_revision: str | None = None", source)
        self.assertEqual(len(re.findall(r'op\.create_table\(\s*"', source)), 10)

    def test_schema_enforces_runtime_safety_constraints(self) -> None:
        schema = SCHEMA.read_text(encoding="utf-8")

        for constraint in (
            "ck_scenario_concurrency",
            "ck_execution_dates",
            "ck_metric_error_rate",
            "ck_prediction_probability",
            "ck_decision_concurrency",
            "fk_scenario_endpoint_project",
        ):
            self.assertIn(constraint, schema)


if __name__ == "__main__":
    unittest.main()
