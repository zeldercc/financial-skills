# financial-skills

用于学习并应用 Mi姐（Mistery，资料汇编中署名 Sky / @wr0789）的股票投资研究方法的 Agent Skill。

## Skill 定位

本仓库不是荐股合集，也不是实时交易信号服务。它把用户提供的历史会议纪要、复盘、长文和推文中可追溯的投资方法，转换为可执行的股票研究工作流：

1. **宏观和流动性**：先识别市场环境与主要风险。
2. **大盘和行业周期**：判断大级别趋势、板块景气与资金轮动。
3. **个股基本面和估值**：核验企业质量、估值及市场预期。
4. **技术实操及交易结构**：实际计算MA5/10/20/60/120/250、均线交叉、成交量及RVOL、支撑压力、突破/回踩，并结合趋势、震荡及左侧/右侧模式形成条件式计划。
5. **仓位、失效条件与复盘**：设定可承受风险，记录历史观点和实际结果。

关键规则：**忠实还原作者观点，但不把作者历史判断当作当前事实，不把 AI 推断冒充作者建议。**

## 文件结构

```text
financial-skills/
  .agents/skills/mi-sky-investing/
    SKILL.md
    references/
      core-methodology.md
      source-index.md
      evidence-protocol.md
      decision-process.md
      technical-playbook.md
      stock-selection.md
      price-action-and-exits.md
      multi-timeframe-and-chips.md
      chanlun-framework.md
      unified-decision-framework.md
      historical-notes.md
    templates/
      stock-analysis.md
      opinion-ledger.csv
    scripts/
      validate_skill.py
      analyze_ohlcv.py
      screen_watchlist.py
      analyze_multitimeframe.py
      chan_segment_check.py
  tests/test_skill.py
  tests/test_technical_analysis.py
  tests/test_watchlist_screening.py
  tests/test_multitimeframe.py
  tests/test_chan_structure.py
  README.md
  NOTICE.md
  .gitignore
```

## 使用方法

将仓库放在支持 `.agents/skills/` 的 Agent 工作目录，或者将 `mi-sky-investing/` 子目录安装到客户端规定的 Skills 路径。在 ChatGPT / WorkBuddy / Codex 等环境中，要求 Agent 读取本 Skill，再提出例如：

> 请调用 mi-sky-investing 研究中科曙光。给出大盘、行业、个股三层分析，评估估值与交易结构，列出左侧/右侧两套条件式方案，逐条给出处和失效条件。数据截止今天，请先联网核验。

> 用 mi-sky-investing 分析某只股票是否适合长期持有。区分作者明确说过什么、由作者方法推导出的假设、最新市场事实。

> 基于我新补充的会议纪要更新 Mi姐投资思想，列出新增、改变和冲突的观点，保留历史版本和原始出处。


## 技术分析实操

本Skill包含来源可追溯的“520战法”（MA5和MA20）、MA5/20/60趋势确认、量价结构、放量突破、缩量回踩、支撑压力转换、MACD及右侧入场验证流程。技术规则详见 .agents/skills/mi-sky-investing/references/technical-playbook.md。

用户提出具体股票研究时，需要先取得真实的最新行情及历史OHLCV数据；不得仅因“均线金叉”给出买入建议，也不得编造未取得的价格或量能。

提供本地CSV时，可以执行离线指标计算：

~~~bash
python .agents/skills/mi-sky-investing/scripts/analyze_ohlcv.py daily.csv \
  --timeframe daily \
  --as-of 2026-11-04
~~~

CSV为按日期严格升序的已完成K线，必须包含以下列：

~~~csv
date,open,high,low,close,volume
~~~

可选：--high-rvol 1.5 设定用户自定义放量比较阈值；该阈值是用户研究参数，并非作者固定标准。--breakout-lookback 20 用于当前已完成K线相对于此前20根K线的突破候选识别。工具不会自动确认未来回踩，也不自动联网获取行情。

如有账户风险条件，可以再提供 --account-equity、--risk-percent、--entry-price、--stop-price、--lot-size，得到止损距离约束的理论最大数量；它没有计入费用、跳空和组合约束，实际风险可能超过预算。

