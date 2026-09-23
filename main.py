# -*- coding: utf-8 -*-
"""
Web 服务入口。

启动：
    python main.py
或：
    uvicorn main:app --reload --port 8000

启动后浏览器打开 http://127.0.0.1:8000 即可使用。
"""

import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 直接执行 python main.py 时，把项目根目录加入模块搜索路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core import llm                      # noqa: E402
from core.engine import ask               # noqa: E402
from core.sql_guard import SQLGuardError  # noqa: E402
from data.db import get_table_overview    # noqa: E402

app = FastAPI(
    title="产线数据问答助手",
    description="用自然语言查询产线生产数据：大模型生成 SQL → 安全校验 → 执行 → 自动选图与结论",
    version="1.0.0",
)

STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str


@app.get("/")
def index():
    """返回前端页面。"""
    page = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(page):
        return JSONResponse({"error": "未找到前端页面 static/index.html"}, status_code=500)
    return FileResponse(page)


@app.get("/api/health")
def health():
    """健康检查：返回服务状态、当前模型模式与数据概览。"""
    mode = "mock" if llm.is_mock_mode() else llm.get_provider()
    try:
        overview = get_table_overview()
    except FileNotFoundError as exc:
        return JSONResponse(
            {"status": "error", "mode": mode, "message": str(exc)}, status_code=503
        )
    return {"status": "ok", "mode": mode, "data": overview}


@app.get("/api/examples")
def examples():
    """返回示例问题，前端点击即可提问。"""
    return {
        "examples": [
            "各产线的总产量是多少？",
            "哪条产线的不良率最高？",
            "各产线的停机时长排名",
            "一号线的产量趋势",
            "按月统计产量和不良品数量",
            "各产线的人均产量对比",
            "产量排名前 5 的产线和产品",
        ]
    }


@app.post("/api/ask")
def api_ask(req: AskRequest):
    """核心接口：接收自然语言问题，返回 SQL、结果、图表类型与结论。"""
    try:
        return ask(req.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SQLGuardError as exc:
        raise HTTPException(status_code=403, detail="SQL 安全校验未通过：%s" % exc)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # 兜底，避免把堆栈直接抛给前端
        raise HTTPException(status_code=500, detail="服务内部错误：%s" % exc)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    print("=" * 56)
    print("  产线数据问答助手 已启动")
    print("  请用浏览器打开： http://127.0.0.1:%d" % port)
    print("  当前模型模式：%s" % ("演示模式（规则引擎）" if llm.is_mock_mode() else llm.get_provider()))
    print("  按 Ctrl + C 停止服务")
    print("=" * 56)
    uvicorn.run(app, host="127.0.0.1", port=port)
