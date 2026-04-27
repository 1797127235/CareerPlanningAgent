"""Demo data seed — populate fresh database with sample data.

Usage:
    python seed_demo.py

Creates:
  - Demo user (demo@careerplan.local / demo123456)
  - Sample profile with skills and projects
  - Career goal (Java 后端工程师)
  - JD diagnosis with match score and gaps
  - Growth entries (learning and project)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.auth import hash_password
from backend.db import Base, get_db, engine
from backend.models import CareerGoal, GrowthEntry, JDDiagnosis, Profile, User

Base.metadata.create_all(bind=engine)
db = next(get_db())

DEMO_EMAIL = "demo"
DEMO_PASSWORD = "demo123456"

existing = db.query(User).filter(User.username == DEMO_EMAIL).first()
if existing:
    print(f"Demo user already exists (id={existing.id}), skipping.")
    db.close()
    exit(0)

print("Seeding demo data...")

# ── 1. User ──
u = User(username=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD),
          created_at=datetime.now(timezone.utc))
db.add(u); db.flush(); uid = u.id
print(f"  User (id={uid})")

# ── 2. Profile ──
pj = json.dumps({
    "name": "张三（Demo）",
    "education": "本科 · 计算机科学与技术 · 大三",
    "skills": [{"name":"Python","level":"熟悉"},{"name":"Java","level":"掌握"},
               {"name":"Spring Boot","level":"了解"},{"name":"MySQL","level":"掌握"},{"name":"Git","level":"熟悉"}],
    "projects": [
        {"name":"校园二手交易平台","description":"Spring Boot + Vue 全栈项目"},
        {"name":"分布式爬虫课程设计","description":"Scrapy + Redis 多层爬虫"}],
    "target": "Java 后端工程师",
}, ensure_ascii=False)
p = Profile(user_id=uid, name="张三（Demo）", profile_json=pj)
db.add(p); db.flush(); pid = p.id
print(f"  Profile (id={pid})")

# ── 3. Career Goal ──
db.add(CareerGoal(user_id=uid, profile_id=pid, target_node_id="java-backend-dev",
                   target_label="Java 后端工程师",
                   gap_skills=["Spring Boot","Redis","Kafka","分布式系统设计"],
                   total_hours=120, safety_gain=35.0, tag="安全转移",
                   set_at=datetime.now(timezone.utc)))
print("  Career goal")

# ── 4. JD Diagnosis ──
result = json.dumps({
    "dimensions": {"foundation":{"score":72},"skill":{"score":55},"potential":{"score":68},"soft_skill":{"score":60}},
    "matched_skills": ["Java","MySQL","Git"],
    "gap_skills": [{"skill":"Redis","priority":"high"},{"skill":"Kafka","priority":"high"},{"skill":"Spring Boot","priority":"medium"}],
    "resume_tips": ["在项目中加入具体技术栈和量化成果","扩展为微服务架构演示项目"],
    "graph_context": {"zone":"caution","label":"Java 后端工程师","replacement_pressure":35,"human_ai_leverage":72},
}, ensure_ascii=False)
db.add(JDDiagnosis(
    user_id=uid, profile_id=pid,
    jd_title="Java 后端开发工程师 · 3-5年",
    jd_text="精通 Java/Spring Boot，熟悉 MySQL、Redis、Kafka，具备微服务架构和分布式系统设计经验",
    match_score=62,
    result_json=result,
    created_at=datetime.now(timezone.utc)))
print("  JD diagnosis (score=62)")

# ── 5. Growth Entries ──
now = datetime.now(timezone.utc)
for content, cat, tags, is_plan in [
    ("学习 Spring Boot Getting Started Guide", "learning", ["Spring Boot"], False),
    ("搭建 Redis 集群实验环境", "learning", ["Redis"], False),
    ("在二手交易平台引入 RabbitMQ 异步处理", "project", ["RabbitMQ"], True),
]:
    db.add(GrowthEntry(user_id=uid, content=content, category=cat, tags=tags,
                        is_plan=is_plan, status="pending" if is_plan else "done",
                        completed_at=None if is_plan else now))
print("  3 growth entries")

db.commit(); db.close()

print()
print("Demo data ready!")
print(f"  Login: {DEMO_EMAIL}")
print(f"  Pass:  {DEMO_PASSWORD}")
print()
print("  Start: python -m uvicorn backend.app:app --reload")
print("  Open:  http://localhost:5174")
