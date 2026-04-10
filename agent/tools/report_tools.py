"""报告生成工具 — ReportAgent 使用的 @tool 函数。"""
from __future__ import annotations
import json
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def gather_report_data(profile_id: int) -> str:
    """收集报告素材：聚合用户画像、JD诊断、面试记录、成长数据，返回结构化文本供 LLM 撰写报告。"""
    if not profile_id:
        return "需要提供画像ID才能收集报告数据。"

    try:
        from backend.db import SessionLocal
        from backend.services.report_service import ReportService

        db = SessionLocal()
        try:
            svc = ReportService()
            return svc.gather_report_data(profile_id, db)
        finally:
            db.close()
    except Exception as e:
        logger.error("gather_report_data failed: %s", e)
        return f"收集数据时出错：{e}"


@tool
def save_report(profile_id: int, report_markdown: str, title: str = "") -> str:
    """保存报告：将 LLM 生成的 Markdown 报告存入数据库，返回报告ID。"""
    if not profile_id or not report_markdown:
        return "需要提供画像ID和报告内容。"

    try:
        from datetime import datetime, timezone
        from backend.db import SessionLocal
        from backend.db_models import Profile, Report

        db = SessionLocal()
        try:
            profile = db.query(Profile).filter_by(id=profile_id).first()
            if not profile:
                return f"未找到画像 #{profile_id}。"

            report_key = f"ai_{profile_id}_{int(datetime.now(timezone.utc).timestamp())}"
            final_title = title or f"{profile.name}的职业发展报告"

            row = Report(
                report_key=report_key,
                user_id=profile.user_id,
                title=final_title,
                summary=report_markdown[:200],
                data_json=json.dumps({
                    "version": "ai_v1",
                    "markdown": report_markdown,
                    "profile_id": profile_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False),
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            return f"报告已保存！报告ID: {row.id}，标题: {final_title}"
        finally:
            db.close()
    except Exception as e:
        logger.error("save_report failed: %s", e)
        return f"保存报告时出错：{e}"
