# 千里马 API 与脚本响应

## 认证与事实

默认生产地址 `https://skills.qianlima.com`，可通过既有 `QIANLIMA_BASE_URL` 配置。认证请求头是 `qianlimaApiKey`，每次值来自当前 `QIANLIMA_API_KEY`；JSON 请求使用 `Content-Type: application/json`。Key 只放在本次初始接口请求头，HTTP 重定向不转发。查询状态不选择或替换凭据；换 Key 不使原查询失效，由当前业务 API 最终鉴权。不自创认证头，不打印、记录或回显密钥，不写入快照。

真实联调前 `GET /api/user/verify` 确认账号与 Skill 权限；成功 data 的 `username` 仅供账号核对，不主动展示。此验证不是普通每次搜索的额外前置请求。

API 通用外层是 `code/msg/data/success`，以 code 200 判断业务成功，其他业务码按 API 返回处理。Skill 不按 data 的字段、类型、空值或对象编号再次判断成败。字段为空或 null 表示信息未公示，0 和 false 保留原意。

## 按能力读取

| 能力 | 参考 |
| --- | --- |
| 项目搜索、详情 | [普通项目](api-projects.md) |
| 正文、附件、时间线、来源链接 | [项目资源](api-project-resources.md) |
| 采购意向搜索、详情 | [采购意向](api-purchase-intentions.md) |
| 临期项目搜索、详情 | [临期项目](api-expiring-projects.md) |
| 公司搜索、8 类企业分析/电话 | [企业情报](api-enterprise-intel.md) |
| 当前积分、原文月度用量 | [积分权益](api-entitlement.md) |
| 搜索 ID 与枚举 | [枚举](enums.md) |

## 脚本 JSON

`scripts/qianlima_skill.py` 返回给 Agent；面向用户翻译成任务结论，不平铺字段。

| 字段 | 用途 |
| --- | --- |
| `ok/user_message/warnings` | API 业务结果与展示说明；展示/状态异常不覆盖已取得的业务结果 |
| `api_responses` | 每次调用的 path 与原始 response，完整保留状态、消息、未知字段、值和类型；连接/解析异常单列 transport_error |
| `total_count/returned_count` | 当前查询总数、本批数量；不合并独立分支总数 |
| `effective_query/request_query` | 实际生效、发送条件，核对原意未丢失 |
| `cards` | 三类项目的当前列表 |
| `rows` | 公司候选或企业分析结果 |
| `detail/full_detail` | 单条请求字段/完整支持详情 |
| `partial_success/retry_fields` | 多资源按各自 API 结果交付；详情与来源任一失败均保留另一项成功数据，不重放成功调用 |
| `full_text` | 普通项目正文对象 |
| `attachments/timeline` | 附件/进展节点数组 |
| `resolution` | 唯一对象定位结果 |
| `follow_up` | 保存 session_id/result_set_id、有效期、允许动作 |
| `area_expansion` | 支持区县筛选地区的零结果扩大建议；用户同意前不得执行 |
| `retry_policy` | 状态异常为 `restore_explicit_context_or_clarify_missing_fields`：先恢复明确上下文，只澄清缺项，不自动重查 |
| `balancePoints/frozenPoints/availablePoints/sourceUrlUsage` | 积分命令顶层事实 |

展示字段服务当前用户任务，不替代原始响应；不向用户平铺原始 JSON。展示或保存失败时依据 api_responses 交付已有数据，不重复成功调用。字段空值只表达“未公示”，不解释为“未返回”“接口未提供”或不存在。只有接口明确失败才保留失败；连接/解析异常表示未取得可解析响应。页码或定位信息不足时限制对应后续操作，不猜测、不修改本次成功状态。

本手册中的 current_query 指原成功输出的完整 effective_query；current_result_set 是指定结果的当前列表；focus_project 是最近唯一定位的项目。公司候选、时间线和项目列表不是同一组序号，按各自 follow_up 绑定。状态错误的 `requires_user_confirmation` 为 false、`needs_clarification` 为 true；先检查对话能否补全，不以缓存问题要求确认重搜。

三源搜索 API 列表返回 rowCount/pageCount/list；公司候选返回 total/currentPage/pageSize/list。总数只按接口总数字段说明，本批条数按实际返回列表说明；缺总数字段时不把本批条数当作总数。来源链接与详情页不同，只有明确索要才取来源链接。详情字段按当前源，支持位置检索不能推导详情新增字段。

金额为元，可转换为万元显示；空值未披露，数值 0 不是空值。附件状态保留 true/false/null；候选、分类、标的物等数组保持结构，不转字符串。

## 错误码


