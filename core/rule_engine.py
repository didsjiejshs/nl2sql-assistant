# -*- coding: utf-8 -*-
"""
规则引擎（演示模式下的兜底方案）。

作用：
    没有配置大模型 API Key 时，用关键词 + 模板的方式把中文问题转成 SQL。
    这样任何人 clone 项目后都能立刻跑通，不需要先去申请 Key。

说明：
    这是"降级方案"，不是核心卖点。核心卖点是 core/engine.py 里的大模型链路。
    规则引擎只覆盖最典型的几类问法，复杂问题会提示需要配置 API Key。
"""

import re
from typing import Optional


def _has(text: str, *keywords: str) -> bool:
    return any(k in text for k in keywords)


def _extract_limit(text: str) -> int:
    """从问题里抽取 Top N 的 N。"""
    match = re.search(r"(?:top|前|排名前|最高的)\s*(\d+)", text, re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 50))
    if _has(text, "前三", "前3"):
        return 3
    if _has(text, "前五", "前5"):
        return 5
    return 5


def _extract_line(text: str) -> Optional[str]:
    for line in ("一号线", "二号线", "三号线"):
        if line in text:
            return line
    if "1号线" in text:
        return "一号线"
    if "2号线" in text:
        return "二号线"
    if "3号线" in text:
        return "三号线"
    return None


def _extract_shift(text: str) -> Optional[str]:
    for shift in ("早班", "中班", "夜班"):
        if shift in text:
            return shift
    return None


def generate_sql_by_rule(question: str):
    """
    用规则生成 SQL。

    返回：(sql, 说明) —— 无法识别时返回 (None, 提示语)
    """
    q = question.strip()
    if not q:
        return None, "问题为空。"

    line = _extract_line(q)
    shift = _extract_shift(q)
    limit = _extract_limit(q)

    # 构造 WHERE 条件
    conditions = []
    if line:
        conditions.append("line_name = '%s'" % line)
    if shift:
        conditions.append("shift = '%s'" % shift)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # 1. 不良率相关
    if _has(q, "不良率", "不良品率", "次品率", "合格率"):
        sql = (
            "SELECT line_name, "
            "ROUND(SUM(defect_qty) * 100.0 / SUM(output_qty), 2) AS defect_rate "
            "FROM production_records%s "
            "GROUP BY line_name ORDER BY defect_rate DESC" % where
        )
        return sql, "按产线统计不良率（不良品数 ÷ 产量 × 100）"

    # 2. 停机 /  downtime
    if _has(q, "停机", "故障时间", "停线"):
        sql = (
            "SELECT line_name, SUM(downtime_min) AS total_downtime "
            "FROM production_records%s "
            "GROUP BY line_name ORDER BY total_downtime DESC" % where
        )
        return sql, "按产线汇总停机时长（分钟）"

    # 3. 人均产量 / 效率
    if _has(q, "人均", "人效", "效率", "人均产量"):
        sql = (
            "SELECT line_name, "
            "ROUND(SUM(output_qty) * 1.0 / SUM(operator_cnt), 2) AS output_per_person "
            "FROM production_records%s "
            "GROUP BY line_name ORDER BY output_per_person DESC" % where
        )
        return sql, "按产线统计人均产量（总产量 ÷ 总在岗人数）"

    # 4. 趋势 / 按月 按天
    if _has(q, "趋势", "走势", "变化", "每天", "按天", "按日", "逐日"):
        sql = (
            "SELECT record_date, SUM(output_qty) AS total_output "
            "FROM production_records%s "
            "GROUP BY record_date ORDER BY record_date ASC" % where
        )
        return sql, "按日期展示产量趋势"

    if _has(q, "按月", "月度", "每月"):
        sql = (
            "SELECT substr(record_date, 1, 7) AS month, SUM(output_qty) AS total_output, "
            "SUM(defect_qty) AS total_defect "
            "FROM production_records%s "
            "GROUP BY month ORDER BY month ASC" % where
        )
        return sql, "按月汇总产量与不良品数量"

    # 5. Top N 排名
    if _has(q, "top", "前", "排名", "最高", "最多", "最好"):
        sql = (
            "SELECT line_name, product_name, SUM(output_qty) AS total_output "
            "FROM production_records%s "
            "GROUP BY line_name, product_name "
            "ORDER BY total_output DESC LIMIT %d" % (where, limit)
        )
        return sql, "按产量降序取前 %d 名" % limit

    # 6. 平均产量
    if _has(q, "平均", "均值"):
        sql = (
            "SELECT line_name, ROUND(AVG(output_qty), 2) AS avg_output "
            "FROM production_records%s "
            "GROUP BY line_name ORDER BY avg_output DESC" % where
        )
        return sql, "按产线统计平均单班产量"

    # 7. 总产量（兜底）
    if _has(q, "产量", "总产量", "产出", "多少件"):
        if line or shift:
            sql = (
                "SELECT line_name, shift, SUM(output_qty) AS total_output "
                "FROM production_records%s "
                "GROUP BY line_name, shift ORDER BY total_output DESC" % where
            )
            return sql, "按产线与班次汇总产量"
        sql = (
            "SELECT line_name, SUM(output_qty) AS total_output "
            "FROM production_records%s "
            "GROUP BY line_name ORDER BY total_output DESC" % where
        )
        return sql, "按产线汇总总产量"

    return None, (
        "演示模式（规则引擎）无法理解这个问题。\n"
        "请在 .env 中配置大模型 API Key 后重试，或点击下方的示例问题。"
    )
