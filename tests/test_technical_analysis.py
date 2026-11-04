"""仅用标准库验证离线指标及输入安全边界。"""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents/skills/mi-sky-investing/scripts/analyze_ohlcv.py"
spec = importlib.util.spec_from_file_location("analyze_ohlcv", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def args(**overrides):
    params = dict(account_equity=None, risk_percent=None, entry_price=None,
                  stop_price=None, lot_size=100, breakout_lookback=20,
                  high_rvol=None, low_rvol=None, timeframe="daily",
                  price_unit="CNY", volume_unit="shares")
    params.update(overrides)
    return SimpleNamespace(**params)


def sample_bars(n=61):
    from datetime import date, timedelta
    start = date(2026, 1, 1)
    bars = []
    for i in range(n):
        price = 10.0 if i < n-1 else 30.0
        bars.append({"date": (start + timedelta(days=i)).isoformat(),
                     "open": price, "high": price+0.5, "low": price-0.5,
                     "close": price, "volume": 1000.0 if i < n-1 else 5000.0})
    return bars


class TechnicalAnalysisTest(unittest.TestCase):
    def test_ma_cross_and_volume(self):
        x = mod.analyze(sample_bars(), args())
        self.assertEqual(x["signals"]["ma5_ma20_cross"], "golden")
        self.assertEqual(x["volume"]["rvol20_excluding_current"], 5.0)
        self.assertEqual(x["structure"]["candidate_close_above_previous_high"], True)
        self.assertIsNone(x["structure"]["retest_confirmed"])
        self.assertEqual(x["volume"]["classification"], "between_thresholds_or_no_thresholds")
        self.assertIsNone(x["moving_average"]["250"]["value"])

    def test_threshold_is_user_parameter(self):
        x = mod.analyze(sample_bars(), args(high_rvol=2.0))
        self.assertEqual(x["volume"]["classification"], "above_user_high_threshold")
        self.assertEqual(x["volume"]["user_high_rvol"], 2.0)

    def test_insufficient_series_never_invents_values(self):
        x = mod.analyze(sample_bars(12), args())
        self.assertIsNone(x["moving_average"]["20"]["value"])
        self.assertIsNone(x["volume"]["rvol20_excluding_current"])
        self.assertIsNone(x["signals"]["macd_12_26_9"])
        self.assertEqual(x["signals"]["ma5_ma20_cross"], "unknown_insufficient_history")

    def test_risk_based_position_cap(self):
        x = mod.analyze(sample_bars(), args(account_equity=100000,
                                              risk_percent=1.0,
                                              entry_price=20.0,
                                              stop_price=18.0, lot_size=100))
        self.assertEqual(x["position_sizing"]["quantity_upper_bound_before_costs"], 500)

    def test_risk_inputs_are_not_silently_filled(self):
        with self.assertRaises(ValueError):
            mod.analyze(sample_bars(), args(account_equity=100000))

    def test_csv_rejects_invalid_ohlc_and_dates(self):
        with tempfile.TemporaryDirectory() as temp:
            name = Path(temp) / "bars.csv"
            with name.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
                writer.writeheader()
                writer.writerow({"date":"2026-01-01","open":10,"high":11,"low":9,"close":10,"volume":1000})
                writer.writerow({"date":"2026-01-01","open":10,"high":11,"low":9,"close":10,"volume":2000})
            with self.assertRaisesRegex(ValueError, "日期"):
                mod.load_csv(name)
            with name.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["date","open","high","low","close","volume"])
                writer.writeheader()
                writer.writerow({"date":"2026-01-01","open":10,"high":9,"low":8,"close":10,"volume":1000})
                writer.writerow({"date":"2026-01-02","open":10,"high":11,"low":9,"close":10,"volume":2000})
            with self.assertRaisesRegex(ValueError, "OHLC"):
                mod.load_csv(name)


if __name__ == "__main__":
    unittest.main()
