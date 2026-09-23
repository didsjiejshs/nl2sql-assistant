# 产线数据问答助手 · NL2SQL Data Assistant

> 用中文提问，自动生成 SQL 并返回可视化结果 —— 一个完整可运行的 **NL2SQL（Natural Language to SQL）** 应用。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 项目解决什么问题

制造业工厂每天产生大量产线数据（产量、不良品、停机时长、在岗人数），
但业务同事**不会写 SQL**，每次想看数据都要找开发同事提需求，一来一回就是半天。

本项目把这一步自动化：**业务同事用中文问，系统自动查出数据、画出图、并给出业务结论。**

```
业务同事：  "哪条产线的不良率最高？"
              ↓
数据处理：  大模型生成 SQL → 安全校验 → 执行查询 → 推断图表 → 生成结论
              ↓
返回结果：  SQL 语句 + 柱状图 + 业务结论（"二号线不良率 3.2%，显著高于其他产线……"）
```

---

## 功能特性

| 功能 | 说明 |
|---|---|
| **自然语言转 SQL** | 支持 DeepSeek / 通义千问 / OpenAI / 本地 Ollama，全部走 OpenAI 兼容协议 |
| **SQL 安全护栏（SQL Guard）** | 白名单 + 黑名单 + 强制改写三层防护，杜绝 `DROP`／多语句注入／越权查表 |
| **自动图表推断** | 根据结果形状自动选择折线图 / 柱状图 / 数值卡片 / 表格 |
| **AI 业务结论** | 把查询结果回传给大模型，生成 2–3 句业务洞察 |
| **零配置演示模式** | 未配置任何 API Key 时自动降级为规则引擎，**clone 下来就能跑** |
| **降级容错** | 大模型调用失败时自动回退规则引擎，服务不中断 |
| **23 个单元测试** | 重点覆盖 SQL 安全校验模块 |

---

## 快速开始

### 环境要求

- Python **3.8 及以上**（推荐 3.10+）

### 三步跑起来

```bash
# （推荐）先建虚拟环境，避免污染全局 Python
# Windows:
python -m venv .venv && .venv\Scripts\activate
# macOS / Linux:
# python3 -m venv .venv && source .venv/bin/activate

# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成演示数据库（约 6500 条产线记录，只需执行一次）
python -m data.seed

# 3. 启动服务
python main.py
```

然后用浏览器打开 **http://127.0.0.1:8000** 即可使用。

> **Windows 用户如果终端输出中文乱码**，先执行：
> ```powershell
> $env:PYTHONIOENCODING='utf-8'
> ```

> **没有 API Key 也能用。** 不配置 `.env` 时，系统进入「演示模式」，
> 用内置规则引擎解析问题，功能完整可演示。

---

## 接入真正的大模型

```bash
cp .env.example .env     # Windows: copy .env.example .env
```

编辑 `.env`，填入任意一家的 API Key：

```ini
# DeepSeek（推荐：中文效果好、价格低）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的key

# 或者 阿里云百炼 / 通义千问
# LLM_PROVIDER=dashscope
# DASHSCOPE_API_KEY=sk-你的key

# 或者 本地 Ollama（完全免费、无需联网）
# LLM_PROVIDER=ollama
# OLLAMA_API_KEY=ollama
# OLLAMA_MODEL=qwen2.5:7b
```

重启服务后，页面右上角会从「演示模式」变成「在线模式」。

---

## 使用示例

启动后点击页面上方的示例标签，或直接输入下列问题：

| 提问 | 系统行为 |
|---|---|
| 各产线的总产量是多少？ | 按产线聚合，返回柱状图 |
| 哪条产线的不良率最高？ | 计算 `SUM(defect_qty)*100.0/SUM(output_qty)` 并降序 |
| 一号线的产量趋势 | 按日期分组，返回 120 天折线图 |
| 各产线的人均产量对比 | 计算 `SUM(output_qty)/SUM(operator_cnt)` |
| 产量排名前 5 的产线和产品 | Top-N 查询 |

---

## 项目结构