- `200`：成功。
- `401`：未认证。
- `429`：请求过于频繁。
- `10001`：API Key 无效。
- `10004`：接口参数异常。
- `10005`：详情不存在。
- `10006`：详情已撤回。
- `10007`：无权查看详情。
- `10010`：用户无权限查看该数据。
- `10011`：原文链接不存在。
- `10028`：地区权限不足。
- `10030`：积分余额不足。
- `10031`：积分扣除失败，请稍后重试。
- `10032`：积分账户未初始化或正在初始化。
- `10036`：原始公告来源链接本月获取次数已用完。
- `10037`：积分结算已超时，请重试。
- `10038`：请求正在处理中，请稍后重试。
- `10039`：价格版本已变化，请刷新权益后重试。
- `10040`：请求标识冲突，请重新发起请求。
- `10041`：项目完整正文未采集或为空。

错误码用于判断错误类别，面向用户时可转换为友好的中文提示，例如密钥问题、数据权限、积分余额、
月度次数、结算状态、请求频率、参数问题或数据暂不可用。

原业务错误原因始终保留，权益诊断最多补充一次积分/原文用量事实，不能覆盖错误。余额正常不证明地区权限可用或存在数据。正常零结果不诊断，网络或结算状态不明不自动重放计费调用。

状态缺失、过期、损坏时，已知公告 ID 可独立读取；原查询可由完整上下文恢复。明确结果集可跨会话引用，无需会话编号。不能准确恢复对象、源、全部条件或页码时只澄清缺项，不回退别的结果。多资源部分成功时交付成功部分，清理或保存故障不覆盖 API 成功、不触发重放。账号入口与故障反馈见 [账号](account-access.md)、[FAQ](faq.md)。

## 完整查询上下文

`next/refine/search-company --next` 可用 `--context-json` 恢复明确原查询。`result_type` 必须已知；`effective_query` 完整复制上一轮成功输出，保留所有有效条件、准确 `currentPage` 和页大小，不使用原始简略输入或补猜默认。项目页大小是 `numPerPage`，公司是 `pageSize`，并保留 `companyName`。已知 `page_count` 可附带；0 或已到末页不多调，未知总页数但当前页准确可继续。

原结果集仍可用时最短调用如下，可省略或更换会话：

```bash
python3 scripts/qianlima_skill.py next --result-set-id RESULT
python3 scripts/qianlima_skill.py refine --result-set-id RESULT --query-json '{"hasAnnex":0}'
```

例如原成功输出的全部有效条件如下：

```json
{"result_type":"project","effective_query":{"keywordGroups":[{"keywords":["物业"],"matchScopes":[2,9]}],"beginTime":"2026-09-01 00:00:00","endTime":"2026-09-30 23:59:59","currentPage":1,"numPerPage":10},"page_count":3}
```

```bash
python3 scripts/qianlima_skill.py next --context-json '{"result_type":"project","effective_query":{"keywordGroups":[{"keywords":["物业"],"matchScopes":[2,9]}],"beginTime":"2026-09-01 00:00:00","endTime":"2026-09-30 23:59:59","currentPage":1,"numPerPage":10},"page_count":3}'
python3 scripts/qianlima_skill.py refine --context-json '{"result_type":"project","effective_query":{"keywordGroups":[{"keywords":["物业"],"matchScopes":[2,9]}],"beginTime":"2026-09-01 00:00:00","endTime":"2026-09-30 23:59:59","currentPage":1,"numPerPage":10}}' --query-json '{"hasAnnex":0}'
```

下一页只将原页码加 1，细化只改 patch 并回第一页。采购意向/临期保留自身全部有效条件，例如：

```json
{"result_type":"purchase_intention","effective_query":{"keywords":["物业"],"startPlanPurchaseDate":"2026-11","endPlanPurchaseDate":"2027-01","currentPage":1,"numPerPage":10}}
```

```json
{"result_type":"expiring_project","effective_query":{"keywords":["物业"],"beginServiceExpireTime":"2026-10-12","endServiceExpireTime":"2027-04-12","currentPage":1,"numPerPage":10}}
```

上述各例仅在与原成功输出全部条件一致时使用；有其他地区、金额、排序等字段须全部复制。公司样例见 [企业能力](capabilities/enterprise-intelligence.md)。原 API `effective_query` 无须追加金额确认字段，已执行金额直接继承；新的/改变的小额由 Agent 自行核对原话单位。完整上下文或缓存页大小超过三源 100/公司 20 时先纠正，不静默缩小改变分页；新查询默认规则不变。

`AREA_SCOPE_UNSUPPORTED`：指定区县目前只能返回更大范围，查询未发出。按 [地区规则](../SKILL.md#地区) 确认实际范围后重试，不自动替换地区编号。
