# -*- coding: utf-8 -*-
"""
SQL 安全校验模块的单元测试。

这是本项目最需要测试的部分 —— 一旦校验被绕过，就是数据安全事故。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sql_guard import SQLGuardError, validate_sql  # noqa: E402


def test_normal_select_passes():
    """正常查询应当通过，并被自动补上 LIMIT。"""
    sql, note = validate_sql("SELECT line_name, SUM(output_qty) FROM production_records GROUP BY line_name")
    assert "LIMIT" in sql.upper()
    assert note  # 有补充说明


def test_existing_limit_is_kept():
    """已有 LIMIT 时不应重复追加。"""
    sql, note = validate_sql("SELECT * FROM production_records LIMIT 10")
    assert sql.upper().count("LIMIT") == 1
    assert note == ""


def test_code_fence_is_stripped():
    """大模型常把 SQL 包在 markdown 代码块里，应当能自动剥离。"""
    sql, _ = validate_sql("```sql\nSELECT COUNT(*) FROM production_records\n```")
    assert sql.upper().startswith("SELECT")
    assert "`" not in sql


@pytest.mark.parametrize(
    "dangerous_sql",
    [
        "DROP TABLE production_records",
        "DELETE FROM production_records",
        "UPDATE production_records SET output_qty = 0",
        "INSERT INTO production_records VALUES (1)",
        "ALTER TABLE production_records ADD COLUMN x INT",
        "PRAGMA table_info(production_records)",
    ],
)
def test_write_operations_are_rejected(dangerous_sql):
    """任何写操作都必须被拒绝。"""
    with pytest.raises(SQLGuardError):
        validate_sql(dangerous_sql)


def test_multi_statement_is_rejected():
    """多语句注入必须被拒绝。"""
    with pytest.raises(SQLGuardError):
        validate_sql("SELECT * FROM production_records; DROP TABLE production_records")


def test_comment_bypass_is_rejected():
    """用注释符绕过关键字检查必须失败。"""
    with pytest.raises(SQLGuardError):
        validate_sql("SELECT * FROM production_records -- WHERE 1=1")


def test_unknown_table_is_rejected():
    """白名单之外的表必须被拒绝。"""
    with pytest.raises(SQLGuardError):
        validate_sql("SELECT * FROM users")


def test_empty_sql_is_rejected():
    with pytest.raises(SQLGuardError):
        validate_sql("   ")


def test_field_name_containing_keyword_is_allowed():
    """字段名里含关键字（如 created_at 含 CREATE）不应被误杀。"""
    sql, _ = validate_sql("SELECT created_at FROM production_records")
    assert "created_at" in sql
