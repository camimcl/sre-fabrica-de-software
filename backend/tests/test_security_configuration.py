from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class SecurityConfigurationTest(unittest.TestCase):
    def test_database_requires_a_password_and_binds_only_to_loopback(self) -> None:
        compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("${POSTGRES_PASSWORD:?", compose)
        self.assertIn('"127.0.0.1:${POSTGRES_PORT:-5432}:5432"', compose)
        self.assertNotIn("DATABASE_URL: postgresql", compose)
        self.assertIn("POSTGRES_HOST: db", compose)

    def test_repository_configuration_has_no_credential_bearing_default_url(self) -> None:
        known_default = ":".join(("loadforge", "loadforge"))
        for relative_path in (
            ".env.example",
            "docker-compose.yml",
            "backend/alembic.ini",
            "backend/app/core/config.py",
        ):
            source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn(known_default, source, relative_path)

        alembic = (REPOSITORY_ROOT / "backend/alembic.ini").read_text(
            encoding="utf-8"
        )
        self.assertIn("sqlalchemy.url =\n", alembic)

    def test_gitignore_covers_environment_variants_and_private_keys(self) -> None:
        source = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")

        for pattern in (".env.*", "!.env.example", "*.pem", "*.key", "*.p12"):
            self.assertIn(pattern, source)


if __name__ == "__main__":
    unittest.main()
