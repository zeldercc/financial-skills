#!/usr/bin/env python3
"""基于A股已完成5分钟K线的多周期量价/均线/支撑观察，不抓行情也不下单。

输入CSV列: timestamp,open,high,low,close,volume。
timestamp为Asia/Shanghai本地K线开始时刻；需要标记为已完成的K线。
筹码成本分布须另外提供包含price,weight的CSV及来源信息，不能从OHLCV伪造。
"""
import argparse
import csv
import datetime as dt
import json
import math
from collections import defaultdict
from pathlib import Path


MORNING = dt.time(9, 30)
AFTERNOON = dt.time(13, 0)
ALL_TIMEFRAMES = ("monthly", "weekly", "daily", "120m", "60m", "30m", "5m")


def finite(value, field, line):
    try:
        n = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"第{line}行{field}无法解析") from exc
    if not math.isfinite(n):
        raise ValueError(f"第{line}行{field}不是有限数值")
    return n


def session_slot(moment):
    start = dt.datetime.combine(moment.date(), MORNING)
    afternoon = dt.datetime.combine(moment.date(), AFTERNOON)
    if start <= moment < start + dt.timedelta(minutes=120):
        return "morning", int((moment-start).total_seconds() // 300)
    if afternoon <= moment < afternoon + dt.timedelta(minutes=120):
        return "afternoon", int((moment-afternoon).total_seconds() // 300)
    raise ValueError(f"非A股正常竞价5分钟K线起始时间: {moment.isoformat()}")


def load_5m(path, as_of=None):
    rows, previous = [], None
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not {"timestamp", "open", "high", "low", "close", "volume"}.issubset(reader.fieldnames):
            raise ValueError("CSV必须包含timestamp,open,high,low,close,volume列")
        for line, raw in enumerate(reader, 2):
            try:
                moment = dt.datetime.fromisoformat(raw["timestamp"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"第{line}行timestamp无效") from exc
            if moment.tzinfo is not None:
                raise ValueError("时间须为Asia/Shanghai本地无时区偏移格式，避免静默时区变换")
            if moment.weekday() >= 5:
                raise ValueError(f"第{line}行为非周一至周五的日期，无法作为A股正常交易日")
            if previous is not None and moment <= previous:
                raise ValueError("K线起始时间须严格递增且不能重复")
            previous = moment
            if as_of is not None and moment > as_of:
                continue
            session, slot = session_slot(moment)
            if moment.second or moment.microsecond or not 0 <= slot < 24:
                raise ValueError(f"第{line}行非严格5分钟起始时刻")
            origin = dt.datetime.combine(moment.date(), MORNING if session == "morning" else AFTERNOON)
            if moment != origin + dt.timedelta(minutes=5 * slot):
                raise ValueError(f"第{line}行非5分钟整点")
            bar = {field:finite(raw[field], field, line) for field in ("open","high","low","close","volume")}
            if min(bar["open"], bar["high"], bar["low"], bar["close"]) <= 0 or bar["volume"] < 0:
                raise ValueError(f"第{line}行价格必须为正，成交量不能为负")
            if bar["high"] < max(bar["open"],bar["close"],bar["low"]) or bar["low"] > min(bar["open"],bar["close"],bar["high"]):
                raise ValueError(f"第{line}行OHLC无效")
            rows.append({"time":moment.isoformat(timespec="minutes"),"date":moment.date().isoformat(),
                         "session":session,"slot":slot,**bar})
    if not rows:
        raise ValueError("没有可用的已完成5分钟K线")
    return rows


def aggregate(items, label):
    return {"time":label, "open":items[0]["open"], "high":max(b["high"] for b in items),
            "low":min(b["low"] for b in items), "close":items[-1]["close"],
            "volume":sum(b["volume"] for b in items)}


def make_timeframes(bars):
    bydate = defaultdict(list)
    for bar in bars:
        bydate[bar["date"]].append(bar)
    completed_days, incomplete = [], []
    groups = {"5m":[{k:bar[k] for k in ("time","open","high","low","close","volume")} for bar in bars],
              "30m":[], "60m":[], "120m":[], "daily":[], "weekly":[], "monthly":[]}
    for date, day in sorted(bydate.items()):
        actual = {(b["session"],b["slot"]) for b in day}
        expected = {(session,slot) for session in ("morning","afternoon") for slot in range(24)}
        if actual != expected or len(day) != 48:
            incomplete.append({"date":date,"bars_found":len(day),"missing":len(expected - actual)})
            continue
        completed_days.append(date)
        groups["daily"].append(aggregate(day,date))
        for duration, count in ((30,6),(60,12),(120,24)):
            for session in ("morning","afternoon"):
                session_bars = sorted((b for b in day if b["session"] == session),key=lambda x:x["slot"])
                for pos in range(0,24,count):
                    batch = session_bars[pos:pos+count]
                    groups[f"{duration}m"].append(aggregate(batch,batch[0]["time"]))
    # Previous weekly/monthly groups only: without a later observed period,
    # current week/month cannot be proved closed based on this dataset alone.
    for name, key in (
        ("weekly",lambda x:dt.date.fromisoformat(x["time"]).isocalendar()[:2]),
        ("monthly",lambda x:x["time"][:7]),
    ):
        slices = defaultdict(list)
        for bar in groups["daily"]:
            slices[key(bar)].append(bar)
        keys = sorted(slices)
        for period in keys[:-1]:
            group = slices[period]
            label = str(period[0]) + "-W" + str(period[1]).zfill(2) if name=="weekly" else period
            groups[name].append(aggregate(group,label))
    return groups,{"completed_days":len(completed_days),"incomplete_days":incomplete,
                   "weekly_monthly_rule":"只确认出现下一周/月之后的先前周期；当前周期不作为已收盘"}


def sma(values, n, end=None):
    end = len(values) if end is None else end
    return sum(values[end-n:end]) / n if end >= n else None


def round6(x):
    return round(x,6) if x is not None else None


def macd(values):
    if len(values) < 35:
        return None
    def ema(seq, n):
        alpha=2/(n+1)
        out=[seq[0]]
        for x in seq[1:]:
            out.append(alpha*x+(1-alpha)*out[-1])
        return out
    a,b=ema(values,12),ema(values,26)
    dif=[x-y for x,y in zip(a,b)]
    signal=ema(dif,9)
    return {"dif":round6(dif[-1]),"dea":round6(signal[-1]),
            "histogram":round6(2*(dif[-1]-signal[-1]))}



def rsi14(values):
    if len(values) < 15:
        return None
    differences=[values[i]-values[i-1] for i in range(1,len(values))]
    gains=[max(0.0,x) for x in differences]
    losses=[max(0.0,-x) for x in differences]
    avg_gain=sum(gains[:14])/14
    avg_loss=sum(losses[:14])/14
    for gain,loss in zip(gains[14:],losses[14:]):
        avg_gain=(avg_gain*13+gain)/14
        avg_loss=(avg_loss*13+loss)/14
    if avg_loss==0:
        return 100.0 if avg_gain>0 else 50.0
    return round6(100-100/(1+avg_gain/avg_loss))


def atr14(bars):
    if len(bars)<15:
        return None
    tr=[]
    for i in range(1,len(bars)):
        b=bars[i]
        prev=bars[i-1]["close"]
        tr.append(max(b["high"]-b["low"],abs(b["high"]-prev),abs(b["low"]-prev)))
    atr=sum(tr[:14])/14
    for value in tr[14:]:
        atr=(13*atr+value)/14
    return round6(atr)


def bollinger20_width(values):
    if len(values)<20:
        return None
    last=values[-20:]
    mean=sum(last)/20
    if mean==0:
        return None
    sigma=math.sqrt(sum((x-mean)**2 for x in last)/20)
    return {"middle":round6(mean),"upper":round6(mean+2*sigma),
            "lower":round6(mean-2*sigma),
            "width_pct":round6(4*sigma/abs(mean)*100)}

def pivots(bars, left=2, right=2):
    if len(bars) < left+right+1:
        return []
    results=[]
    for i in range(left,len(bars)-right):
        for kind,col,cmp in (("swing_high","high",max),("swing_low","low",min)):
            neighbors=[b[col] for b in bars[i-left:i+right+1]]
            value=bars[i][col]
            if cmp(neighbors)==value and neighbors.count(value)==1:
                results.append({"type":kind,"price":round6(value),"formed_at":bars[i]["time"],
                                "confirmed_at":bars[i+right]["time"]})
    return results


def technical(bars, convergence_threshold=None):
    if not bars:
        return {"status":"no_confirmed_bars"}
    close=[b["close"] for b in bars]
    vol=[b["volume"] for b in bars]
    last=bars[-1]
    ma={}
    for n in (5,10,20,60):
        current=sma(close,n)
        previous=sma(close,n,len(close)-1)
        ma[f"MA{n}"]={"value":round6(current),
                      "one_bar_slope_pct":round6((current/previous-1)*100) if previous else None}
    xs=[ma[f"MA{n}"]["value"] for n in (5,10,20)]
    disparity=(max(xs)-min(xs))/abs(xs[2])*100 if all(x is not None for x in xs) else None
    prior_xs=[sma(close,n,len(close)-5) for n in (5,10,20)]
    prior_disparity=(max(prior_xs)-min(prior_xs))/abs(prior_xs[2])*100 if all(x is not None for x in prior_xs) else None
    ma20=ma["MA20"]["value"];ma5=ma["MA5"]["value"]
    status="unknown_insufficient_history"
    if ma5 is not None and ma20 is not None and ma["MA20"]["one_bar_slope_pct"] is not None:
        if close[-1]>ma20 and ma5>ma20 and ma["MA20"]["one_bar_slope_pct"]>0:
            status="ma_uptrend_candidate"
        elif close[-1]<ma20 and ma5<ma20 and ma["MA20"]["one_bar_slope_pct"]<0:
            status="ma_downtrend_candidate"
        else:
            status="mixed_or_range_candidate"
    pv=sma(vol,20,len(vol)-1)
    turns=pivots(bars)
    price=close[-1]
    levels=[]
    for event in turns[-20:]:
        levels.append(event)
    for n in (10,20,60):
        x=ma[f"MA{n}"]["value"]
        if x is not None:
            levels.append({"type":f"MA{n}","price":x,"formed_at":last["time"],"confirmed_at":last["time"]})
    prev_high=max((b["high"] for b in bars[-21:-1]),default=None)
    prev_low=min((b["low"] for b in bars[-21:-1]),default=None)
    if prev_high is not None:
        levels.append({"type":"previous_20_high","price":round6(prev_high),"formed_at":"rolling","confirmed_at":last["time"]})
    if prev_low is not None:
        levels.append({"type":"previous_20_low","price":round6(prev_low),"formed_at":"rolling","confirmed_at":last["time"]})
    sup=sorted((x for x in levels if x["price"]<=price),key=lambda x:price-x["price"])[:5]
    res=sorted((x for x in levels if x["price"]>price),key=lambda x:x["price"]-price)[:5]
    return {
        "as_of":last["time"],"bars":len(bars),"close":price,
        "trend_candidate":status,"moving_averages":ma,
        "ma_convergence":{"periods":[5,10,20],"dispersion_pct":round6(disparity),
                          "dispersion_5_bars_ago_pct":round6(prior_disparity),
                          "change_pct_points":round6(disparity-prior_disparity) if disparity is not None and prior_disparity is not None else None,
                          "user_threshold_pct":convergence_threshold,
                          "within_user_threshold":disparity<=convergence_threshold if disparity is not None and convergence_threshold is not None else None},
        "volume":{"current":vol[-1],"rvol20_prior_bars":round6(vol[-1]/pv) if pv else None},
        "macd_12_26_9":macd(close),
        "rsi14":rsi14(close),"atr14":atr14(bars),
        "bollinger20_2sigma":bollinger20_width(close),
        "nearest_support_candidates":sup,"nearest_resistance_candidates":res,
        "pivot_rule":"left2/right2 completed bars; no lookahead",
        "notes":["只为候选支撑/压力，实际有效性需后续K线验证","指标级别与交易级别必须一致"]
    }


def weighted_profile(points, coverage=0.70):
    if not points:
        return None
    pairs=sorted(points)
    total=sum(w for p,w in pairs)
    if total<=0:
        return None
    best=(float("inf"),None,None)
    right=0
    curr=0.
    for left in range(len(pairs)):
        while curr < coverage*total and right<len(pairs):
            curr+=pairs[right][1]
            right+=1
        if curr>=coverage*total:
            width=pairs[right-1][0]-pairs[left][0]
            if width<best[0]:
                best=(width,pairs[left][0],pairs[right-1][0])
        curr-=pairs[left][1]
    poc=max(pairs,key=lambda x:x[1])[0]
    return {"POC":round6(poc),"lower_70pct":round6(best[1]),
            "upper_70pct":round6(best[2]),"coverage_target":coverage,
            "weighted_mass":round6(total)}


def volume_profile(bars, n_bars=240, n_bins=40):
    source=bars[-n_bars:]
    lo=min(b["low"] for b in source)
    hi=max(b["high"] for b in source)
    if lo==hi:
        return None
    width=(hi-lo)/n_bins
    weights=[0.0]*n_bins
    for bar in source:
        typical=(bar["high"]+bar["low"]+bar["close"])/3
        idx=min(n_bins-1,max(0,int((typical-lo)/width)))
        weights[idx]+=bar["volume"]
    points=[(lo+(idx+0.5)*width,val) for idx,val in enumerate(weights) if val>0]
    result=weighted_profile(points)
    if result is not None:
        result.update({"method":"approx_5m_typical_price_bucket_not_actual_holding_cost",
                       "price_bin_width":round6(width),"bins":n_bins,"bars_used":len(source),
                       "note":"一根5分钟K线成交量全部记入典型价位，存在偏差；不是筹码成本分布"})
    return result


def load_chip_csv(path, chip_asof, chip_model):
    if not chip_asof or not chip_model:
        raise ValueError("成本分布必须提供--chip-asof及--chip-model，区分数据日期和模型")
    values=[]
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not {"price","weight"}.issubset(reader.fieldnames):
            raise ValueError("筹码成本CSV需要price,weight两列")
        for line,row in enumerate(reader,2):
            price=finite(row["price"],"price",line)
            weight=finite(row["weight"],"weight",line)
            if price<=0 or weight<0:
                raise ValueError("成本价必须正数，权重不能负数")
            if weight:
                values.append((price,weight))
    result=weighted_profile(values)
    if result:
        result.update({"kind":"external_estimated_holding_cost_model",
                       "as_of":chip_asof,"provider_or_model":chip_model,
                       "warning":"筹码分布来自外部估计模型，不能证明真实所有股东成本或机构持仓"})
    return result


def confluence(groups, tolerance_pct, volume_info=None, chip_info=None):
    if tolerance_pct is None:
        return {"status":"no_user_tolerance","clusters":[]}
    prices=[]
    for tf in ALL_TIMEFRAMES:
        for side in ("nearest_support_candidates","nearest_resistance_candidates"):
            for level in groups[tf].get(side,[]):
                prices.append({"timeframe":tf,"side":side,"type":level["type"],"price":level["price"]})
    if volume_info is not None and volume_info.get("POC") is not None:
        prices.append({"timeframe":"volume_profile_approx","side":"price_volume_node",
                       "type":"historical_volume_POC","price":volume_info["POC"]})
    if chip_info is not None and chip_info.get("POC") is not None:
        prices.append({"timeframe":"chip_cost_model","side":"estimated_cost_node",
                       "type":"estimated_chip_cost_POC","price":chip_info["POC"]})
    prices.sort(key=lambda x:x["price"])
    clusters=[]
    for level in prices:
        if not clusters or 100*abs(level["price"]-clusters[-1]["mean"])/clusters[-1]["mean"]>tolerance_pct:
            clusters.append({"mean":level["price"],"members":[level]})
        else:
            cluster=clusters[-1]
            cluster["members"].append(level)
            cluster["mean"]=sum(x["price"] for x in cluster["members"])/len(cluster["members"])
    result=[]
    for cluster in clusters:
        frames=sorted({x["timeframe"] for x in cluster["members"] if x["timeframe"] in ALL_TIMEFRAMES})
        kinds=sorted({x["timeframe"] for x in cluster["members"]})
        if len(kinds)>1:
            result.append({"zone_low":round6(min(x["price"] for x in cluster["members"])),
                           "zone_high":round6(max(x["price"] for x in cluster["members"])),
                           "timeframes":frames,"distinct_data_sources":kinds,
                           "levels":cluster["members"]})
    return {"status":"multi_timeframe_level_proximity_only_not_probability",
            "user_tolerance_pct":tolerance_pct,"clusters":result}


def analyze(rows,args):
    if args.chip_profile and args.chip_asof and dt.date.fromisoformat(args.chip_asof) > dt.date.fromisoformat(rows[-1]["date"]):
        raise ValueError("筹码分布模型日期晚于已取得行情，禁止使用未来数据")
    timeframes,quality=make_timeframes(rows)
    readings={tf:technical(timeframes[tf],args.ma_convergence_pct) for tf in ALL_TIMEFRAMES}
    profile=volume_profile(rows,args.profile_bars,args.profile_bins)
    chips=load_chip_csv(args.chip_profile,args.chip_asof,args.chip_model) if args.chip_profile else None
    prev_chip=load_chip_csv(args.chip_prev_profile,args.chip_prev_asof,args.chip_model) if args.chip_prev_profile else None
    if prev_chip is not None and chips is not None and args.chip_prev_asof>=args.chip_asof:
        raise ValueError("上期筹码模型日期必须早于当前模型日期")
    drift=round6(chips["POC"]-prev_chip["POC"]) if chips and prev_chip else None
    return {"source":"user_supplied_completed_5m_ohlcv","exchange_timezone":"Asia/Shanghai",
            "reference_session":"09:30-11:30,13:00-15:00; 120m does not cross lunch",
            "timeframes":readings,"quality":quality,
            "cross_timeframe_levels":confluence(readings,args.zone_tolerance_pct,profile,chips),
            "executed_volume_profile_approx":profile,"estimated_chip_cost_profile":chips,
            "previous_estimated_chip_cost_profile":prev_chip,"chip_poc_change_price_units":drift,
            "warning":["5分钟OHLCV的价量分桶不是真实持仓筹码分布",
                       "多周期同步/均线粘合只反映过去数据，不保证后续上涨",
                       "周/月周期保守排除尚未观察到下一周期的当期K线",
                       "没有用户明确设置阈值时，不宣称均线已粘合或支撑出现多周期共振",
                       "本脚本不获取交易所数据，不自动执行交易"]}


def percent(value):
    x=float(value)
    if not math.isfinite(x) or x<=0 or x>100:
        raise argparse.ArgumentTypeError("百分比须在0~100之间")
    return x


def main():
    p=argparse.ArgumentParser(description="从A股已完成5分钟K线生成5/30/60/120分钟、日周月多周期技术诊断")
    p.add_argument("ohlcv_5m",type=Path)
    p.add_argument("--as-of",type=dt.datetime.fromisoformat)
    p.add_argument("--ma-convergence-pct",type=percent,help="用户自定义MA5/10/20离散度阈值")
    p.add_argument("--zone-tolerance-pct",type=percent,help="用户自定义多周期价位聚合容差")
    p.add_argument("--profile-bars",type=int,default=240,help="近多少根5分K线用于估算成交量价格分布")
    p.add_argument("--profile-bins",type=int,default=40,help="成交量价格分布价位桶数")
    p.add_argument("--chip-profile",type=Path,help="来自外部数据商的筹码成本估计CSV，需price,weight")
    p.add_argument("--chip-asof",help="成本分布数据日期YYYY-MM-DD")
    p.add_argument("--chip-model",help="成本分布供应商及模型名称")
    p.add_argument("--chip-prev-profile",type=Path,help="可选上期筹码成本价格权重CSV")
    p.add_argument("--chip-prev-asof",help="上期筹码模型数据日期YYYY-MM-DD")
    args=p.parse_args()
    try:
        if args.as_of is not None and args.as_of.tzinfo is not None:
            raise ValueError("--as-of须为Asia/Shanghai本地无时区偏移时间")
        if args.profile_bars<1 or not 4<=args.profile_bins<=400:
            raise ValueError("profile-bars应>=1且profile-bins须在4~400")
        if args.chip_prev_profile and (not args.chip_profile or not args.chip_prev_asof):
            raise ValueError("要比较筹码变化须有当前模型及--chip-prev-asof")
        if args.chip_prev_asof and not args.chip_prev_profile:
            raise ValueError("提供上期筹码日期时须有上期筹码CSV")
        if args.chip_profile is None and (args.chip_asof or args.chip_model):
            raise ValueError("提供--chip-asof/--chip-model时必须同时提供--chip-profile")
        if args.chip_asof:
            dt.date.fromisoformat(args.chip_asof)
        if args.chip_prev_asof:
            dt.date.fromisoformat(args.chip_prev_asof)
        rows=load_5m(args.ohlcv_5m,args.as_of)
        print(json.dumps(analyze(rows,args),ensure_ascii=False,indent=2))
    except (OSError,ValueError) as exc:
        p.error(str(exc))


if __name__=="__main__":
    main()
