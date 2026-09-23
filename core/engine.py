# -*- coding: utf-8 -*-
"""
核心引擎 —— 把自然语言问题，变成可执行的安全 SQL，并生成结论。

完整链路：
    用户问题
      ↓
    ① 大模型生成 SQL（未配置 Key 时降级为规则引擎）
      ↓
    ② SQL 安全校验（core/sql_guard.py）
      ↓
    ③ 执行查询（data/db.py）
      ↓
    ④ 推断最合适的图表类型
      ↓
    ⑤ 大模型基于查询结果生成业务结论
      ↓
    返回前端

这个"生成 → 校验 → 执行 → 解释"的四段式结构，
是企业级 AI 应用的标准形态：模型负责理解，代码负责兜底。
"""

import json
from typing import Any, Dict, List, Optional

from core import llm
from core.llm import LLMError
from core.rule_engine import generate_sql_by_rule
from core.sql_guard import SQLGuardError, validate_sql
from data.db import run_query
from data.schema import SCHEMA_TEXT

SQL_SYSTEM_PROMPT = """你是一个严谨的数据分析助手，负责把用户的自然语言问题转换成 SQLite 查询语句。

数据库结构如下：
{schema}

必须严格遵守以下规则：
1. 只输出一条 SELECT 语句，不要输出任何解释、说明或 markdown 代码块标记；
2. 禁止使用 INSERT、UPDATE、DELETE、DROP 等任何写操作；
3. 禁止使用分号，禁止一次返回多条语句；
4. 只能查询 production_records 这一张表；
5. 日期字段 record_date 是 'YYYY-MM-DD' 格式的文本，按月分组请用 substr(record_date, 1, 7)；
6. 不良率 = SUM(defect_qty) * 100.0 / SUM(output_qty)，保留两位小数用 ROUND(x, 2)；
7. 除非用户明确要求查看明细，否则请使用 GROUP BY 做聚合，并加上 LIMIT 限制返回行数。

只输出 SQL，不要输出其他任何内容。"""

EXPLAIN_SYSTEM_PROMPT = """你是一位制造业生产管理顾问。
用户提出了一个关于产线数据的问题，系统已经查出结果，请你用 2-3 句中文给出结论。

要求：
1. 直接给结论和业务洞察，不要复述 SQL；
2. 如果数据中存在明显异常（比如某条产线不良率显著偏高），请指出并给出可能原因；
3. 不要编造数据中不存在的信息；
4. 总字数控制在 120 字以内。"""


def infer_chart_type(columns: List[str], rows: List[List[Any]]) -> str:
    """
    根据查询结果的形状推断最合适的图表类型。

    规则：
        0 行           -> none
        只有 1 行 1 列 -> single（大数字卡片）
        含日期列       -> line
        2 列且第一列非数值 -> bar
        其他           -> table
    """
    if not rows:
        return "none"
    if len(rows) == 1 and len(columns) == 1:
        return "single"
    if any(c in ("record_date", "month") for c in columns):
        return "line"
    if len(columns) == 2:
        return "bar"
    return "table"


def _generate_sql_by_llm(question: str) -> str:
    """调用大模型生成 SQL 原始文本。"""
    prompt = SQL_SYSTEM_PROMPT.format(schema=SCHEMA_TEXT)
    raw = llm.chat(prompt, question, temperature=0.0)
    return raw


def _explain_result(question: str, columns: List[str], rows: List[List[Any]]) -> str:
    """调用大模型基于查询结果生成业务结论。"""
    preview = {
        "columns": columns,
        "rows": rows[:20],
        "total_rows": len(rows),
    }
    user_prompt = (
        "用户问题：%s\n\n"
        "查询结果（JSON，最多展示 20 行）：\n%s"
        % (question, json.dumps(preview, ensure_ascii=False))
    )
    return llm.chat(EXPLAIN_SYSTEM_PROMPT, user_prompt, temperature=0.3).strip()


def ask(question: str) -> Dict[str, Any]:
    """
    对外统一入口：提出问题，返回完整结果。

    返回值包含：sql / columns / rows / chart_type / explanation / mode / warning
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("请输入问题。")

    mode = "mock" if llm.is_mock_mode() else llm.get_provider()
    warnings: List[str] = []

    # ---------- ① 生成 SQL ----------
    raw_sql: Optional[str] = None
    rule_note = ""

    if mode == "mock":
        raw_sql, rule_note = generate_sql_by_rule(question)
        if raw_sql is None:
            raise ValueError(rule_note or "规则引擎无法解析该问题。")
    else:
        try:
            raw_sql = _generate_sql_by_llm(question)
        except LLMError as exc:
            # 大模型失败时自动降级到规则引擎，保证可用性
            warnings.append("大模型调用失败（%s），已自动切换到规则引擎。" % exc)
            mode = "mock-fallback"
            raw_sql, rule_note = generate_sql_by_rule(question)
            if raw_sql is None:
                raise ValueError("大模型不可用，且规则引擎无法解析该问题。")

    # ---------- ② SQL 安全校验 ----------
    safe_sql, guard_note = validate_sql(raw_sql)
    if guard_note:
        warnings.append(guard_note)

    # ---------- ③ 执行查询 ----------
    result = run_query(safe_sql)
    columns = result["columns"]
    rows = result["rows"]
    if result["truncated"]:
        warnings.append("结果超过上限，仅返回前 %d 行。" % len(rows))

    # ---------- ④ 推断图表 ----------
    chart_type = infer_chart_type(columns, rows)

    # ---------- ⑤ 生成业务结论 ----------
    explanation = ""
    if mode == "mock":
        explanation = rule_note or "（演示模式：配置大模型 API Key 后可自动生成业务结论）"
    else:
        try:
            explanation = _explain_result(question, columns, rows)
        except LLMError as exc:
            warnings.append("生成结论失败：%s" % exc)

    return {
        "question": question,
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "chart_type": chart_type,
        "explanation": explanation,
        "mode": mode,
        "warnings": warnings,
    }
