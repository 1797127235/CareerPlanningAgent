"""一次性迁移脚本：把所有老 coach_memo 文本迁移进 Mem0。

可选执行，不是强制——任务 C 的 _update_coach_memo 已经内置了对话时自动迁移逻辑。
这个脚本用于主动预热，避免老用户首次对话时的延迟。
"""
from __future__ import annotations

from backend.db import SessionLocal
from backend.models import Profile
from backend.services.coach.memory import migrate_legacy_memo


def main() -> None:
    db = SessionLocal()
    try:
        profiles = db.query(Profile).filter(Profile.coach_memo != "").all()
        migrated = 0
        for p in profiles:
            migrate_legacy_memo(p.user_id, p.coach_memo)
            p.coach_memo = ""
            migrated += 1
        db.commit()
        print(f"Migrated {migrated} profiles")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
