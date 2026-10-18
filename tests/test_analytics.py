import json
from pathlib import Path
import subprocess
import sys
import unittest

from portfolio_risk_analytics import analyze_portfolio


ROOT = Path(__file__).resolve().parents[1]


class PortfolioAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = json.loads((ROOT / "examples/sample_portfolio.json").read_text())

    def test_sample_metrics_and_risk_contributions(self):
        result = analyze_portfolio(self.sample)
        self.assertEqual(result["metadata"]["return_observations"], 11)
        self.assertGreater(result["portfolio"]["total_return"], 0)
        self.assertGreater(result["portfolio"]["annualized_volatility"], 0)
        self.assertLessEqual(result["portfolio"]["maximum_drawdown"], 0)
        shares = [item["risk_share"] for item in result["asset_risk_contributions"]]
        self.assertAlmostEqual(sum(shares), 1.0, places=10)
        contributions = [
            item["annualized_volatility_contribution"]
            for item in result["asset_risk_contributions"]
        ]
        self.assertAlmostEqual(
            sum(contributions), result["portfolio"]["annualized_volatility"], places=10
        )
        self.assertEqual(len(result["covariance_annualized"]["matrix"]), 3)

    def test_rejects_weights_that_do_not_sum_to_one(self):
        invalid = json.loads(json.dumps(self.sample))
        invalid["assets"][0]["weight"] = 0.4
        with self.assertRaisesRegex(ValueError, "sum to 1"):
            analyze_portfolio(invalid)

    def test_rejects_unaligned_dates(self):
        invalid = json.loads(json.dumps(self.sample))
        invalid["assets"][1]["dates"][1] = "2025-01-04"
        with self.assertRaisesRegex(ValueError, "identical dates"):
            analyze_portfolio(invalid)

    def test_cli_outputs_json(self):
        process = subprocess.run(
            [sys.executable, "-m", "portfolio_risk_analytics", str(ROOT / "examples/sample_portfolio.json")],
            cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
            check=True, capture_output=True, text=True,
        )
        self.assertIn("annualized_volatility", json.loads(process.stdout)["portfolio"])


if __name__ == "__main__":
    unittest.main()