周线或月线需**单独提供对应周期、已经完成的K线CSV**，并以 --timeframe weekly/monthly 计算。不能将日线数据改个标签当周线，也不能将尚未收盘的周/月K作为确认信号。

研究时可直接询问：

> 使用 mi-sky-investing 分析中科曙光。按最新真实价格给出MA5/10/20/60/120/250、均量与RVOL20、MACD、前高前低和支撑压力；指出是否满足520战法、是否存在放量突破与缩量回踩、右侧确认处于哪一步，并将未完成条件、失效位置和证据来源列清楚。

## 新增：股票池筛选与买卖点

v1.2.0 新增可溯源的选股与操作规则：

- `references/stock-selection.md`：T00第196条的强势股筛选参数、股性分类、月线长期箱体与周线W底候选、RPS口径限制。
- `references/price-action-and-exits.md`：涨跌趋势/震荡区间识别、五类买点、七类卖点、突破后1至3根K线的确认观察、移动止盈、缠论术语冲突。
- `scripts/screen_watchlist.py`：按本地股票CSV目录批量输出MA20/60/120、VMA5/10、RSI、MACD及是否满足历史技术筛选参数；明确缺失数据和“不能计算完整市场RPS”。

使用方法：

~~~bash
python .agents/skills/mi-sky-investing/scripts/screen_watchlist.py ./ohlcv/ --as-of 2026-11-04
~~~

目录内每个CSV用股票代码命名，如600536.SH.csv，列名与OHLCV分析脚本一致。输出仅是**技术候选及不满足条件记录**，不代表真实机构持仓，不完成财报、估值筛选，更不直接构成交易指令。原文中部分数值阈值仅来自2025年的一篇文章，不能当作统一有效策略。

## v1.3.0：多周期支撑压力、均线粘合与筹码成本

详细规则在 `references/multi-timeframe-and-chips.md`，包括：
1. 5、30、60、120分钟及日、周、月七级别联动，先月周定方向，日线找结构，分钟级别定位候选买卖区。
2. 各级MA5/10/20/60及其斜率；MA5/10/20离散度，用于观察均线粘合到发散的变化；粘合阈值仅由用户另行指定。
3. 前高前低、已确认摆动点、各级均线的候选支撑压力与跨级别近价位聚合；不能凭单一周期确认周/月反转。
4. 分离“历史成交量按价分布”与外部数据商估计的“持仓筹码成本分布”。筹码估计必须提供数据日期和模型来源，不可把5分钟OHLCV模拟为实际持有人成本。

A股完整5分钟K线应使用Asia/Shanghai时区的本地**K线开始时间**，并有如下CSV列：

~~~csv
timestamp,open,high,low,close,volume
2026-11-04T09:30,10.00,10.12,9.99,10.08,18000
~~~

该行**仅为CSV格式演示，不是真实行情**，不能在投资分析中当作实际数据。

~~~bash
python .agents/skills/mi-sky-investing/scripts/analyze_multitimeframe.py ./bars_5m.csv \
  --ma-convergence-pct 1.0 \
  --zone-tolerance-pct 0.5
~~~

以上两个百分数属于**用户研究参数**，并非Mi姐原文规定。

若另有数据商提供的筹码成本CSV（列`price,weight`），可额外加入：

~~~bash
  --chip-profile ./chips.csv --chip-asof 2026-11-03 --chip-model "来源与估算方法" \
  --chip-prev-profile ./chips_previous.csv --chip-prev-asof 2026-10-31
~~~

脚本不会抓取行情或验证数据商来源；会拒绝周末5分钟K线、排除不完整交易日的高级别确认，并采用保守的周/月收盘规则。筹码模型可选提供两个不同日期的同源价格分布快照，以对比模型成本峰迁移。近240根5分钟K线的成交量分桶仅为粗略的价位成交量分布，**并非真实筹码成本数据**。

