"""
清空 zhangmingyuan 用户的成长档案数据（保留用户和档案本体）
然后重新导入更丰富的分阶段数据
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db import SessionLocal
from backend.models import (
    User, Profile, CareerGoal, ProjectRecord, ProjectLog,
    InterviewRecord, JobApplication, GrowthEntry, GrowthSnapshot,
    SkillUpdate, ActionPlanV2, ActionProgress, Report,
)

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "zhangmingyuan").first()
    if not user:
        print("User not found")
        sys.exit(1)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    # Delete in dependency order
    tables = [
        (ActionProgress, "profile_id", profile.id if profile else 0),
        (ActionPlanV2, "profile_id", profile.id if profile else 0),
        (SkillUpdate, "profile_id", profile.id if profile else 0),
        (GrowthSnapshot, "profile_id", profile.id if profile else 0),
        (GrowthEntry, "user_id", user.id),
        (InterviewRecord, "user_id", user.id),
        (JobApplication, "user_id", user.id),
        (ProjectLog, "project_id", -1),  # handled separately
        (ProjectRecord, "user_id", user.id),
        (Report, "user_id", user.id),
        (CareerGoal, "user_id", user.id),
    ]

    for model, field, val in tables:
        if field == "project_id":
            # Delete logs for user's projects
            pids = [p.id for p in db.query(ProjectRecord).filter(ProjectRecord.user_id == user.id).all()]
            if pids:
                cnt = db.query(model).filter(model.project_id.in_(pids)).delete(synchronize_session=False)
                print(f"  Deleted {cnt} {model.__tablename__}")
            continue
        cnt = db.query(model).filter(getattr(model, field) == val).delete(synchronize_session=False)
        print(f"  Deleted {cnt} {model.__tablename__}")

    db.commit()
    print("\n[OK] Cleared all growth data for zhangmingyuan")
    print("     Now run: python test_data/seed_more_data.py")
finally:
    db.close()
