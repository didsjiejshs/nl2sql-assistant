# -*- coding: utf-8 -*-
"""
数据库连接与查询执行模块。

安全要点：
    1. 使用白名单表名，禁止访问未登记的表；
    2. 查询结果强制加行数上限，避免返回海量数据；
    3. SQL 语句本身必须先通过 sql_guard 校验才会走到这里。
"""

import os
import sqlite3
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "production.db")

MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "200"))


def get_connection() -> sqlite3.Connection:
    """获取数据库连接（行以字典形式返回，方便转 JSON）。"""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "未找到数据库文件：%s\n请先执行：python -m data.seed" % DB_PATH
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(sql: str, max_rows: int = MAX_RESULT_ROWS) -> Dict[str, Any]:
    """
    执行一条已经过安全校验的 SELECT 语句。

    返回结构：
        {"columns": [...], "rows": [[...], ...], "row_count": int, "truncated": bool}
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        fetched = cursor.fetchmany(max_rows + 1)

        truncated = len(fetched) > max_rows
        rows = [list(r) for r in fetched[:max_rows]]

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }
    finally:
        conn.close()


def get_table_overview() -> Dict[str, Any]:
    """返回数据概览，用于前端首屏展示与健康检查。"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM production_records")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT MIN(record_date), MAX(record_date) FROM production_records")
        date_range = cursor.fetchone()
        cursor.execute("SELECT DISTINCT line_name FROM production_records ORDER BY line_name")
        lines = [r[0] for r in cursor.fetchall()]
        return {
            "total_records": total,
            "date_start": date_range[0],
            "date_end": date_range[1],
            "lines": lines,
        }
    finally:
        conn.close()
