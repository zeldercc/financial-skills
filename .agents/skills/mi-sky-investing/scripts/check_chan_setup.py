#!/usr/bin/env python3
"""Conservative geometry checker for user-verified Chan (缠论) structural units.

This program does not derive 笔, 线段, 走势类型, 中枢, or buy/sell points from raw candles.
Input JSON explicitly supplies those prerequisites; results never constitute orders.
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path

ROLES = ("zone1", "zone2", "zone3", "departure", "retest")
DIRECTIONS = {"up", "down"}
UNIT_TYPE = "completed_sublevel_movement_type"


def finite_positive(x, field):
    try:
        n = float(x)
    except (TypeError, ValueError) as exc:
        raise ValueError(field + " must be numeric") from exc
    if not math.isfinite(n) or n <= 0:
        raise ValueError(field + " must be finite and >0")
    return n


def time_value(value):
    if not isinstance(value, str):
        raise ValueError("segment timestamp must be ISO date/datetime")
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid ISO timestamp: " + value) from exc


def evaluate(data):
    """Check boundaries only, not whether the caller's structural segmentation is correct."""
    parent = data.get("parent_structure_level")
    lower = data.get("sublevel_structure_level")
    if not parent or not lower or parent == lower:
        raise ValueError("distinct parent/sublevel structure labels required")
    z = data.get("zhongshu") or {}
    zd = finite_positive(z.get("ZD"), "ZD")
    zg = finite_positive(z.get("ZG"), "ZG")
    if not zd < zg:
        raise ValueError("require lower boundary ZD < upper boundary ZG")
    segments = data.get("segments")
    if not isinstance(segments, list) or len(segments) != 5:
        raise ValueError("five segments required: 3 zone, departure, first retest")
    if [x.get("role") for x in segments] != list(ROLES):
        raise ValueError("segments must be in zone1-zone2-zone3-departure-retest order")
    previous_end = None
    problems = []
    for i, s in enumerate(segments):
        lo = finite_positive(s.get("low"), f"segment {i} low")
        hi = finite_positive(s.get("high"), f"segment {i} high")
        if lo > hi:
            raise ValueError("segment high < low")
        if s.get("direction") not in DIRECTIONS:
            raise ValueError("direction must be up or down")
        if s.get("structure_level") != lower:
            raise ValueError("all segments must be user-classified at the same sublevel")
        start = time_value(s.get("start"))
        end = time_value(s.get("end"))
        if start > end or (previous_end is not None and start < previous_end):
            raise ValueError("segment times not in chronological order")
        previous_end = end
        if s.get("structure_type") != UNIT_TYPE:
            problems.append(f"segment {i} is not a verified complete sublevel movement type")
        if s.get("completed") is not True or s.get("verified") is not True:
            problems.append(f"segment {i} is incomplete/unverified")
    if segments[0]["direction"] != segments[2]["direction"] or segments[0]["direction"] == segments[1]["direction"]:
        problems.append("zone segments do not alternate direction")
    overlap_low = max(float(s["low"]) for s in segments[:3])
    overlap_high = min(float(s["high"]) for s in segments[:3])
    if overlap_low >= overlap_high:
        problems.append("three supplied structural units have no nonzero common price overlap")
    if zd < overlap_low or zg > overlap_high:
        problems.append("provided ZD/ZG not contained in all three supplied structural price ranges")
    if data.get("first_retest_verified") is not True:
        problems.append("first retest sequence not independently verified")
    direction = segments[3]["direction"]
    if segments[4]["direction"] == direction:
        problems.append("retest direction must oppose departure")
    evidence = {
        "zone_lower_ZD": zd, "zone_upper_ZG": zg,
        "geometric_overlap_of_three_inputs": [round(overlap_low, 6), round(overlap_high, 6)],
        "departure_direction": direction,
        "first_retest_low": float(segments[4]["low"]),
        "first_retest_high": float(segments[4]["high"]),
    }
    if problems:
        return {"status": "structure_not_independently_confirmed", "candidate": None,
                "problems": problems, "evidence": evidence,
                "warning": "never infer formal Chan buy/sell from bars or MA cross alone"}
    if direction == "up":
        threshold_met = float(segments[3]["high"]) > zg and float(segments[4]["low"]) >= zg
        candidate = "third_buy_geometry_candidate" if threshold_met else "third_buy_geometry_not_met"
        anchor = zg
    else:
        threshold_met = float(segments[3]["low"]) < zd and float(segments[4]["high"]) <= zd
        candidate = "third_sell_geometry_candidate" if threshold_met else "third_sell_geometry_not_met"
        anchor = zd
    return {"status": "boundary_check_on_user_attested_structural_inputs",
            "candidate": candidate, "reference_boundary": anchor,
            "problems": [], "evidence": evidence,
            "warning": "geometric check only; independent identification of complete sublevel movements and zone required; no claim of profitable entry"}


def main():
    p = argparse.ArgumentParser(description="Verify a user-supplied Chan structure's geometric bounds; never auto trade")
    p.add_argument("file", type=Path, help="JSON of verified structural units and explicit ZD/ZG")
    args = p.parse_args()
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
        print(json.dumps(evaluate(data), ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
