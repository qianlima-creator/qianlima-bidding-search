# 采购意向查询

## 何时使用

- 查采购意向、采购计划、未来采购、预计采购时间或正式招标前的机会。
- 不用于已发布的招标/中标公告、临期续约、企业关系或企业电话。
- “采购”但没有未来、意向、计划等信号时，按普通项目理解；无法稳定判断时再澄清。

执行动作：`search-purchase`；接口：`POST /api/search/purchase`；命令同时传 `--user-text` 用户原话。禁止改用项目阶段 `99`。

## 关键参数

| 用户条件 | query-json |
| --- | --- |
| 产品、服务、项目或行业词 | `keywords`，必填 |
| 排除内容 | `excludeWords` |
| 预计采购时间 | `startPlanPurchaseDate` / `endPlanPurchaseDate`，`YYYY-MM` |
| 公告发布时间 | `beginTime` / `endTime`，`YYYY-MM-DD` |
| 预计采购金额 | `startPlanPurchaseAmount` / `endPlanPurchaseAmount`，单位元 |
| 地区、采购单位类型 | `areaIds`、`purchasingUnitTypes`，映射见 `query-strategy.md` |
| 匹配范围、扩词、数量、排序 | 按 `query-strategy.md`；匹配范围支持 1–10；仅用户明确指定或角色/编号等语义需要时传 |

## 时间与金额

- “近三个月采购意向”默认理解为预计采购时间；只有明确“最近发布”才使用公告发布时间。
- 同时明确预计采购时间和发布时间时，两组条件同时生效。
- 未传预计采购时间时，接口默认查询未来第 1 至第 3 个月。
- 金额条件始终表示预计采购金额；`refine` 可用 `beginAmount/endAmount`，运行时会映射到预计采购金额字段。

## 结果

- 列表可回答标题、采购单位、地区、预计采购时间、预计采购金额、发布时间和千里马详情页。
- `purchaseContent` 只在用户指定某条后通过 `detail` 获取，不在列表阶段编造摘要。
- 采购意向详情不返回原文链接、联系人、电话、代理机构、标的物或截止时间；检索范围仍支持对应位置；需要来源时只返回接口已有的千里马详情页 `url`。
- 与正式项目同时查询时，拆成两个独立查询并按 `follow-up-and-results.md` 分区展示。

完整请求和返回字段见 [采购意向 API](../api-purchase-intentions.md)。独立正文、附件和时间线接口不适用于采购意向。
