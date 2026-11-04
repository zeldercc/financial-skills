#!/usr/bin/env python3
"""离线股票池技术筛选。输入目录中每只股票一份OHLCV CSV；只观察，不出买卖指令。"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mi_ohlcv", HERE / "analyze_ohlcv.py")
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


def classify(bars, period=20):
    price = [r["close"] for r in bars]
    volume = [r["volume"] for r in bars]
    out = {"last_date": bars[-1]["date"], "last_close": price[-1],
           "sample_bars": len(price), "checks": {}, "missing": []}
    for n in (20, 60, 120):
        out[f"MA{n}"] = calc.r4(calc.avg(price, n))
    for n in (5, 10):
        out[f"VMA{n}"] = calc.r4(calc.avg(volume, n))
    ma = (out["MA20"], out["MA60"], out["MA120"])
    checks = out["checks"]
    checks["ma20_gt_ma60_gt_ma120"] = ma[0] > ma[1] > ma[2] if all(x is not None for x in ma) else None
    checks["close_above_ma20"] = price[-1] > ma[0] if ma[0] is not None else None
    checks["vma5_gt_vma10"] = out["VMA5"] > out["VMA10"] if out["VMA10"] is not None else None
    out["rsi14"] = calc.rsi14(price)
    checks["rsi_above_50"] = out["rsi14"] > 50 if out["rsi14"] is not None else None
    out["macd"] = calc.macd(price)
    checks["dif_above_zero"] = out["macd"]["dif"] > 0 if out["macd"] else None
    prior_volume_20 = calc.avg(volume, period, len(volume)-1)
    out["rvol20_excluding_current"] = calc.r4(volume[-1] / prior_volume_20) if prior_volume_20 else None
    out["return_20_bars"] = calc.r4(100 * (price[-1]/price[-21]-1)) if len(price)>=21 else None
    out["missing"] = [k for k, v in checks.items() if v is None]
    out["technical_observation"] = (
        "strong_filter_components_met" if all(v is True for v in checks.values()) else
        "strong_filter_components_not_met" if all(v is not None for v in checks.values()) else
        "insufficient_data"
    )
    return out


def screen_directory(folder, as_of=None, max_staleness=None):
    records, errors = [], []
    files = sorted(folder.glob("*.csv"))
    if not files:
        raise ValueError("目录中没有CSV文件")
    for path in files:
        try:
            rows = calc.load_csv(path, as_of=as_of)
            record = classify(rows)
            record["ticker_from_filename"] = path.stem
            if as_of is not None and max_staleness is not None:
                import datetime as dt
                last = dt.date.fromisoformat(record["last_date"])
                record["stale_calendar_days"] = (as_of - last).days
                record["stale"] = record["stale_calendar_days"] > max_staleness
            records.append(record)
        except (ValueError, OSError) as exc:
            errors.append({"file": path.name, "error": str(exc)})
    return {"universe": "user_supplied_csv_files_only",
            "rps": None,
            "rps_reason": "无完整可比股票池、明确窗口和指数成分，不能计算作者同口径RPS",
            "does_not_predict_success": True, "not_trade_signal": True,
            "records": records, "errors": errors,
            "notes": [
                "过滤条件来自T00第196条的历史文章，非普适有效策略",
                "不能由单一股票走势推断机构或主力真实交易意图",
                "财务基本面、行业景气、估值与交易可行性尚未筛选",
                "历史数据复权、成分样本与停复牌应在外部核实",
                "不能把输入目录的股票相对排名称为全市场RPS"
            ]}


def main():
    p = argparse.ArgumentParser(description="批量筛选用户提供的股票OHLCV CSV")
    p.add_argument("folder", type=Path)
    p.add_argument("--as-of", type=__import__("datetime").date.fromisoformat)
    p.add_argument("--max-staleness-calendar-days", type=int, default=7)
    args = p.parse_args()
    if not args.folder.is_dir():
        p.error("请提供包含多个CSV的目录")
    if args.max_staleness_calendar_days < 0:
        p.error("max-staleness-calendar-days须非负")
    try:
        result = screen_directory(args.folder, args.as_of, args.max_staleness_calendar_days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
