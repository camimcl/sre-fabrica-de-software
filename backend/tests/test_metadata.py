import ast
from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
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
}


class MetadataContractTest(unittest.TestCase):
    def test_schema_contains_every_sprint_02_table(self) -> None:
        schema = (REPOSITORY_ROOT / "database" / "schema.sql").read_text(
            encoding="utf-8"
        )

        tables = set(re.findall(r"CREATE TABLE ([a-z_]+)", schema))
        self.assertEqual(tables, EXPECTED_TABLES)

    def test_sqlalchemy_sources_register_every_table(self) -> None:
        modules = REPOSITORY_ROOT / "backend" / "app" / "modules"
        source = "\n".join(
            path.read_text(encoding="utf-8") for path in modules.glob("*/models.py")
        )

        tables = set(re.findall(r'__tablename__\s*=\s*"([a-z_]+)"', source))
        self.assertEqual(tables, EXPECTED_TABLES)

    def test_schema_migration_and_sqlalchemy_columns_are_equivalent(self) -> None:
        schema_source = (REPOSITORY_ROOT / "database" / "schema.sql").read_text(
            encoding="utf-8"
        )
        schema_columns: dict[str, set[str]] = {}
        for table_name, body in re.findall(
            r"CREATE TABLE ([a-z_]+) \((.*?)\n\);", schema_source, re.DOTALL
        ):
            schema_columns[table_name] = {
                line.strip().split()[0]
                for line in body.splitlines()
                if re.match(r"^    [a-z0-9_]+\s", line)
            }

        migration_source = (
            REPOSITORY_ROOT
            / "backend"
            / "migrations"
            / "versions"
            / "20260917_0001_initial_schema.py"
        ).read_text(encoding="utf-8")
        migration_columns: dict[str, set[str]] = {}
        for node in ast.walk(ast.parse(migration_source)):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "create_table"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                continue
            migration_columns[node.args[0].value] = {
                argument.args[0].value
                for argument in node.args[1:]
                if isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Attribute)
                and argument.func.attr == "Column"
                and argument.args
                and isinstance(argument.args[0], ast.Constant)
            }

        sqlalchemy_columns: dict[str, set[str]] = {}
        modules = REPOSITORY_ROOT / "backend" / "app" / "modules"
        for path in modules.glob("*/models.py"):
            for node in ast.parse(path.read_text(encoding="utf-8")).body:
                if not isinstance(node, ast.ClassDef):
                    continue
                table_name = None
                columns: set[str] = set()
                for statement in node.body:
                    if (
                        isinstance(statement, ast.Assign)
                        and any(
                            isinstance(target, ast.Name)
                            and target.id == "__tablename__"
                            for target in statement.targets
                        )
                        and isinstance(statement.value, ast.Constant)
                    ):
                        table_name = statement.value.value
                    if (
                        isinstance(statement, ast.AnnAssign)
                        and isinstance(statement.target, ast.Name)
                        and isinstance(statement.value, ast.Call)
                        and isinstance(statement.value.func, ast.Name)
                        and statement.value.func.id == "mapped_column"
                    ):
                        columns.add(statement.target.id)
                if table_name:
                    sqlalchemy_columns[table_name] = columns

        self.assertEqual(schema_columns, migration_columns)
        self.assertEqual(schema_columns, sqlalchemy_columns)


if __name__ == "__main__":
    unittest.main()
