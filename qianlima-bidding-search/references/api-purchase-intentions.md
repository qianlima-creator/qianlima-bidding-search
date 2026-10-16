# 采购意向接口

## 搜索

`POST /api/search/purchase`

通过关键词、预采时间等检索条件，搜索采购意向。

### 入参字段

- `keywords`：搜索关键词数组，必填。最多 10 个，且至少包含一个非空关键词，用于检索采购意向的关键词，例如产品、项目、公司、行业词。
- `keywordsSearchType`：关键词匹配方式。`1` 表示任一关键词命中；`2` 表示所有关键词同时命中，默认 `1`。
- `excludeWords`：排除词数组，可选。最多 10 个，命中任意排除词的公告会被过滤掉。
- `matchScopes`：匹配范围列表，可选。控制关键词匹配的位置，不传默认匹配标题+正文。与普通标讯和临期项目共用匹配范围枚举，支持 `1`（全部：标题+正文+附件）、`2`（标题）、`3`（项目编号）、`4`（采购单位）、`5`（中标单位）、`6`（代理机构）、`7`（联系人）、`8`（正文）、`9`（标的物）、`10`（附件），支持组合多选。格式为数字数组。
- `startPlanPurchaseDate`：预计采购开始时间，可选。格式 `yyyy-MM`，默认未来 1 个月。
- `endPlanPurchaseDate`：预计采购结束时间，可选。格式 `yyyy-MM`，默认未来 3 个月。
- `beginTime`：发布开始时间，可选。公告发布时间起始日期，格式 `yyyy-MM-dd`。
- `endTime`：发布结束时间，可选。公告发布时间截止日期，格式 `yyyy-MM-dd`。
- `areaIds`：地区 ID 数组，可选。支持省、市、区/县，取值来自 `area.json`；不传时按全国查询。 先按 [地区规则](../SKILL.md#地区) 取得已确定参数；`[]` 为显式取消筛选，运行时移除该字段，未知编号、布尔值与小数不接受。
- `startPlanPurchaseAmount`：预计采购金额下限，可选。单位为元。
- `endPlanPurchaseAmount`：预计采购金额上限，可选。单位为元。
- `purchasingUnitTypes`：采购单位类型数组，可选，枚举见 `enums.md`。
- `sortType`：排序字段，可选。采购意向支持 `1`（时间倒序）、`2`（综合排序）、`6`（相关性倒序），默认值为 `2`。
- `currentPage`：页码，必传，从 1 开始。
- `numPerPage`：每页数量，可选。默认 30，最大 100。

### 返回字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `rowCount` | integer | 符合条件的公告总数。 |
| `pageCount` | integer | 按当前每页数量计算出的总页数。用于判断是否还有下一批。 |
| `list` | array | 当前页返回的公告列表。 |

公告卡片字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 公告唯一标识。 |
| `title` | string | 项目名称/公告标题。 |
| `publishTime` | string | 公告发布日期，格式 `yyyy-MM-dd`。 |
| `budgetAmount` | string | 预算金额，单位为元。为空表示未公示。 |
| `planPurchaseDate` | string | 预计采购的日期。 |
| `purchasingUnit` | string | 发布招标或采购需求的单位。 |
| `areaName` | string | 项目所属地区，通常为”省-市-区/县”格式。 |
| `url` | string | 千里马采购意向详情页链接。用于查看正文。 |

## 详情

`GET /api/purchase/detail/{id}`

已知真实采购意向公告 ID 直接 `detail --id ID --result-type purchase_intention`，不要求搜索名单、会话或有效/可写缓存。序号/标题先由对应结果唯一定位；来源不明只澄清，不尝试其他接口。

### 入参字段

- `id`：公告 ID，路径参数。用于精确定位采购意向公告。

### 返回字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | integer | 公告唯一标识。 |
| `title` | string | 项目名称/公告标题。 |
| `publishTime` | string | 公告发布日期，格式通常为 `yyyy-MM-dd`。 |
| `budgetAmount` | string | 预算金额，单位为元。为空表示未公示。 |
| `planPurchaseDate` | string | 预计采购的日期。 |
| `purchasingUnit` | string | 发布招标或采购需求的单位。 |
| `areaName` | string | 项目所属地区，通常为"省-市-区/县"格式。 |
| `purchaseContent` | string | 采购需求描述。 |
| `url` | string | 千里马采购意向详情页链接。用于查看正文。 |


检索匹配范围支持 1–10，不表示详情会返回这些位置的字段。采购意向只可取采购需求和详情页，不支持普通项目正文、附件、时间线或来源链接接口。