[上海证券交易所交易规则（2026年修订）](https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml)；
[TradingView Volume Profile官方解释](https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/)；
[富途牛牛筹码分布说明](https://support.futunn.com/topic585?from_platform=1&lang=zh-cn)。

[富途牛牛筹码分布入口及数据含义](https://support.futunn.com/topic585?from_platform=1&lang=zh-cn)可辅助取得该指标，但脚本不会直接读取富途账户；需提供CSV及来源。


## v1.4.0：2026-11-04云盘更新后的重新梳理

2026-11-04再次扫描用户指定的Google Drive文件夹，记录到**34个文件（28份PDF、1份DOCX、5张JPG）**。与v1.3.0的32项目录相比，新增两份缠论相关资料：

- C01：《缠中说禅：股市技术理论》，理论编订资料，含分型、笔、线段、中枢、背驰和三类买卖点。
- C02：《缠中说禅：教你炒股票108课》，原始课程的PDF汇编；文字提取有部分乱码，准确术语需与C01和公开原课交叉核对。

**三种内容必须分开**：
1. Mi姐（Sky/Mistery）2025至2026年整理资料中的投资思想、产业周期、均线、选股和交易经验。
2. 独立于Mi姐的缠中说禅原始理论及编订教材，尤其是完整次级别走势、中枢ZD/ZG与一二三类买卖点的严格定义。
3. 用于实操的市场数据计算约定，例如MA离散度、RVOL、价格支撑聚合、成交量价分桶及完整K线分时合成。

### 新增模块

- **统一操作流程**：references/unified-decision-framework.md。按市场→行业→估值与股性→七级别K线→支撑压力与筹码→普通买卖点/缠论双轨→退出与复盘。
- **缠论原典与Mi姐应用比较**：references/chanlun-framework.md。明确三买须有已形成中枢、完成的次级走势向上离开后首次回试不跌破中枢上沿ZG；三卖反向，注意中枢下沿ZD。
- **次级走势几何校验**：scripts/chan_segment_check.py。只对外部事先分段、已完成、同级的次级走势段检查价格区间重叠及候选三买/三卖模板。它**不从OHLCV自动识别缠论笔、线段或严格走势级别**，输出不代表真实可交易的缠论信号。

### 缠论分段检查示例

人工划分次级走势段CSV需列：
~~~csv
end_time,level,direction,low,high,completed
~~~

要求每段的level相同，direction为up或down、交替，completed必须为true，end_time严格递增且为交易所当地时间。这些分段须先按**书面固定的包含关系、分型、笔、线段及走势类型规则**进行外部校验。

~~~bash
python .agents/skills/mi-sky-investing/scripts/chan_segment_check.py \
  ./completed_legs.csv \
  --source "本人审查后的人工分段数据" \
  --segment-method "已声明并固定的分型、笔、线段与走势划分版本"
~~~

程序仅输出几何候选，不会自动确认证券买卖点；缺少完整的次级走势结构时，个股研究必须写“严格缠论不可判定”。

### 与现有模块的关系

v1.1均线与量价、v1.2选股及买卖点、v1.3七周期支撑压力/筹码分布全部保留。**v1.4新增严格缠论理论校核和统一决策流程，并修正把箱体回踩当“三买”的潜在误用。**原教材中“100%”等表达不代表经回测的实盘胜率。

详见[来源索引](.agents/skills/mi-sky-investing/references/source-index.md)及[证据规则](.agents/skills/mi-sky-investing/references/evidence-protocol.md)。

## 原始资料的管理

- 原始 PDF、DOCX 和私人 Google Drive 文件链接**未被上传到本包**。使用者须通过其有权限的云端目录或自行提供资料。
- `references/source-index.md` 列出用户指定目录的资料名称与检索定位点。文件包含重复汇编，分析时不要重复计权。
- 书稿《Mistery趋势交易论》明确标明禁止转载或改编，因此本仓库不包含该书原文、扫描件或节选复刻。只保留思想的独立归纳和定位索引。
- 研究结果不自动转换为下单、交易或投顾行为。

## 验证

```bash
python .agents/skills/mi-sky-investing/scripts/validate_skill.py
python -m unittest discover -s tests -v
```

## 参考标准

Skill 结构遵循 [Agent Skills specification](https://agentskills.io/specification)。研究方法的独立验证原则参考 [CFA Institute 2026 Active Equity Investing](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/active-equity-investing-strategies)。
