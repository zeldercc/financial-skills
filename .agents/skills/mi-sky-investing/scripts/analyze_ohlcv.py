#!/usr/bin/env python3
"""基于已有 OHLCV 数据的离线技术分析。仅提供候选信号，不联网或下单。"""
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path


def finite_number(value, name, line):
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"第{line}行 {name} 非数字") from exc
    if not math.isfinite(n):
        raise ValueError(f"第{line}行 {name} 非有限数值")
    return n


def load_csv(path, as_of=None):
    rows = []
    last_date = None
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        needed = {"date", "open", "high", "low", "close", "volume"}
        if not reader.fieldnames or not needed.issubset(reader.fieldnames):
            raise ValueError("CSV须包含 date,open,high,low,close,volume 字段")
        for lineno, record in enumerate(reader, 2):
            date = dt.date.fromisoformat(record["date"].strip())
            if last_date is not None and date <= last_date:
                raise ValueError(f"第{lineno}行日期非严格升序或重复")
            last_date = date
            if as_of is not None and date > as_of:
                continue
            bar = {k: finite_number(record[k], k, lineno)
                   for k in ("open", "high", "low", "close", "volume")}
            if min(bar["open"], bar["high"], bar["low"], bar["close"]) <= 0:
                raise ValueError(f"第{lineno}行价格须为正数")
            if bar["volume"] < 0:
                raise ValueError(f"第{lineno}行成交量不能为负")
            if bar["high"] < max(bar["open"], bar["close"], bar["low"]) or \
               bar["low"] > min(bar["open"], bar["close"], bar["high"]):
                raise ValueError(f"第{lineno}行OHLC关系不合法")
            rows.append({"date": str(date), **bar})
    if len(rows) < 2:
        raise ValueError("截止观察日的有效K线至少需要两根")
    return rows


def avg(values, n, end=None):
    if end is None:
        end = len(values)
    return sum(values[end-n:end]) / n if end >= n else None


def r4(value):
    return round(value, 4) if value is not None else None


