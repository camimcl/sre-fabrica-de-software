import unittest

from app.modules.control.contracts import ControlInput, RulesController


class RulesControllerTest(unittest.TestCase):
    def test_reduces_concurrency_on_high_error_rate(self) -> None:
        controller = RulesController(decrease_factor=0.5)

        result = controller.decide(
            ControlInput(
                concurrency=20,
                max_concurrency=100,
                error_rate=0.20,
                error_rate_limit=0.10,
                p95_ms=400.0,
                p95_limit_ms=600.0,
                risk=None,
            )
        )

        self.assertEqual(result.action, "DECREASE")
        self.assertEqual(result.next_concurrency, 10)


if __name__ == "__main__":
    unittest.main()
