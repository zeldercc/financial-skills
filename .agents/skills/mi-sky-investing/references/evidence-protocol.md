# 来源、证据分级与验证纪律

## 一、证据类型

| 标签 | 说明 | 引用方式 |
|---|---|---|
| `A` 原作者可追溯陈述 | 能在原始账号、直接发表文章或原始会议纪要中定位 | 作者、精确时间、链接、原文片段/段落 |
| `B` 用户提供的资料汇编 | 编辑整理过的同一作者材料、书稿、图片或复盘 | 文档完整文件名、内部条目编号、原文标示日期、PDF页（有可靠定位时） |
| `C` 交叉归纳 | 多个 `A/B` 支持的思想总结，非直接引语 | 至少两个独立的主题段落，同时标明可能重复来源 |
| `D` 框架推断 | AI 使用方法对现实标的作推论 | 明示`[框架推演]`、假设、数据、反证 |
| `E` 外部事实 | 财报、公告、交易所、统计部门及最新市场数据 | 出处、发布时间、数据时点、币种和统计口径 |

**注意**：证据强度按可验证性而非“文档出现次数”决定。P01、P02、P03是同一批2026年10月推文的不同编辑版本，不能视为三次独立证据。

## 二、观点记录字段

- `claim_id`：稳定观点编号
- `author`：Mi姐/Sky/Mistery，按资料署名原样记录
- `claimed_at`：作者原始发言日期；未知标“未知”
- `compiled_at`：收录/文件修改日期，不等于发言日期
- `source_key`：source-index中的代码
- `locator`：条目编号、标题、原始推文时间戳或PDF页码
- `claim_kind`：长期原则 / 阶段性预测 / 个股观点 / 具体交易触发
- `horizon`：作者明确给出的有效期限或“未披露”
- `market_context`：当时的大盘、政策及行业背景（必须来源明确）
- `confidence`：证据 A/B/C/D/E，另给“高/中/低”的可核验程度
- `claim_text_paraphrase`：简短概括，避免大量复制原文
- `falsifier`：何种事实将推翻假设
- `status`：待验证 / 支持 / 部分支持 / 反证 / 过期 / 无法评估

## 三、来源质量规则

1. **先查原始 X 帖及官方公告**。推文汇编可能丢失互动上下文，按“整理资料”引用，不推断真实身份或业绩。
2. **原文日期 > 编纂日期**。遇到日期标注冲突，指出具体差异，不猜。
3. **不把同一观点不同排版当成多份独立证据**。同一笔历史案例也不能重复计算命中率。
4. **行情数据不得使用模糊时间戳**。报告开头写“截至 YYYY-MM-DD HH:mm 交易所时区”；盘中数据标盘中，收盘数据标收盘。
5. **多语言核对**：中国市场检索简体中文、繁体中文和英文；港股以披露交易所语言为准；其他国家添加当地语言。原始证券披露优于转述报道。
6. **不得自动背书**：在报告中分离作者思想适配度、股票当前价值判断和个人组合适配度。
7. **反面证据为强制项**：至少列出两项，阐明对结论影响。
8. **没有有效数据时不能硬凑**：不给目标价、胜率、仓位数字或买卖点。

## 四、预测质量复盘

复盘历史推文时：先锁定发言当日已知信息、预测对象、价格口径、期间、预测方向；再查询之后的实际数据、交易成本、最大回撤、相应基准收益。无法确认这些条件的，不评“预测成功率”。

避免选择性披露：同时纳入支持和不支持作者判断的案例。区分“某一阶段方向预测正确”与“按可成交价格执行后能盈利”。

参考：
- CFA Institute 2026, Active Equity Investing: Strategies: https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/active-equity-investing-strategies
- CFA Institute 2026, Portfolio Performance Evaluation: https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/portfolio-performance-evaluation
- 美国SEC 2026-02-06, Social Media and Stock Tip Scams: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/social-media-stock-scams
