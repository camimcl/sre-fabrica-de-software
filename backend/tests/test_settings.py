import unittest
from unittest.mock import patch

from app.core.config import Settings


class SettingsTest(unittest.TestCase):
    def test_database_url_is_required(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL must be set"):
                Settings()

    def test_database_url_comes_from_environment(self) -> None:
        expected = "postgresql+psycopg://app:secret@db:5432/loadforge"

        with patch.dict("os.environ", {"DATABASE_URL": expected}, clear=True):
            self.assertEqual(Settings().database_url, expected)


if __name__ == "__main__":
    unittest.main()
