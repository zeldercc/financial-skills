#!/usr/bin/env python3
"""检查人工划分的已完成次级走势段，寻找类缠论中枢/三买三卖的几何候选。

不能从OHLCV自动确认笔、线段、级别。程序仅做几何校验，永远不输出正式一/二/三买卖点。
"""
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path


REQUIRED = {"end_time", "level", "direction", "low", "high", "completed"}


def read_segments(path, as_of=None):
    rows, previous, unique_level = [], None, None
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("分段CSV须包含 end_time,level,direction,low,high,completed")
        for line, raw in enumerate(reader, 2):
            try:
                when = dt.datetime.fromisoformat(raw["end_time"].strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f"第{line}行end_time无效") from exc
            if when.tzinfo is not None:
                raise ValueError("end_time应为行情交易所当地时间，禁止混用时区偏移")
            if previous is not None and when <= previous:
                raise ValueError("分段时间必须严格递增，不能重复")
            previous = when
            if as_of is not None and when > as_of:
                continue
            lvl = (raw["level"] or "").strip().lower()
            if not lvl:
                raise ValueError(f"第{line}行level为空")
            if unique_level is None:
                unique_level = lvl
            elif lvl != unique_level:
                raise ValueError("同一输入必须仅含同一声明级别的次级走势段")
            direction = (raw["direction"] or "").strip().lower()
            if direction not in ("up", "down"):
                raise ValueError(f"第{line}行direction必须up/down")
            if rows and direction == rows[-1]["direction"]:
                raise ValueError("连续两段方向相同，尚未形成合格的交替完整走势段")
            status = (raw["completed"] or "").strip().lower()
            if status not in ("true", "1", "yes"):
                raise ValueError(f"第{line}行包含未完成走势段，禁止生成确认信号")
            try:
                low, high = float(raw["low"]), float(raw["high"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"第{line}行high/low非数字") from exc
            if not math.isfinite(low) or not math.isfinite(high) or low <= 0 or high < low:
                raise ValueError(f"第{line}行价格范围无效")
            rows.append({"end_time": when.isoformat(timespec="minutes"),
                         "level":lvl, "direction":direction, "low":low, "high":high})
    return rows


def examine_windows(segments):
    centers, matches, failures = [], [], []
    if len(segments) < 3:
        return centers, matches, failures
    for i in range(len(segments) - 2):
        triple = segments[i:i+3]
        zd = max(x["low"] for x in triple)
        zg = min(x["high"] for x in triple)
        if zd > zg:
            continue
        center = {"start_segment":i,"end_segment":i+2,"ZD":round(zd,8),
                  "ZG":round(zg,8),"confirmed_at":triple[-1]["end_time"],
                  "type":"geometric_overlap_of_three_user_supplied_completed_legs"}
        centers.append(center)
        if len(segments)<i+5:
            continue
        departure, retest = segments[i+3],segments[i+4]
        direction = "third_buy" if departure["direction"]=="up" and retest["direction"]=="down" else (
                    "third_sell" if departure["direction"]=="down" and retest["direction"]=="up" else None)
        if direction is None:
            continue
        if direction=="third_buy":
            left_center = departure["high"]>zg
            held = retest["low"]>=zg
            threshold = zg
            retest_extreme = retest["low"]
        else:
            left_center = departure["low"]<zd
            held = retest["high"]<=zd
            threshold = zd
            retest_extreme = retest["high"]
        if not left_center:
            continue
        record = {"candidate_type":direction,"center_start_segment":i,
                  "center_end_segment":i+2,"departure_segment":i+3,
                  "first_retest_segment":i+4,"center_ZD":round(zd,8),
                  "center_ZG":round(zg,8),"retest_extreme":round(retest_extreme,8),
                  "boundary":round(threshold,8),
                  "retest_completed_at":retest["end_time"],
                  "geometric_fits":held,
                  "formal_chan_status":"UNVERIFIED_SEGMENTATION_AND_TREND_LEVEL",
                  "execution_status":"NOT_A_TRADE_SIGNAL"}
        (matches if held else failures).append(record)
    return centers,matches,failures


def report(segments,source,method):
    centers,matches,failures=examine_windows(segments)
    return {"source":source,"segmentation_method":method,
            "declared_leg_level":segments[0]["level"] if segments else None,
            "completed_segments":len(segments),"candidate_centers":centers,
            "geometrically_matched_templates":matches,
            "failed_retests":failures,
            "strict_chan_label_confirmed":False,
            "notes":[
                "三段连续价格区间重叠仅作人工完整次级走势段的中枢几何候选",
                "走势段身份和级别由外部人工/算法标注，程序未验证包含关系、笔、线段和走势类型",
                "上离开再首次下回试不破ZG为三买几何候选；下离开再首次上回抽不升破ZD为三卖几何候选",
                "即使满足五段价格结构，也不输出正式缠论买卖点或历史胜率",
                "不得用三根K线、MACD金叉或均线缠绕的形状冒充三段次级走势"
            ]}


def main():
    parser=argparse.ArgumentParser(description="校验人工标注的次级别走势段重叠和候选三买三卖")
    parser.add_argument("segments_csv",type=Path)
    parser.add_argument("--source",required=True,help="完整的人工分段数据来源或文件描述")
    parser.add_argument("--segment-method",required=True,help="用于标注完整同级次级走势的具体规则")
    parser.add_argument("--as-of",type=dt.datetime.fromisoformat,help="只使用这个当地时间点前已完成的分段")
    args=parser.parse_args()
    try:
        if not args.source.strip() or not args.segment_method.strip():
            raise ValueError("source和segment-method都必须明确")
        if args.as_of is not None and args.as_of.tzinfo is not None:
            raise ValueError("as-of须使用交易所当地无偏移时间")
        data=read_segments(args.segments_csv,args.as_of)
        print(json.dumps(report(data,args.source,args.segment_method),ensure_ascii=False,indent=2))
    except (OSError,ValueError) as exc:
        parser.error(str(exc))


if __name__=="__main__":
    main()