```
nl2sql-assistant/
├── main.py                  # FastAPI 服务入口与 4 个接口
├── requirements.txt
├── .env.example             # 环境变量模板（复制为 .env 使用）
├── core/
│   ├── engine.py            # 核心编排：生成 → 校验 → 执行 → 选图 → 结论
│   ├── sql_guard.py         # ★ SQL 安全校验（项目的安全防线）
│   ├── llm.py               # 大模型调用封装（多服务商统一接口）
│   └── rule_engine.py       # 规则引擎（无 API Key 时的降级方案）
├── data/
│   ├── schema.py            # 表结构定义（提供给大模型的上下文）
│   ├── db.py                # 数据库连接与受限查询执行
│   └── seed.py              # 演示数据生成脚本
├── static/
│   └── index.html           # 前端页面（原生 JS + ECharts，零构建）
└── tests/
    ├── test_sql_guard.py    # SQL 安全校验测试
    └── test_engine.py       # 规则引擎与图表推断测试
```

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│  前端 static/index.html （原生 JS + ECharts，无构建步骤）  │
└───────────────────────────┬─────────────────────────────┘
                            │ POST /api/ask
┌───────────────────────────▼─────────────────────────────┐
│  main.py  FastAPI 路由层                                  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  core/engine.py  编排层                                   │
│                                                          │
│   ① 生成 SQL  ──► core/llm.py（大模型）                    │
│              └──► core/rule_engine.py（降级方案）          │
│   ② 安全校验  ──► core/sql_guard.py  ◄── 关键防线          │
│   ③ 执行查询  ──► data/db.py                              │
│   ④ 图表推断  （按结果形状自动选择）                        │
│   ⑤ 生成结论  ──► core/llm.py                             │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  SQLite  production_records（6552 条产线生产记录）         │
└─────────────────────────────────────────────────────────┘
```

### 核心设计思路

**1. 大模型负责理解，代码负责兜底。**
让大模型直接生成 SQL 并执行是危险的。本项目把链路拆成「生成 → **校验** → 执行」，
模型只负责把中文翻译成 SQL，能不能执行由 `sql_guard.py` 说了算。

**2. 安全防线是三层而不是一层。**
`core/sql_guard.py` 依次校验：

1. **必须是单条语句** —— 拦截 `;` 多语句注入；
2. **必须以 SELECT 开头** —— 拦截一切写操作；
3. **危险关键字黑名单** —— `DROP` / `UPDATE` / `PRAGMA` / 注释符等；
4. **表名白名单** —— 只允许访问登记过的表；
5. **自动补 LIMIT** —— 防止全表扫爆内存。

**3. 没有 API Key 也必须能跑。**
开源项目最大的门槛是「别人跑不起来」。所以做了双引擎：
配了 Key 走大模型，没配 Key 走规则引擎，**任何人 clone 下来都能立即看到效果**。

---

## 接口说明

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 前端页面 |
| GET | `/api/health` | 健康检查，返回模型模式与数据概览 |
| GET | `/api/examples` | 返回示例问题列表 |
| POST | `/api/ask` | **核心接口**：`{"question": "各产线总产量"}` |

`/api/ask` 返回结构：

```json
{
  "question": "哪条产线的不良率最高？",
  "sql": "SELECT line_name, ROUND(SUM(defect_qty)*100.0/SUM(output_qty), 2) AS defect_rate FROM production_records GROUP BY line_name ORDER BY defect_rate DESC LIMIT 200",
  "columns": ["line_name", "defect_rate"],
  "rows": [["二号线", 3.21], ["一号线", 2.87], ["三号线", 2.64]],
  "chart_type": "bar",
  "explanation": "二号线不良率 3.21%，为三条产线中最高……",
  "mode": "deepseek",
  "warnings": []
}
```

交互式 API 文档：启动服务后访问 **http://127.0.0.1:8000/docs**（FastAPI 自动生成）。

---

## 运行测试

```bash
pytest tests -v
```

```
23 passed in 0.09s
```

---

## 后续可扩展方向

- [ ] 支持多轮对话，让用户可以追问（"那上个月呢？"）
- [ ] 引入向量检索做 Schema 召回，支持几十张表的复杂库
- [ ] 把生成过的「问题 → SQL」缓存下来，相似问题直接复用，降低 token 成本
- [ ] 接入更多数据源（MySQL / PostgreSQL / ClickHouse）
- [ ] 增加查询审计日志，记录谁在什么时候查了什么数据

---

## License

MIT License，可自由使用与修改。

---

## 关于作者

本项目为个人学习实践项目，用于验证「大模型 + 安全校验 + 数据可视化」的完整落地链路。
欢迎提 Issue 交流。