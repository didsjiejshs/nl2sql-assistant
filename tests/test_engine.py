# -*- coding: utf-8 -*-
"""规则引擎与图表推断的单元测试。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import infer_chart_type          # noqa: E402
from core.rule_engine import generate_sql_by_rule  # noqa: E402
from core.sql_guard import validate_sql           # noqa: E402


def test_defect_rate_question():
    sql, note = generate_sql_by_rule("哪条产线的不良率最高？")
    assert sql is not None
    assert "defect_rate" in sql
    validate_sql(sql)  # 规则生成的 SQL 也必须能通过安全校验


def test_downtime_question():
    sql, _ = generate_sql_by_rule("各产线的停机时长排名")
    assert sql is not None and "downtime_min" in sql


def test_trend_question():
    sql, _ = generate_sql_by_rule("一号线的产量趋势")
    assert sql is not None
    assert "record_date" in sql
    assert "一号线" in sql


def test_top_n_question():
    sql, _ = generate_sql_by_rule("产量排名前 3 的产线")
    assert sql is not None and "LIMIT 3" in sql.upper()


def test_unknown_question_returns_none():
    sql, note = generate_sql_by_rule("今天天气怎么样")
    assert sql is None
    assert note


def test_chart_type_single_value():
    assert infer_chart_type(["COUNT(*)"], [[42]]) == "single"


def test_chart_type_line_for_date():
    assert infer_chart_type(["record_date", "total"], [["2026-01-01", 1]]) == "line"


def test_chart_type_bar_for_two_columns():
    assert infer_chart_type(["line_name", "total"], [["一号线", 1]]) == "bar"


def test_chart_type_none_for_empty():
    assert infer_chart_type(["a"], []) == "none"
