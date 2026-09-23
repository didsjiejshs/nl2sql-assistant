# -*- coding: utf-8 -*-
"""
生成演示用数据库 —— 运行一次即可。

    python -m data.seed

数据规模：120 天 × 3 条产线 × 3 个班次 × 6 种产品，约 6500 条记录。

刻意制造了三类"脏数据"，用来演示真实项目中的数据质量问题：
    1. 约 2% 的 runtime_min 为 NULL（设备未回传）
    2. 约 1% 的重复记录（同一产线同日同班次同产品重复上报）
    3. 停机时长存在少量异常值
"""

import os
import random
import sqlite3
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "production.db")

LINES = ["一号线", "二号线", "三号线"]
PRODUCTS = ["A100", "A200", "B100", "B200", "C100", "C200"]
SHIFTS = ["早班", "中班", "夜班"]

DAYS = 120

# 每条产线的产能基线（单班单产品的基准产量）
LINE_BASE = {"一号线": 95, "二号线": 86, "三号线": 78}

# 不同产品的产量差异
PRODUCT_FACTOR = {
    "A100": 1.15,
    "A200": 1.05,
    "B100": 0.95,
    "B200": 0.88,
    "C100": 0.80,
    "C200": 0.72,
}

# 班次效率差异（夜班效率最低，贴近真实产线）
SHIFT_FACTOR = {"早班": 1.00, "中班": 0.96, "夜班": 0.89}


def build_rows():
    """按天 × 产线 × 班次 × 产品生成生产记录。"""
    random.seed(20260401)  # 固定随机种子，保证每次生成的数据完全一致
    start = date.today() - timedelta(days=DAYS)
    rows = []

    for day_offset in range(DAYS):
        current = start + timedelta(days=day_offset)
        for line in LINES:
            base = LINE_BASE[line]
            for shift in SHIFTS:
                for product in PRODUCTS:
                    expected = base * PRODUCT_FACTOR[product] * SHIFT_FACTOR[shift]
                    output_qty = int(random.gauss(expected, expected * 0.08))
                    output_qty = max(output_qty, 10)

                    defect_rate = random.uniform(0.008, 0.045)
                    defect_qty = int(output_qty * defect_rate)

                    runtime_min = int(random.gauss(430, 25))
                    runtime_min = max(min(runtime_min, 480), 300)
                    downtime_min = 480 - runtime_min

                    operator_cnt = random.choice([8, 9, 10, 11, 12])

                    # 脏数据 1：约 2% 的运行时长为空（设备未回传）
                    runtime_value = None if random.random() < 0.02 else runtime_min

                    row = (
                        current.isoformat(),
                        line,
                        product,
                        shift,
                        output_qty,
                        defect_qty,
                        runtime_value,
                        downtime_min,
                        operator_cnt,
                    )
                    rows.append(row)

                    # 脏数据 2：约 1% 的重复上报
                    if random.random() < 0.01:
                        rows.append(row)

    return rows


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("已删除旧数据库：%s" % DB_PATH)

    rows = build_rows()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE production_records (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date  TEXT    NOT NULL,
                line_name    TEXT    NOT NULL,
                product_name TEXT    NOT NULL,
                shift        TEXT    NOT NULL,
                output_qty   INTEGER NOT NULL,
                defect_qty   INTEGER NOT NULL,
                runtime_min  INTEGER,
                downtime_min INTEGER NOT NULL,
                operator_cnt INTEGER NOT NULL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO production_records
                (record_date, line_name, product_name, shift,
                 output_qty, defect_qty, runtime_min, downtime_min, operator_cnt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.execute("CREATE INDEX idx_date ON production_records(record_date)")
        conn.execute("CREATE INDEX idx_line ON production_records(line_name)")
        conn.commit()
    finally:
        conn.close()

    print("数据库生成完成：%s" % DB_PATH)
    print(
        "共写入 %d 条生产记录，覆盖 %d 天 × %d 条产线 × %d 个班次 × %d 种产品。"
        % (len(rows), DAYS, len(LINES), len(SHIFTS), len(PRODUCTS))
    )


if __name__ == "__main__":
    main()