def ema(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def macd(values):
    if len(values) < 35:
        return None
    e12, e26 = ema(values, 12), ema(values, 26)
    dif = [a - b for a, b in zip(e12, e26)]
    dea = ema(dif, 9)
    return {"dif": r4(dif[-1]), "dea": r4(dea[-1]),
            "histogram": r4(2 * (dif[-1] - dea[-1])),
            "cross": ("golden" if dif[-2] <= dea[-2] and dif[-1] > dea[-1] else
                      "death" if dif[-2] >= dea[-2] and dif[-1] < dea[-1] else "none")}


def rsi14(values):
    period = 14
    if len(values) < period + 1:
        return None
    changes = [values[i] - values[i-1] for i in range(1, len(values))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    g = sum(gains[:period]) / period
    l = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        g = (g * (period - 1) + gain) / period
        l = (l * (period - 1) + loss) / period
    if l == 0:
        return 100.0 if g > 0 else 50.0
    return r4(100 - 100 / (1 + g / l))


def risk_quantity(args):
    fields = (args.account_equity, args.risk_percent, args.entry_price, args.stop_price)
    if all(x is None for x in fields):
        return None
    if any(x is None for x in fields):
        raise ValueError("计算仓位需同时提供 --account-equity --risk-percent --entry-price --stop-price")
    if args.account_equity <= 0 or not 0 < args.risk_percent <= 100:
        raise ValueError("净资产须为正，风险预算比例须在0~100之间")
    if args.stop_price <= 0 or args.entry_price <= args.stop_price:
        raise ValueError("仅支持做多，入场价须大于正数止损价")
    if args.lot_size <= 0:
        raise ValueError("lot-size须大于零")
    budget = args.account_equity * args.risk_percent / 100
    qty_risk = int((budget / (args.entry_price - args.stop_price)) // args.lot_size) * args.lot_size
    qty_cash = int((args.account_equity / args.entry_price) // args.lot_size) * args.lot_size
    qty = min(qty_risk, qty_cash)
    return {"account_equity": args.account_equity, "risk_budget_amount": r4(budget),
            "entry_price": args.entry_price, "stop_price": args.stop_price,
            "lot_size": args.lot_size, "quantity_upper_bound_before_costs": qty,
            "notes": "止损不保证成交；跳空、滑点、手续费、集中度和实际可用资金仍需另行限制"}


def analyze(bars, args):
    close = [r["close"] for r in bars]
    high = [r["high"] for r in bars]
    low = [r["low"] for r in bars]
    volume = [r["volume"] for r in bars]
    current = bars[-1]
    moving = {}
    for period in (5, 10, 20, 60, 120, 250):
        curr = avg(close, period)
        prev = avg(close, period, len(close) - 1)
        moving[str(period)] = {
            "value": r4(curr),
            "previous": r4(prev),
            "one_bar_slope_percent": r4(100 * (curr / prev - 1)) if curr is not None and prev else None,
            "price_above": current["close"] > curr if curr is not None else None
        }
    vma = {str(n): r4(avg(volume, n)) for n in (5, 20)}
    prev_vma20 = avg(volume, 20, len(volume) - 1)
    rvol = volume[-1] / prev_vma20 if prev_vma20 else None
    volume_state = "unclassified_threshold_not_supplied"
    if rvol is not None:
        if args.high_rvol is not None and rvol >= args.high_rvol:
            volume_state = "above_user_high_threshold"
        elif args.low_rvol is not None and rvol <= args.low_rvol:
            volume_state = "below_user_low_threshold"
        else:
            volume_state = "between_thresholds_or_no_thresholds"
    m5, m20, m60 = (moving[str(n)] for n in (5, 20, 60))
    cross = "unknown_insufficient_history"
    if m5["previous"] is not None and m20["previous"] is not None:
        cross = ("golden" if m5["previous"] <= m20["previous"] and m5["value"] > m20["value"] else
                 "death" if m5["previous"] >= m20["previous"] and m5["value"] < m20["value"] else "none")
    if all(x["value"] is not None for x in (m5, m20, m60)):
        trend = ("ma_bullish" if current["close"] > m60["value"] and m5["value"] > m20["value"] > m60["value"] else
                 "ma_bearish" if current["close"] < m60["value"] and m5["value"] < m20["value"] < m60["value"] else
                 "mixed_or_range")
    else:
        trend = "unknown_insufficient_history"
    lookback = args.breakout_lookback
    upper = max(high[-lookback-1:-1]) if len(bars) > lookback else None
    lower = min(low[-lookback-1:-1]) if len(bars) > lookback else None
    warnings = [
        "数据来自用户CSV，未验证交易所数据及复权/停牌/盘中完整性",
        "技术信号仅用于观察；突破后是否站稳、回踩确认需等待未来已完成K线",
        "交易信号阈值如有提供来自用户参数，不是作者统一标准"
    ]
    if len(bars) < 251:
        warnings.append("不足251根K线，MA250的上期及斜率可能无法计算")
    if len(bars) < 60:
        warnings.append("样本较短，MACD指数初始化存在较大热启动偏差")
    if args.timeframe != "daily":
        warnings.append("用户提供的周/月K必须是已完成周期；工具不推断最新周期是否收完")
    return {
        "as_of": current["date"], "timeframe": args.timeframe, "n_bars": len(bars),
        "data_unit": {"price": args.price_unit, "volume": args.volume_unit},
        "last_close": current["close"], "previous_close": close[-2],
        "day_return_percent": r4(100 * (close[-1] / close[-2] - 1)),
        "moving_average": moving, "volume": {
            "current": current["volume"], "vma": vma,
            "prior_20_average": r4(prev_vma20),
            "rvol20_excluding_current": r4(rvol),
            "volume_vs_previous_ratio": r4(volume[-1] / volume[-2]) if volume[-2] else None,
            "classification": volume_state,
            "user_high_rvol": args.high_rvol, "user_low_rvol": args.low_rvol
        },
        "structure": {
            "previous_high": r4(upper), "previous_low": r4(lower),
            "lookback_completed_bars": lookback,
            "candidate_close_above_previous_high": current["close"] > upper if upper else None,
            "candidate_close_below_previous_low": current["close"] < lower if lower else None,
            "retest_confirmed": None
        },
        "signals": {"ma5_ma20_cross": cross, "ma_alignment": trend,
                    "macd_12_26_9": macd(close), "rsi14": rsi14(close)},
        "position_sizing": risk_quantity(args), "warnings": warnings
    }


def positive_float(value):
    f = float(value)
    if not math.isfinite(f) or f <= 0:
        raise argparse.ArgumentTypeError("请输入正有限数")
    return f


def main():
    p = argparse.ArgumentParser(description="读取CSV OHLCV，输出可溯源的技术观察JSON；不联网、不下单")
    p.add_argument("csv_file", type=Path)
    p.add_argument("--timeframe", choices=("daily", "weekly", "monthly"), default="daily")
    p.add_argument("--as-of", type=dt.date.fromisoformat)
    p.add_argument("--breakout-lookback", type=int, default=20)
    p.add_argument("--high-rvol", type=positive_float, help="自定义放量比较阈值，非作者固定参数")
    p.add_argument("--low-rvol", type=positive_float, help="自定义缩量比较阈值，非作者固定参数")
    p.add_argument("--price-unit", default="CNY")
    p.add_argument("--volume-unit", default="shares")
    p.add_argument("--account-equity", type=positive_float)
    p.add_argument("--risk-percent", type=positive_float)
    p.add_argument("--entry-price", type=positive_float)
    p.add_argument("--stop-price", type=positive_float)
    p.add_argument("--lot-size", type=int, default=100)
    args = p.parse_args()
    try:
        if not 2 <= args.breakout_lookback <= 1000:
            raise ValueError("breakout-lookback须在2到1000之间")
        if args.low_rvol is not None and args.high_rvol is not None and args.low_rvol >= args.high_rvol:
            raise ValueError("低量阈值须小于高量阈值")
        result = analyze(load_csv(args.csv_file, args.as_of), args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
