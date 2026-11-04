import importlib.util
import unittest
from pathlib import Path

MODFILE = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "mi-sky-investing" / "scripts" / "check_chan_setup.py"
SPEC = importlib.util.spec_from_file_location("check_chan_setup", MODFILE)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def example(direction="up"):
    vals = [
        ("zone1", "down", 8, 12),
        ("zone2", "up", 7, 14),
        ("zone3", "down", 8, 12),
        ("departure", direction, 10 if direction == "up" else 7, 14 if direction == "up" else 10),
        ("retest", "down" if direction == "up" else "up", 11 if direction == "up" else 7, 13 if direction == "up" else 9),
    ]
    segments = []
    for i, (role, d, lo, hi) in enumerate(vals):
        segments.append({"role": role, "structure_level": "5F", "structure_type": mod.UNIT_TYPE,
                         "direction": d, "low": lo, "high": hi,
                         "start": f"2026-10-{i*2+1:02d}T09:30", "end": f"2026-10-{i*2+2:02d}T09:30",
                         "completed": True, "verified": True})
    return {"parent_structure_level": "30F", "sublevel_structure_level": "5F",
            "zhongshu": {"ZD": 9, "ZG": 11}, "segments": segments,
            "first_retest_verified": True}


class TestChanGeometry(unittest.TestCase):
    def test_third_buy_touch_upper_boundary_is_permitted(self):
        r = mod.evaluate(example())
        self.assertEqual(r["candidate"], "third_buy_geometry_candidate")
        self.assertEqual(r["reference_boundary"], 11)
        self.assertIn("user_attested", r["status"])

    def test_retest_falls_inside_zone_not_third_buy(self):
        d = example()
        d["segments"][4]["low"] = 10.5
        self.assertEqual(mod.evaluate(d)["candidate"], "third_buy_geometry_not_met")

    def test_third_sell_touch_lower_boundary_is_permitted(self):
        self.assertEqual(mod.evaluate(example("down"))["candidate"], "third_sell_geometry_candidate")

    def test_incomplete_segment_never_automatically_confirms(self):
        d = example()
        d["segments"][4]["verified"] = False
        r = mod.evaluate(d)
        self.assertIsNone(r["candidate"])
        self.assertEqual(r["status"], "structure_not_independently_confirmed")

    def test_bar_instead_of_complete_sublevel_structure_is_rejected(self):
        d = example()
        d["segments"][0]["structure_type"] = "single_5m_bar"
        self.assertIsNone(mod.evaluate(d)["candidate"])

    def test_inconsistent_levels_and_ranges(self):
        d = example()
        d["segments"][2]["structure_level"] = "1F"
        with self.assertRaises(ValueError):
            mod.evaluate(d)
        d = example()
        d["zhongshu"]["ZG"] = 13
        self.assertIsNone(mod.evaluate(d)["candidate"])

    def test_first_retest_must_be_attested(self):
        d = example()
        d["first_retest_verified"] = False
        self.assertIsNone(mod.evaluate(d)["candidate"])


if __name__ == "__main__":
    unittest.main()
