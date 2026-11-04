"""多周期5分钟K线聚合、均线离散度、支撑压力与筹码数据分离测试。"""
import csv
import datetime as dt
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/".agents/skills/mi-sky-investing/scripts/analyze_multitimeframe.py"
spec=importlib.util.spec_from_file_location("mi_multitimeframe",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample_bars(days=6, omit=None):
    bars=[]
    for d in range(days):
        date=dt.date(2026,10,26)+dt.timedelta(days=d)
        for session,hour,minute in (("morning",9,30),("afternoon",13,0)):
            origin=dt.datetime.combine(date,dt.time(hour,minute))
            for slot in range(24):
                if omit==(d,session,slot):
                    continue
                t=origin+dt.timedelta(minutes=5*slot)
                price=10.0+d*0.2+(slot/200)
                bars.append({"time":t.isoformat(timespec="minutes"),"date":str(date),
                             "session":session,"slot":slot,
                             "open":price,"high":price+.1,"low":price-.1,
                             "close":price+.05,"volume":1000.0})
    return bars


def args(**kwargs):
    defaults={"ma_convergence_pct":None,"zone_tolerance_pct":None,
              "profile_bars":240,"profile_bins":40,"chip_profile":None,
              "chip_asof":None,"chip_model":None}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class MultiTimeframeTest(unittest.TestCase):
    def test_half_day_aggregation_no_lunch_crossing(self):
        tf,quality=mod.make_timeframes(sample_bars(days=2))
        self.assertEqual(len(tf["5m"]),96)
        self.assertEqual(len(tf["30m"]),16)
        self.assertEqual(len(tf["60m"]),8)
        self.assertEqual(len(tf["120m"]),4)
        self.assertEqual(len(tf["daily"]),2)
        self.assertEqual(tf["120m"][0]["time"],"2026-10-26T09:30")
        self.assertEqual(tf["120m"][1]["time"],"2026-10-26T13:00")
        self.assertEqual(tf["120m"][2]["time"],"2026-10-27T09:30")
        self.assertEqual(len(quality["incomplete_days"]),0)

    def test_partial_day_not_confirmed_as_daily_or_higher(self):
        tf,quality=mod.make_timeframes(sample_bars(days=2,omit=(1,"afternoon",17)))
        self.assertEqual(len(tf["5m"]),95)
        self.assertEqual(len(tf["daily"]),1)
        self.assertEqual(len(tf["120m"]),2)
        self.assertEqual(quality["incomplete_days"][0]["missing"],1)

    def test_current_week_month_not_marked_finished(self):
        tf,_=mod.make_timeframes(sample_bars(days=6))
        self.assertEqual(len(tf["daily"]),6)
        self.assertEqual(len(tf["weekly"]),1)  # 10/26-11/01与11/02-11/01假设跨周，见下行
        self.assertEqual(len(tf["monthly"]),0)

    def test_ma_convergence_needs_user_threshold(self):
        data=[{"time":f"t{i}","open":10,"high":10.1,"low":9.9,"close":10,"volume":100} for i in range(66)]
        a=mod.technical(data)
        self.assertEqual(a["ma_convergence"]["dispersion_pct"],0.0)
        self.assertIsNone(a["ma_convergence"]["within_user_threshold"])
        b=mod.technical(data,0.5)
        self.assertEqual(b["ma_convergence"]["within_user_threshold"],True)

    def test_profile_and_chip_are_distinct(self):
        data=sample_bars(days=2)
        va=mod.volume_profile(data,48,10)
        self.assertIn("not_actual_holding_cost",va["method"])
        self.assertIn("POC",va)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"chip.csv"
            p.write_text("price,weight\n12,10\n12.5,70\n13,20\n",encoding="utf-8")
            chip=mod.load_chip_csv(p,"2026-10-27","ExampleBroker test model")
            self.assertEqual(chip["POC"],12.5)
            self.assertEqual(chip["kind"],"external_estimated_holding_cost_model")
            with self.assertRaises(ValueError):
                mod.load_chip_csv(p,None,"missing_date")

    def test_pivots_only_confirm_after_two_right_bars(self):
        bars=[]
        for i,x in enumerate([10,11,14,12,11,13]):
            bars.append({"time":str(i),"high":x,"low":x-1})
        ev=mod.pivots(bars)
        highs=[e for e in ev if e["type"]=="swing_high"]
        self.assertEqual(len(highs),1)
        self.assertEqual(highs[0]["price"],14)
        self.assertEqual(highs[0]["confirmed_at"],"4")

    def test_complete_multi_timeframe_result_no_chip_fabrication(self):
        x=mod.analyze(sample_bars(days=2),args())
        self.assertIsNone(x["estimated_chip_cost_profile"])
        self.assertIsNotNone(x["executed_volume_profile_approx"])
        self.assertEqual(x["cross_timeframe_levels"]["status"],"no_user_tolerance")
        self.assertEqual(set(x["timeframes"]),set(mod.ALL_TIMEFRAMES))


if __name__=="__main__":
    unittest.main()
