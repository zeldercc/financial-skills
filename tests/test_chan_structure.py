"""真实缠论级别需由外部确认。此测试只验证保守的几何模板和数据边界。"""
import csv
import datetime as dt
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT / ".agents/skills/mi-sky-investing/scripts/chan_segment_check.py"
spec=importlib.util.spec_from_file_location("chan_segment_check",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def leg(t,d,low,high,level="1m"):
    return {"end_time":t,"direction":d,"low":low,"high":high,"level":level}


def buy_segments(retest_low=13.1):
    return [
        leg("2026-11-04T09:50","down",10,13),
        leg("2026-11-04T10:10","up",11,14),
        leg("2026-11-04T10:30","down",11.5,13.5),
        leg("2026-11-04T11:00","up",12,16),
        leg("2026-11-04T11:25","down",retest_low,15)
    ]


def sell_segments(retest_high=12.4):
    return [
        leg("2026-11-04T09:50","up",12,15),
        leg("2026-11-04T10:10","down",11,14),
        leg("2026-11-04T10:30","up",12.5,14.5),
        leg("2026-11-04T11:00","down",10,13),
        leg("2026-11-04T11:25","up",11,retest_high)
    ]


def write_segments(path,items,unfinished_at=None):
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=[
            "end_time","level","direction","low","high","completed"])
        writer.writeheader()
        for i,x in enumerate(items):
            writer.writerow({**x,"completed":"false" if i==unfinished_at else "true"})


class ChanStructureTest(unittest.TestCase):
    def test_geometric_third_buy_is_not_formal_confirmation(self):
        out=mod.report(buy_segments(),"synthetic test","manual, not independently audited")
        self.assertEqual(len(out["geometrically_matched_templates"]),1)
        c=out["geometrically_matched_templates"][0]
        self.assertEqual(c["candidate_type"],"third_buy")
        self.assertEqual(c["center_ZD"],11.5)
        self.assertEqual(c["center_ZG"],13)
        self.assertFalse(out["strict_chan_label_confirmed"])
        self.assertEqual(c["formal_chan_status"],"UNVERIFIED_SEGMENTATION_AND_TREND_LEVEL")

    def test_geometric_third_sell(self):
        out=mod.report(sell_segments(),"test","manual")
        self.assertEqual(len(out["geometrically_matched_templates"]),1)
        c=out["geometrically_matched_templates"][0]
        self.assertEqual(c["candidate_type"],"third_sell")
        self.assertEqual(c["center_ZD"],12.5)
        self.assertEqual(c["center_ZG"],14)

    def test_retest_enters_center_so_no_third_buy(self):
        out=mod.report(buy_segments(retest_low=12.8),"test","manual")
        self.assertEqual(len(out["geometrically_matched_templates"]),0)
        self.assertEqual(len(out["failed_retests"]),1)

    def test_three_overlapping_price_ranges_without_retest_are_not_third_buy(self):
        out=mod.report(buy_segments()[:3],"test","manual")
        self.assertTrue(out["candidate_centers"])
        self.assertEqual(len(out["geometrically_matched_templates"]),0)

    def test_reject_unfinished_or_mixed_level(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"segments.csv"
            write_segments(path,buy_segments(),unfinished_at=4)
            with self.assertRaisesRegex(ValueError,"未完成"):
                mod.read_segments(path)
            mixed=buy_segments()
            mixed[2]["level"]="5m"
            write_segments(path,mixed)
            with self.assertRaisesRegex(ValueError,"同一声明级别"):
                mod.read_segments(path)

    def test_as_of_never_sees_future_retest(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"segments.csv"
            write_segments(path,buy_segments())
            asof=dt.datetime(2026,11,4,11,0)
            past=mod.read_segments(path,asof)
            self.assertEqual(len(past),4)
            centers,matches,failures=mod.examine_windows(past)
            self.assertEqual(len(matches),0)
            self.assertEqual(len(failures),0)

    def test_bad_direction_or_time_order_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"segments.csv"
            parts=buy_segments()
            parts[1]["direction"]="down"
            write_segments(path,parts)
            with self.assertRaisesRegex(ValueError,"方向相同"):
                mod.read_segments(path)
            parts=buy_segments()
            parts[1]["end_time"]=parts[0]["end_time"]
            write_segments(path,parts)
            with self.assertRaisesRegex(ValueError,"严格递增"):
                mod.read_segments(path)


if __name__=="__main__":
    unittest.main()
