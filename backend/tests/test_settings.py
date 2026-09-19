import unittest
from unittest.mock import patch

from app.core.config import Settings


class SettingsTest(unittest.TestCase):
    def test_database_url_is_required(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Database connection variables must be set"):
                Settings()

    def test_database_url_comes_from_environment(self) -> None:
        expected = "postgresql+psycopg://app:secret@db:5432/loadforge"

        with patch.dict("os.environ", {"DATABASE_URL": expected}, clear=True):
            self.assertEqual(Settings().database_url, expected)

    def test_database_url_can_be_built_from_compose_variables(self) -> None:
        values = {
            "POSTGRES_DB": "loadforge",
            "POSTGRES_USER": "app",
            "POSTGRES_PASSWORD": "a b@c",
            "POSTGRES_HOST": "db",
            "POSTGRES_PORT": "5432",
        }
        with patch.dict("os.environ", values, clear=True):
            self.assertEqual(
                Settings().database_url,
                "postgresql+psycopg://app:a%20b%40c@db:5432/loadforge",
            )


if __name__ == "__main__":
    unittest.main()
