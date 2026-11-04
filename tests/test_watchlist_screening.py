"""Watchlist screener uses only submitted CSV universe and reports missing data."""
import importlib.util
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/mi-sky-investing/scripts/screen_watchlist.py"
spec = importlib.util.spec_from_file_location("mi_watchlist", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_csv(path, count=141):
    import csv
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for n in range(count):
            p = 8 + n / 10
            writer.writerow([(date(2026, 1, 1) + timedelta(days=n)).isoformat(),
                             p, p+0.25, p-0.25, p, 1000 + 10*n])


class WatchlistTest(unittest.TestCase):
    def test_full_filter_is_observation_not_trading(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "ABC.csv"
            make_csv(file)
            result = mod.screen_directory(Path(td))
            self.assertTrue(result["not_trade_signal"])
            self.assertIsNone(result["rps"])
            self.assertEqual(len(result["records"]), 1)
            item = result["records"][0]
            self.assertEqual(item["ticker_from_filename"], "ABC")
            self.assertTrue(item["checks"]["ma20_gt_ma60_gt_ma120"])
            self.assertTrue(item["checks"]["vma5_gt_vma10"])
            self.assertEqual(item["technical_observation"], "strong_filter_components_met")

    def test_history_short_never_invents_ma120(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "SHORT.csv"
            make_csv(file, count=15)
            result = mod.screen_directory(Path(td))
            item = result["records"][0]
            self.assertIsNone(item["MA120"])
            self.assertIn("ma20_gt_ma60_gt_ma120", item["missing"])
            self.assertEqual(item["technical_observation"], "insufficient_data")

    def test_staleness_is_visible(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "ABC.csv"
            make_csv(file)
            asof = date(2026, 7, 1)
            result = mod.screen_directory(Path(td), as_of=asof, max_staleness=7)
            self.assertTrue(result["records"][0]["stale"])


if __name__ == "__main__":
    unittest.main()
