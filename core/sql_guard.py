# -*- coding: utf-8 -*-
"""
SQL 安全校验模块（SQL Guard）—— 本项目最核心的安全防线。

为什么需要它：
    让大模型直接生成 SQL 并执行，是极其危险的做法。
    模型可能生成 DROP TABLE、UPDATE、甚至多语句注入。
    本模块用「白名单 + 黑名单 + 强制改写」三层机制，确保只有只读查询能落地。

校验规则：
    1. 必须是单条语句（禁止分号拼接多语句）；
    2. 必须以 SELECT 开头（禁止 INSERT/UPDATE/DELETE/DROP/ALTER 等）；
    3. 禁止出现任何危险关键字（含注释符、PRAGMA、ATTACH 等绕过手段）；
    4. 只能查询白名单内的表；
    5. 若无 LIMIT 子句，自动补上 LIMIT，防止全表扫爆内存。
"""

import re
from typing import Tuple

from data.schema import ALLOWED_TABLES

# 危险关键字黑名单（全部转为大写后匹配）
FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
    "TRUNCATE", "ATTACH", "DETACH", "PRAGMA", "VACUUM", "GRANT", "REVOKE",
    "EXEC", "EXECUTE", "MERGE", "CALL", "COPY", "LOAD", "INTO OUTFILE",
)

# 从 SQL 中提取表名：匹配 FROM / JOIN 后面的标识符
TABLE_PATTERN = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)

# 匹配 LIMIT 子句
LIMIT_PATTERN = re.compile(r"\blimit\s+\d+", re.IGNORECASE)


class SQLGuardError(Exception):
    """SQL 未通过安全校验时抛出。"""


def _strip_sql(sql: str) -> str:
    """去掉代码块围栏、多余空白与结尾分号，做规范化。"""
    if sql is None:
        return ""
    text = sql.strip()

    # 去掉 markdown 代码块围栏，模型经常带出来
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"```\s*$", "", text)

    text = text.strip().rstrip(";").strip()
    # 压缩连续空白，避免多行 SQL 干扰关键字匹配
    text = re.sub(r"\s+", " ", text)
    return text


def validate_sql(sql: str, max_rows: int = 200) -> Tuple[str, str]:
    """
    校验并规范化 SQL。

    返回：(安全的 SQL, 提示信息)
    校验不通过时抛出 SQLGuardError。
    """
    cleaned = _strip_sql(sql)

    if not cleaned:
        raise SQLGuardError("SQL 为空，无法执行。")

    upper = cleaned.upper()

    # 规则 1：禁止多语句
    if ";" in cleaned:
        raise SQLGuardError("检测到分号，禁止一次执行多条语句。")

    # 规则 2：必须是 SELECT 开头
    if not upper.startswith("SELECT"):
        raise SQLGuardError("只允许 SELECT 只读查询，当前语句不是以 SELECT 开头。")

    # 规则 3：危险关键字黑名单
    for keyword in FORBIDDEN_KEYWORDS:
        # 用词边界匹配，避免把 created_at 之类的字段名误判
        if re.search(r"\b%s\b" % re.escape(keyword), upper):
            raise SQLGuardError("检测到禁止使用的关键字：%s" % keyword)

    # 规则 4：注释符绕过检查
    if "--" in cleaned or "/*" in cleaned:
        raise SQLGuardError("禁止在 SQL 中使用注释符。")

    # 规则 5：表名白名单
    tables = set(t.lower() for t in TABLE_PATTERN.findall(cleaned))
    if not tables:
        raise SQLGuardError("未能识别查询的表名，请确认 SQL 中包含 FROM 子句。")

    illegal = tables - set(t.lower() for t in ALLOWED_TABLES)
    if illegal:
        raise SQLGuardError("不允许查询以下表：%s" % "、".join(sorted(illegal)))

    # 规则 6：自动补 LIMIT
    note = ""
    if not LIMIT_PATTERN.search(cleaned):
        cleaned = "%s LIMIT %d" % (cleaned, max_rows)
        note = "已自动追加 LIMIT %d 以限制返回行数。" % max_rows

    return cleaned, note
