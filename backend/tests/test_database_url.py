import unittest
from unittest.mock import patch

from app.core.database_url import postgresql_url_from_environment


class DatabaseUrlTest(unittest.TestCase):
    def test_components_are_encoded_when_building_the_url(self) -> None:
        environment = {
            "POSTGRES_DB": "loadforge",
            "POSTGRES_USER": "loadforge",
            "POSTGRES_PASSWORD": "strong@pass:/#%",
            "POSTGRES_HOST": "db",
            "POSTGRES_PORT": "5432",
        }

        with patch.dict("os.environ", environment, clear=True):
            result = postgresql_url_from_environment()

        self.assertIn("strong%40pass%3A%2F%23%25", result)
        self.assertNotIn("strong@pass:/#%", result)

    def test_all_components_are_required(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "POSTGRES_DB"):
                postgresql_url_from_environment()


if __name__ == "__main__":
    unittest.main()
