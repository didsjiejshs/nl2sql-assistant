# -*- coding: utf-8 -*-
"""
数据表结构定义 —— 这是大模型理解数据库的唯一依据。

设计说明：
    真实项目里，这份 schema 通常从数据库的 information_schema 自动导出，
    或者维护在一个 YAML 文件里。这里为了保持 Demo 小而清晰，直接写成常量。
"""

SCHEMA_TEXT = """
表名：production_records（产线生产日报明细表）

字段说明：
- id           INTEGER  主键，自增
- record_date  TEXT     生产日期，格式 'YYYY-MM-DD'
- line_name    TEXT     产线名称，取值：'一号线'、'二号线'、'三号线'
- product_name TEXT     产品名称，取值：'A100'、'A200'、'B100'、'B200'、'C100'、'C200'
- shift         TEXT    班次，取值：'早班'、'中班'、'夜班'
- output_qty   INTEGER  当日产量（件）
- defect_qty   INTEGER  当日不良品数量（件）
- runtime_min  INTEGER  当日有效运行时长（分钟）
- downtime_min INTEGER  当日停机时长（分钟）
- operator_cnt INTEGER  当日在岗人数（人）
"""

# 允许查询的表（白名单机制：只有列在这里的表才允许被查询）
ALLOWED_TABLES = ("production_records",)
