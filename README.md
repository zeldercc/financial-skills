# financial-skills

用于学习并应用 Mi姐（Mistery，资料汇编中署名 Sky / @wr0789）的股票投资研究方法的 Agent Skill。

## Skill 定位

本仓库不是荐股合集，也不是实时交易信号服务。它把用户提供的历史会议纪要、复盘、长文和推文中可追溯的投资方法，转换为可执行的股票研究工作流：

1. **宏观和流动性**：先识别市场环境与主要风险。
2. **大盘和行业周期**：判断大级别趋势、板块景气与资金轮动。
3. **个股基本面和估值**：核验企业质量、估值及市场预期。
4. **交易结构和策略**：区分趋势、震荡及左侧/右侧模式，拟定条件式计划。
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
      historical-notes.md
    templates/
      stock-analysis.md
      opinion-ledger.csv
    scripts/
      validate_skill.py
  tests/test_skill.py
  README.md
  NOTICE.md
  .gitignore
```

## 使用方法

将仓库放在支持 `.agents/skills/` 的 Agent 工作目录，或者将 `mi-sky-investing/` 子目录安装到客户端规定的 Skills 路径。在 ChatGPT / WorkBuddy / Codex 等环境中，要求 Agent 读取本 Skill，再提出例如：

> 请调用 mi-sky-investing 研究中科曙光。给出大盘、行业、个股三层分析，评估估值与交易结构，列出左侧/右侧两套条件式方案，逐条给出处和失效条件。数据截止今天，请先联网核验。

> 用 mi-sky-investing 分析某只股票是否适合长期持有。区分作者明确说过什么、由作者方法推导出的假设、最新市场事实。

> 基于我新补充的会议纪要更新 Mi姐投资思想，列出新增、改变和冲突的观点，保留历史版本和原始出处。

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
