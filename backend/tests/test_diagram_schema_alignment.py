from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DiagramSchemaAlignmentTest(unittest.TestCase):
    def test_relational_diagram_lists_every_table(self) -> None:
        source = (
            REPOSITORY_ROOT / "docs" / "diagrams" / "relational-model.mmd"
        ).read_text(encoding="utf-8")

        for table in (
            "users",
            "projects",
            "endpoints",
            "test_scenarios",
            "test_executions",
            "metric_windows",
            "model_versions",
            "risk_predictions",
            "control_decisions",
            "execution_reports",
        ):
            self.assertIn(table, source)

    def test_optional_relations_match_database_constraints(self) -> None:
        """The diagram must not require child rows that the schema allows to be absent."""
        source = (
            REPOSITORY_ROOT / "docs" / "diagrams" / "relational-model.mmd"
        ).read_text(encoding="utf-8")

        for relationship in (
            "projects ||--o{ endpoints : project_id",
            "test_executions ||--o{ metric_windows : execution_id",
            "metric_windows ||--o| control_decisions : metric_window_id",
        ):
            self.assertIn(relationship, source)


if __name__ == "__main__":
    unittest.main()
