"""
补充丰富的分阶段成长档案数据
模拟一个真实 Java 后端工程师 6 个月的成长过程

用法:
  python test_data/clear_mock_data.py   # 先清旧数据
  python test_data/seed_more_data.py    # 再导入
"""
import json, os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime, timedelta
from backend.db import SessionLocal
from backend.models import (
    User, Profile, CareerGoal, ProjectRecord, ProjectLog,
    InterviewRecord, JobApplication, GrowthEntry, GrowthSnapshot, SkillUpdate,
)


def seed():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "zhangmingyuan").first()
        if not user:
            print("[ERR] User zhangmingyuan not found. Run seed_mock_data.py first.")
            return
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not profile:
            print("[ERR] Profile not found.")
            return

        # ═══════════════════════════════════════════════════
        # 1. GrowthSnapshot — 模拟每周/双周记录，曲线更平滑
        # ═══════════════════════════════════════════════════
        existing = db.query(GrowthSnapshot).filter(GrowthSnapshot.profile_id == profile.id).count()
        if existing == 0:
            snaps = [
                # ── Phase 0: 建档 (01/15) ──
                dict(report_key="initial-assessment", target_node_id="senior-java-engineer",
                     trigger="initial", stage_completed=0,
                     readiness_score=38.0, base_score=38.0, growth_bonus=0.0,
                     four_dim_detail={"technical_depth":40,"technical_breadth":35,"project_quality":32,"soft_skills":45},
                     created_at=datetime(2025,1,15)),

                # ── Phase 0→1 过渡 ──
                dict(report_key="initial-assessment", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=0,
                     readiness_score=42.0, base_score=38.0, growth_bonus=4.0,
                     four_dim_detail={"technical_depth":44,"technical_breadth":38,"project_quality":36,"soft_skills":48},
                     created_at=datetime(2025,1,28)),

                # ── Phase 1: 基础复盘期 (02月) ──
                dict(report_key="phase1-fortnight1", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=1,
                     readiness_score=47.0, base_score=38.0, growth_bonus=9.0,
                     four_dim_detail={"technical_depth":50,"technical_breadth":42,"project_quality":40,"soft_skills":52},
                     action_progress={"total_items":3,"checked":2,"pct":66.7},
                     created_at=datetime(2025,2,5)),
                dict(report_key="phase1-fortnight2", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=1,
                     readiness_score=51.5, base_score=38.0, growth_bonus=13.5,
                     four_dim_detail={"technical_depth":54,"technical_breadth":46,"project_quality":44,"soft_skills":58},
                     action_progress={"total_items":3,"checked":3,"pct":100.0},
                     created_at=datetime(2025,2,20)),

                # ── Phase 1→2 过渡 ──
                dict(report_key="phase1-final", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=1,
                     readiness_score=55.0, base_score=38.0, growth_bonus=17.0,
                     four_dim_detail={"technical_depth":57,"technical_breadth":50,"project_quality":48,"soft_skills":62},
                     action_progress={"total_items":5,"checked":4,"pct":80.0},
                     created_at=datetime(2025,3,1)),

                # ── Phase 2: 核心突破期 (03月) ──
                dict(report_key="phase2-fortnight1", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=2,
                     readiness_score=59.0, base_score=38.0, growth_bonus=21.0,
                     four_dim_detail={"technical_depth":61,"technical_breadth":53,"project_quality":54,"soft_skills":65},
                     action_progress={"total_items":4,"checked":2,"pct":50.0},
                     created_at=datetime(2025,3,12)),
                dict(report_key="phase2-fortnight2", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=2,
                     readiness_score=63.0, base_score=38.0, growth_bonus=25.0,
                     four_dim_detail={"technical_depth":65,"technical_breadth":57,"project_quality":58,"soft_skills":68},
                     action_progress={"total_items":4,"checked":3,"pct":75.0},
                     created_at=datetime(2025,3,25)),

                # ── Phase 2→3 过渡（面试高峰后） ──
                dict(report_key="phase2-final", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=2,
                     readiness_score=67.0, base_score=38.0, growth_bonus=29.0,
                     four_dim_detail={"technical_depth":68,"technical_breadth":61,"project_quality":63,"soft_skills":73},
                     action_progress={"total_items":4,"checked":4,"pct":100.0},
                     created_at=datetime(2025,4,5)),

                # ── Phase 3: 冲刺期 (04月) ──
                dict(report_key="phase3-fortnight1", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=3,
                     readiness_score=70.5, base_score=38.0, growth_bonus=32.5,
                     four_dim_detail={"technical_depth":71,"technical_breadth":64,"project_quality":67,"soft_skills":77},
                     action_progress={"total_items":3,"checked":2,"pct":66.7},
                     created_at=datetime(2025,4,15)),
                dict(report_key="phase3-fortnight2", target_node_id="senior-java-engineer",
                     trigger="stage_complete", stage_completed=3,
                     readiness_score=74.0, base_score=38.0, growth_bonus=36.0,
                     four_dim_detail={"technical_depth":74,"technical_breadth":67,"project_quality":70,"soft_skills":80},
                     action_progress={"total_items":3,"checked":3,"pct":100.0},
                     created_at=datetime(2025,4,28)),

                # ── Phase 3 完成 + 深度重评 ──
                dict(report_key="phase3-reeval", target_node_id="senior-java-engineer",
                     trigger="deep_reeval", stage_completed=3,
                     readiness_score=78.0, base_score=38.0, growth_bonus=40.0,
                     four_dim_detail={"technical_depth":78,"technical_breadth":70,"project_quality":75,"soft_skills":82},
                     action_progress={"total_items":6,"checked":6,"pct":100.0},
                     created_at=datetime(2025,5,10)),

                # ── Phase 4: 新方向启动（架构师） ──
                dict(report_key="architect-initial", target_node_id="architect",
                     trigger="deep_reeval", stage_completed=0,
                     readiness_score=52.0, base_score=52.0, growth_bonus=0.0,
                     four_dim_detail={"technical_depth":78,"technical_breadth":70,"project_quality":75,"soft_skills":55},
                     created_at=datetime(2025,5,15)),

                # ── Phase 4 成长中 ──
                dict(report_key="architect-fortnight1", target_node_id="architect",
                     trigger="stage_complete", stage_completed=1,
                     readiness_score=56.0, base_score=52.0, growth_bonus=4.0,
                     four_dim_detail={"technical_depth":80,"technical_breadth":72,"project_quality":76,"soft_skills":58},
                     action_progress={"total_items":2,"checked":1,"pct":50.0},
                     created_at=datetime(2025,5,28)),
                dict(report_key="architect-fortnight2", target_node_id="architect",
                     trigger="stage_complete", stage_completed=1,
                     readiness_score=60.0, base_score=52.0, growth_bonus=8.0,
                     four_dim_detail={"technical_depth":82,"technical_breadth":74,"project_quality":78,"soft_skills":62},
                     action_progress={"total_items":2,"checked":2,"pct":100.0},
                     created_at=datetime(2025,6,10)),

                # ── Phase 4 → Phase 2 ──
                dict(report_key="architect-phase2-start", target_node_id="architect",
                     trigger="stage_complete", stage_completed=2,
                     readiness_score=64.0, base_score=52.0, growth_bonus=12.0,
                     four_dim_detail={"technical_depth":83,"technical_breadth":76,"project_quality":80,"soft_skills":65},
                     action_progress={"total_items":3,"checked":1,"pct":33.3},
                     created_at=datetime(2025,6,25)),
            ]
            for s in snaps:
                db.add(GrowthSnapshot(profile_id=profile.id, **s))
            db.flush()
            print(f"[OK] {len(snaps)} growth snapshots (38%->78%(Java)->64%(Architect))")
        else:
            print(f"[SKIP] {existing} snapshots exist")

        # ═══════════════════════════════════════════════════
        # 2. GrowthEntry — 按阶段分布，模拟真实学习节奏
        # ═══════════════════════════════════════════════════
        existing_e = db.query(GrowthEntry).filter(GrowthEntry.user_id == user.id).count()
        if existing_e == 0:
            entries = [
                # ── Phase 0: 建档期 (01月) — 自我评估+补基础 ──
                dict(content="完成初始能力评估：Java基础OK，JVM/分布式/系统设计薄弱", category="career", tags=["自我评估","建档"], is_plan=False, status="done", completed_at=datetime(2025,1,15)),
                dict(content="精读《深入理解JVM》1-7章：内存模型、GC算法、类加载机制", category="learning", tags=["JVM","读书笔记"], structured_data={"type":"book","hours":30}, is_plan=False, status="done", completed_at=datetime(2025,1,20)),
                dict(content="JVM实战：用VisualVM分析线上OOM，定位到ThreadLocal泄漏", category="learning", tags=["JVM","实战","OOM"], structured_data={"type":"practice","hours":6}, is_plan=False, status="done", completed_at=datetime(2025,1,23)),
                dict(content="整理Spring Boot核心：Bean生命周期+自动配置+条件注解源码", category="learning", tags=["Spring Boot","源码"], structured_data={"type":"self_study","hours":10}, is_plan=False, status="done", completed_at=datetime(2025,1,25)),
                dict(content="用STAR法则重写简历项目经历，补充QPS/RT/数据量指标", category="career", tags=["简历优化"], is_plan=False, status="done", completed_at=datetime(2025,1,28)),
                dict(content="Git工作流复习：rebase vs merge，cherry-pick实践", category="learning", tags=["Git","工程化"], structured_data={"type":"self_study","hours":3}, is_plan=False, status="done", completed_at=datetime(2025,1,30)),

                # ── Phase 1: 基础复盘期 (02月) ──
                dict(content="MySQL深入：InnoDB Buffer Pool/索引下推/MVCC/Gap Lock", category="learning", tags=["MySQL","底层原理"], structured_data={"type":"self_study","hours":15}, is_plan=False, status="done", completed_at=datetime(2025,2,3)),
                dict(content="Redis深入：跳表/压缩列表/RDB-AOF混合持久化/主从复制/Sentinel", category="learning", tags=["Redis","底层原理"], structured_data={"type":"self_study","hours":12}, is_plan=False, status="done", completed_at=datetime(2025,2,8)),
                dict(content="Redis实战：用Lua脚本实现分布式限流器，对比令牌桶和漏桶", category="learning", tags=["Redis","限流","Lua"], structured_data={"type":"practice","hours":8}, is_plan=False, status="done", completed_at=datetime(2025,2,12)),
                dict(content="K8s入门：Pod/Service/Deployment/ConfigMap，Minikube部署Spring Boot", category="learning", tags=["Kubernetes","云原生"], structured_data={"type":"course","hours":18}, is_plan=False, status="done", completed_at=datetime(2025,2,15)),
                dict(content="Dockerfile最佳实践：多阶段构建+安全基线+镜像瘦身(1.2G→280M)", category="learning", tags=["Docker","工程化"], structured_data={"type":"practice","hours":4}, is_plan=False, status="done", completed_at=datetime(2025,2,18)),
                dict(content="LeetCode周赛参加3次，最高排名1200/4000，DP是弱项", category="learning", tags=["算法","周赛"], structured_data={"type":"contest","count":3}, is_plan=False, status="done", completed_at=datetime(2025,2,22)),
                dict(content="团队内部做了一次Redis分享，收到正向反馈", category="career", tags=["技术分享","Redis"], structured_data={"type":"share","audience":15}, is_plan=False, status="done", completed_at=datetime(2025,2,25)),

                # ── Phase 2: 核心突破期 (03月) — 面试高峰 ──
                dict(content="MIT 6.824 Lab1 MapReduce + Lab2 Raft选举（Go实现）", category="learning", tags=["分布式","Raft","Go"], structured_data={"type":"course","hours":25}, is_plan=False, status="done", completed_at=datetime(2025,3,3)),
                dict(content="消息队列横向对比：RabbitMQ vs Kafka vs RocketMQ 适用场景", category="learning", tags=["消息队列","选型"], structured_data={"type":"self_study","hours":6}, is_plan=False, status="done", completed_at=datetime(2025,3,6)),
                dict(content="字节二面复盘：系统设计没有框架，想到什么说什么", category="interview", tags=["面试复盘","系统设计"], structured_data={"company":"字节跳动","result":"failed"}, is_plan=False, status="done", completed_at=datetime(2025,3,8)),
                dict(content="学习系统设计框架：需求分析→容量估算→API设计→数据模型→扩展性", category="learning", tags=["系统设计","方法论"], structured_data={"type":"self_study","hours":8}, is_plan=False, status="done", completed_at=datetime(2025,3,12)),
                dict(content="练习3个系统设计题：短链/秒杀/Feed流，每道写完整方案", category="learning", tags=["系统设计","练习"], structured_data={"type":"practice","hours":12}, is_plan=False, status="done", completed_at=datetime(2025,3,16)),
                dict(content="美团一面复盘：Java基础和MySQL讲得很顺，项目深挖也能答", category="interview", tags=["面试复盘","美团"], structured_data={"company":"美团","result":"passed"}, is_plan=False, status="done", completed_at=datetime(2025,3,18)),
                dict(content="美团二面复盘：秒杀设计有体系，面试官说方案可落地", category="interview", tags=["面试复盘","offer"], structured_data={"company":"美团","result":"passed"}, is_plan=False, status="done", completed_at=datetime(2025,3,21)),
                dict(content="蚂蚁二面复盘：Raft和RPC原理答得不好，中间件深度不够", category="interview", tags=["面试复盘","分布式"], structured_data={"company":"蚂蚁集团","result":"failed"}, is_plan=False, status="done", completed_at=datetime(2025,3,26)),
                dict(content="Kafka深入：Broker存储架构/Consumer重平衡策略/Exactly-Once语义", category="learning", tags=["Kafka","中间件"], structured_data={"type":"self_study","hours":12}, is_plan=False, status="done", completed_at=datetime(2025,3,30)),

                # ── Phase 3: 冲刺期 (04-05月) — offer + 深化 ──
                dict(content="Spring Cloud全栈实践：Nacos注册/配置中心+Sentinel限流+Seata分布式事务+Gateway", category="learning", tags=["Spring Cloud","微服务"], structured_data={"type":"course","hours":22}, is_plan=False, status="done", completed_at=datetime(2025,4,3)),
                dict(content="微服务拆分实战：按业务域拆分单体，识别限界上下文", category="learning", tags=["微服务","DDD"], structured_data={"type":"practice","hours":8}, is_plan=False, status="done", completed_at=datetime(2025,4,8)),
                dict(content="[MILESTONE] 获得美团Java后端Offer！25K×15，4月入职", category="milestone", tags=["offer","美团"], structured_data={"company":"美团","package":"25K×15"}, is_plan=False, status="done", completed_at=datetime(2025,4,10)),
                dict(content="API网关项目完成：路由+令牌桶限流+JWT鉴权+责任链，完整README", category="project", tags=["API网关","Netty"], is_plan=False, status="done", completed_at=datetime(2025,4,15)),
                dict(content="[MILESTONE] LeetCode 200题达成！DP正确率从40%提升到75%", category="milestone", tags=["算法","LeetCode"], structured_data={"total":200,"dp_accuracy":"75%"}, is_plan=False, status="done", completed_at=datetime(2025,4,18)),
                dict(content="MySQL索引优化实战：慢查询从3s优化到50ms，联合索引+覆盖索引", category="learning", tags=["MySQL","优化","慢查询"], structured_data={"type":"practice","hours":6}, is_plan=False, status="done", completed_at=datetime(2025,4,22)),
                dict(content="Shopee英文面试准备：技术名词英文化+Design英文表述练习", category="career", tags=["面试准备","英文"], structured_data={"type":"practice","hours":10}, is_plan=False, status="done", completed_at=datetime(2025,4,28)),
                dict(content="Shopee技术面复盘：英文面适应比想象快，算法偏多但都写出来了", category="interview", tags=["面试复盘","offer","Shopee"], structured_data={"company":"Shopee","result":"passed"}, is_plan=False, status="done", completed_at=datetime(2025,5,5)),
                dict(content="[MILESTONE] 获得Shopee Backend Engineer Offer！$8K SGD/mo", category="milestone", tags=["offer","Shopee"], structured_data={"company":"Shopee","package":"$8K SGD/mo"}, is_plan=False, status="done", completed_at=datetime(2025,5,8)),
                dict(content="深度重评：Java后端目标达成(78%)，决定转向架构师方向", category="career", tags=["深度重评","方向调整"], structured_data={"old_target":"senior-java-engineer","new_target":"architect","reason":"offer已拿，追求更高"}, is_plan=False, status="done", completed_at=datetime(2025,5,10)),

                # ── Phase 4: 架构师方向 (05-06月) ──
                dict(content="阅读《软件架构：架构模式》+《架构整洁之道》，整理架构思维导图", category="learning", tags=["架构","读书笔记"], structured_data={"type":"book","hours":20}, is_plan=False, status="done", completed_at=datetime(2025,5,18)),
                dict(content="学习DDD领域驱动设计：聚合根/值对象/领域事件/限界上下文", category="learning", tags=["DDD","架构"], structured_data={"type":"course","hours":15}, is_plan=False, status="done", completed_at=datetime(2025,5,22)),
                dict(content="手写RPC框架完成：Protobuf+Netty+ZK服务发现+随机/轮询负载均衡", category="project", tags=["RPC","Netty","架构"], is_plan=False, status="done", completed_at=datetime(2025,5,30)),
                dict(content="K8s进阶：Operator模式/Helm Chart/Istio服务网格实践", category="learning", tags=["Kubernetes","Istio","云原生"], structured_data={"type":"self_study","hours":15}, is_plan=False, status="done", completed_at=datetime(2025,6,3)),
                dict(content="高可用架构学习：熔断/降级/限流/灰度发布/蓝绿部署", category="learning", tags=["高可用","架构"], structured_data={"type":"course","hours":10}, is_plan=False, status="done", completed_at=datetime(2025,6,8)),
                dict(content="整理架构师能力模型：技术深度+系统设计+技术决策+团队影响力", category="career", tags=["架构师","能力模型"], is_plan=False, status="done", completed_at=datetime(2025,6,12)),
                dict(content="参与公司技术方案评审，提出缓存一致性方案被采纳", category="career", tags=["技术决策","影响力"], is_plan=False, status="done", completed_at=datetime(2025,6,18)),
                dict(content="给团队做了一次架构演进分享：从单体到微服务的踩坑经验", category="career", tags=["技术分享","架构","影响力"], structured_data={"type":"share","audience":25}, is_plan=False, status="done", completed_at=datetime(2025,6,22)),

                # ── 计划（未完成） ──
                dict(content="深入RocketMQ源码：CommitLog/Pull消费/HA主从同步", category="learning", tags=["RocketMQ","源码","计划"], is_plan=True, status="pending", due_type="monthly", due_at=datetime(2025,7,15)),
                dict(content="练习5个架构设计题：IM系统/支付系统/推荐系统/搜索系统/配置中心", category="learning", tags=["架构设计","计划"], is_plan=True, status="pending", due_type="monthly", due_at=datetime(2025,7,31)),
                dict(content="写3篇技术博客+2次团队技术分享，建立技术影响力", category="career", tags=["技术影响力","计划"], is_plan=True, status="pending", due_type="quarterly", due_at=datetime(2025,9,30)),
                dict(content="学习Service Mesh实战：Istio流量管理+可观测性+安全策略", category="learning", tags=["Service Mesh","Istio","计划"], is_plan=True, status="pending", due_type="monthly", due_at=datetime(2025,8,15)),
                dict(content="准备架构师认证考试（阿里云/腾讯云）", category="career", tags=["认证","计划"], is_plan=True, status="pending", due_type="quarterly", due_at=datetime(2025,10,31)),
            ]
            for e in entries:
                db.add(GrowthEntry(user_id=user.id, **e))
            db.flush()
            print(f"[OK] {len(entries)} growth entries")
        else:
            print(f"[SKIP] {existing_e} entries exist")

        # ═══════════════════════════════════════════════════
        # 3. SkillUpdate — 技能变更记录
        # ═══════════════════════════════════════════════════
        existing_su = db.query(SkillUpdate).filter(SkillUpdate.profile_id == profile.id).count()
        if existing_su == 0:
            updates = [
                # Phase 0
                dict(update_type="skill", content={"skill":"JVM调优","evidence":"精读《深入理解JVM》+OOM实战分析","hours":36}, source="manual", created_at=datetime(2025,1,23)),
                dict(update_type="skill", content={"skill":"Spring Boot","evidence":"Bean生命周期+自动配置源码整理","hours":10}, source="manual", created_at=datetime(2025,1,25)),
                dict(update_type="skill", content={"skill":"Git工程化","evidence":"rebase/cherry-pick/pipeline配置","hours":3}, source="manual", created_at=datetime(2025,1,30)),
                # Phase 1
                dict(update_type="skill", content={"skill":"MySQL深入","evidence":"Buffer Pool/MVCC/Gap Lock/索引下推","hours":15}, source="manual", created_at=datetime(2025,2,3)),
                dict(update_type="skill", content={"skill":"Redis深入","evidence":"跳表/RDB-AOF混合/Sentinel/Lua限流","hours":20}, source="manual", created_at=datetime(2025,2,12)),
                dict(update_type="skill", content={"skill":"Kubernetes基础","evidence":"Minikube部署+核心概念+Docker优化","hours":22}, source="manual", created_at=datetime(2025,2,18)),
                dict(update_type="skill", content={"skill":"算法竞赛","evidence":"3次LeetCode周赛，最高排名Top30%","hours":8}, source="manual", created_at=datetime(2025,2,22)),
                # Phase 2
                dict(update_type="skill", content={"skill":"分布式理论","evidence":"MIT 6.824 Lab1+Lab2 Raft实现","hours":25}, source="manual", created_at=datetime(2025,3,3)),
                dict(update_type="skill", content={"skill":"系统设计","evidence":"框架学习+3题练习(短链/秒杀/Feed)","hours":20}, source="manual", created_at=datetime(2025,3,16)),
                dict(update_type="project", content={"project":"分布式任务调度系统","skills":["Java","Quartz","RabbitMQ"],"status":"completed"}, source="manual", created_at=datetime(2025,3,20)),
                dict(update_type="skill", content={"skill":"Kafka深入","evidence":"Broker存储/Consumer重平衡/Exactly-Once","hours":12}, source="manual", created_at=datetime(2025,3,30)),
                # Phase 3
                dict(update_type="skill", content={"skill":"Spring Cloud","evidence":"Nacos/Sentinel/Seata/Gateway全栈","hours":22}, source="manual", created_at=datetime(2025,4,3)),
                dict(update_type="skill", content={"skill":"微服务架构","evidence":"DDD拆分+限界上下文识别","hours":8}, source="manual", created_at=datetime(2025,4,8)),
                dict(update_type="project", content={"project":"微服务API网关","skills":["Java","Netty","JWT","Redis","Lua"],"status":"completed"}, source="manual", created_at=datetime(2025,4,15)),
                dict(update_type="skill", content={"skill":"MySQL优化","evidence":"慢查询3s→50ms+索引优化实战","hours":6}, source="manual", created_at=datetime(2025,4,22)),
                dict(update_type="skill", content={"skill":"英文技术面试","evidence":"Shopee英文面通过+Design英文表述","hours":10}, source="manual", created_at=datetime(2025,4,28)),
                # Phase 4
                dict(update_type="skill", content={"skill":"架构设计","evidence":"《架构整洁之道》+DDD+架构思维导图","hours":35}, source="manual", created_at=datetime(2025,5,22)),
                dict(update_type="project", content={"project":"简易RPC框架","skills":["Java","Netty","Protobuf","ZooKeeper"],"status":"completed"}, source="manual", created_at=datetime(2025,5,30)),
                dict(update_type="skill", content={"skill":"Kubernetes进阶","evidence":"Operator/Helm/Istio服务网格","hours":15}, source="manual", created_at=datetime(2025,6,3)),
                dict(update_type="skill", content={"skill":"高可用架构","evidence":"熔断/降级/限流/灰度/蓝绿部署","hours":10}, source="manual", created_at=datetime(2025,6,8)),
                dict(update_type="skill", content={"skill":"技术影响力","evidence":"方案评审+架构分享(25人)","hours":5}, source="manual", created_at=datetime(2025,6,22)),
            ]
            for u in updates:
                db.add(SkillUpdate(profile_id=profile.id, **u))
            db.flush()
            print(f"[OK] {len(updates)} skill updates")
        else:
            print(f"[SKIP] {existing_su} skill updates exist")

        # ═══════════════════════════════════════════════════
        # 4. JobApplication — 更多投递记录
        # ═══════════════════════════════════════════════════
        existing_a = db.query(JobApplication).filter(JobApplication.user_id == user.id).count()
        if existing_a == 0:
            for a in [
                # Phase 1 投递（试水）
                dict(company="小红书", position="Java后端-社区", status="rejected", applied_at=datetime(2025,2,5), interview_at=datetime(2025,2,18), completed_at=datetime(2025,2,25), reflection="面试太紧张，基础题没答好"),
                dict(company="快手", position="Java开发-电商", status="rejected", applied_at=datetime(2025,2,10), interview_at=datetime(2025,2,22), completed_at=datetime(2025,3,1), reflection="算法没写出来，DP是弱项"),
                # Phase 2 投递（正式面试季）
                dict(company="字节跳动", position="Java后端-抖音电商", status="rejected", applied_at=datetime(2025,2,20), interview_at=datetime(2025,3,5), completed_at=datetime(2025,3,10), reflection="二面系统设计挂了"),
                dict(company="美团", position="Java后端-到店", status="offered", applied_at=datetime(2025,3,1), interview_at=datetime(2025,3,15), completed_at=datetime(2025,4,10), reflection="系统设计有进步，注重量化"),
                dict(company="蚂蚁集团", position="Java开发-中间件", status="rejected", applied_at=datetime(2025,3,10), interview_at=datetime(2025,3,22), completed_at=datetime(2025,4,2), reflection="中间件深度不够"),
                dict(company="拼多多", position="服务端-基础架构", status="ghosted", applied_at=datetime(2025,3,15)),
                # Phase 3 投递（冲刺）
                dict(company="携程", position="Java后端-国际业务", status="withdrawn", applied_at=datetime(2025,4,5), completed_at=datetime(2025,4,12), reflection="已有美团offer，放弃"),
                dict(company="Shopee", position="Backend Engineer-Payment", status="offered", applied_at=datetime(2025,4,20), interview_at=datetime(2025,5,5), completed_at=datetime(2025,6,1), reflection="英文面，算法偏多"),
                dict(company="阿里巴巴", position="Java高级-淘天", status="interviewing", applied_at=datetime(2025,5,15), interview_at=datetime(2025,6,5)),
                dict(company="腾讯", position="后端开发-微信支付", status="applied", applied_at=datetime(2025,6,1)),
            ]:
                db.add(JobApplication(user_id=user.id, **a))
            db.flush()
            print("[OK] 10 job applications")
        else:
            print(f"[SKIP] {existing_a} applications exist")

        # ═══════════════════════════════════════════════════
        # 5. InterviewRecord — 更详细的面试记录
        # ═══════════════════════════════════════════════════
        existing_iv = db.query(InterviewRecord).filter(InterviewRecord.user_id == user.id).count()
        if existing_iv == 0:
            apps = db.query(JobApplication).filter(JobApplication.user_id == user.id).order_by(JobApplication.id).all()
            app_map = {a.company: a.id for a in apps}
            for iv in [
                # 小红书（试水挂了）
                dict(application_id=app_map.get("小红书"), company="小红书", position="Java后端", round="技术一面", content_summary="HashMap底层数据结构/ConcurrentHashMap/synchronized vs ReentrantLock/单例模式", self_rating="medium", result="failed", stage="rejected", reflection="紧张，HashMap扩容细节讲错了", ai_analysis=json.dumps({"strengths":["基础概念了解"],"weaknesses":["细节不准","紧张影响发挥"],"action_items":["重做HashMap源码","模拟面试练心态"],"overall":"基础不扎实+心态问题"},ensure_ascii=False), interview_at=datetime(2025,2,18)),

                # 快手（算法挂）
                dict(application_id=app_map.get("快手"), company="快手", position="Java开发", round="技术一面", content_summary="Java线程池参数/volatile/LRU手撕/二叉树层序遍历", self_rating="medium", result="failed", stage="rejected", reflection="LRU没写出来，DP也是短板", ai_analysis=json.dumps({"strengths":["并发概念OK"],"weaknesses":["算法不行","手撕代码弱"],"action_items":["LeetCode每日2题","LRU必刷题"],"overall":"算法是硬伤需加强"},ensure_ascii=False), interview_at=datetime(2025,2,22)),

                # 字节（二面挂）
                dict(application_id=app_map.get("字节跳动"), company="字节跳动", position="Java后端", round="技术一面", content_summary="HashMap/ConcurrentHashMap/JVM G1 GC/LRU手撕/MySQL索引", self_rating="good", result="passed", stage="interviewing", reflection="一面基础扎实", ai_analysis=json.dumps({"strengths":["Java基础扎实","GC理解深入"],"weaknesses":["G1细节不够深"],"action_items":["深入G1/ZGC源码"],"overall":"基础过关JVM需补"},ensure_ascii=False), interview_at=datetime(2025,3,5)),
                dict(application_id=app_map.get("字节跳动"), company="字节跳动", position="Java后端", round="技术二面", content_summary="设计短链接/Redis集群/分布式事务/消息幂等", self_rating="medium", result="failed", stage="rejected", reflection="系统设计没有框架，想到什么说什么", ai_analysis=json.dumps({"strengths":["思路方向正确"],"weaknesses":["没有系统设计框架","缺量化分析"],"action_items":["学习系统设计框架","练3道Design题"],"overall":"系统设计需加强方法论"},ensure_ascii=False), interview_at=datetime(2025,3,8)),

                # 美团（3轮全过→offer）
                dict(application_id=app_map.get("美团"), company="美团", position="Java后端", round="技术一面", content_summary="线程池核心参数/Spring Bean生命周期/MySQL MVCC/二叉树层序遍历", self_rating="good", result="passed", stage="interviewed", reflection="线程池和事务讲得透", interview_at=datetime(2025,3,15)),
                dict(application_id=app_map.get("美团"), company="美团", position="Java后端", round="技术二面", content_summary="设计秒杀系统/微服务拆分策略/Kafka如何保证不丢失", self_rating="good", result="passed", stage="interviewed", reflection="秒杀设计有体系，面试官认可", ai_analysis=json.dumps({"strengths":["秒杀设计完整","微服务理解到位"],"weaknesses":["Kafka消费幂等细节模糊"],"action_items":["Kafka Exactly-Once深入"],"overall":"系统设计进步明显"},ensure_ascii=False), interview_at=datetime(2025,3,18)),
                dict(application_id=app_map.get("美团"), company="美团", position="Java后端", round="HR面", content_summary="职业规划/遇到最大困难/为什么选美团/期望薪资", self_rating="good", result="passed", stage="offered", reflection="沟通顺畅，真诚表达", interview_at=datetime(2025,3,20)),

                # 蚂蚁（中间件深度不够）
                dict(application_id=app_map.get("蚂蚁集团"), company="蚂蚁集团", position="Java开发", round="技术一面", content_summary="Java内存模型/ConcurrentHashMap/线程池/MySQL索引", self_rating="good", result="passed", stage="interviewing", reflection="一面基础题答得不错", interview_at=datetime(2025,3,22)),
                dict(application_id=app_map.get("蚂蚁集团"), company="蚂蚁集团", position="Java开发", round="技术二面", content_summary="分布式ID方案/Raft协议/RPC框架设计/RocketMQ存储模型", self_rating="bad", result="failed", stage="rejected", reflection="Raft和RPC超出当前水平", ai_analysis=json.dumps({"strengths":["Snowflake了解"],"weaknesses":["Raft只有概念","RPC无实践经验"],"action_items":["完成MIT 6.824","手写RPC框架"],"overall":"中间件深度不够需补课"},ensure_ascii=False), interview_at=datetime(2025,3,25)),

                # Shopee（英文面→offer）
                dict(application_id=app_map.get("Shopee"), company="Shopee", position="Backend Engineer", round="技术一面(英文)", content_summary="Design a rate limiter/Consistent hashing/Thread-safe LRU/JMM", self_rating="good", result="passed", stage="interviewing", reflection="英文面试比想象顺利，技术词汇准备充分", ai_analysis=json.dumps({"strengths":["英文表述OK","Design有框架"],"weaknesses":["偶有语法错误"],"action_items":["继续英文练习"],"overall":"英文面适应良好"},ensure_ascii=False), interview_at=datetime(2025,5,5)),
                dict(application_id=app_map.get("Shopee"), company="Shopee", position="Backend Engineer", round="技术二面(英文)", content_summary="Design a distributed cache/Merge K sorted lists/Kafka consumer group", self_rating="good", result="passed", stage="offered", reflection="分布式缓存设计讲得清晰，算法也写出来了", interview_at=datetime(2025,5,10)),

                # 阿里（进行中）
                dict(application_id=app_map.get("阿里巴巴"), company="阿里巴巴", position="Java高级", round="技术一面", content_summary="JVM调优经验/Spring循环依赖/Redis集群/分布式事务", self_rating="good", result="pending", stage="interviewing", reflection="等结果中", interview_at=datetime(2025,6,5)),
            ]:
                db.add(InterviewRecord(user_id=user.id, profile_id=profile.id, **iv))
            db.flush()
            print("[OK] 12 interview records")
        else:
            print(f"[SKIP] {existing_iv} interviews exist")

        # ═══════════════════════════════════════════════════
        # 6. Projects + Logs — 更真实的项目记录
        # ═══════════════════════════════════════════════════
        existing_p = db.query(ProjectRecord).filter(ProjectRecord.user_id == user.id).count()
        if existing_p == 0:
            P = []
            for p in [
                dict(name="校园二手交易平台", description="Spring Boot+Vue全栈，Redis分布式锁+WebSocket即时通讯+ES搜索", skills_used=["Java","Spring Boot","MySQL","Redis","WebSocket","Elasticsearch"], gap_skill_links=["Redis","微服务"], github_url="https://github.com/zhangmingyuan/campus-trade", status="completed", linked_node_id="senior-java-engineer", reflection="Redisson分布式锁三次重构是最大收获", started_at=datetime(2024,9,1), completed_at=datetime(2024,12,15)),
                dict(name="分布式任务调度系统", description="Quartz调度中心，Mod分片+失败重试+死信队列+监控告警", skills_used=["Java","Quartz","Spring Boot","MySQL","RabbitMQ"], gap_skill_links=["系统架构设计","性能调优"], github_url="https://github.com/zhangmingyuan/task-scheduler", status="completed", linked_node_id="senior-java-engineer", reflection="参考ElasticJob设计分片，学到不少", started_at=datetime(2025,1,5), completed_at=datetime(2025,3,20)),
                dict(name="微服务API网关", description="仿Spring Cloud Gateway，路由匹配+令牌桶限流+JWT鉴权+责任链过滤器", skills_used=["Java","Netty","Spring Cloud Gateway","JWT","Redis","Lua"], gap_skill_links=["Kubernetes","系统架构设计"], github_url="https://github.com/zhangmingyuan/api-gateway", status="completed", linked_node_id="architect", reflection="Lua原子性限流+Netty高性能是亮点", started_at=datetime(2025,4,1), completed_at=datetime(2025,5,10)),
                dict(name="LeetCode每日打卡", description="每天1-2题，DP/图论/二分/滑动窗口专题", skills_used=["Java","Python","算法"], gap_skill_links=[], github_url="https://github.com/zhangmingyuan/leetcode", status="in_progress", linked_node_id="senior-java-engineer", started_at=datetime(2025,1,1)),
                dict(name="简易RPC框架", description="Protobuf序列化+Netty通信+ZK服务发现+随机/轮询负载均衡", skills_used=["Java","Netty","Protobuf","ZooKeeper"], gap_skill_links=["RPC框架设计"], github_url="https://github.com/zhangmingyuan/simple-rpc", status="completed", linked_node_id="architect", reflection="从0到1搭建，对RPC理解质的飞跃", started_at=datetime(2025,5,15), completed_at=datetime(2025,5,30)),
                dict(name="配置中心", description="仿Apollo，长轮询配置推送+多环境管理+灰度发布", skills_used=["Java","Spring Boot","MySQL","Long Polling"], gap_skill_links=["分布式配置"], github_url="https://github.com/zhangmingyuan/config-center", status="in_progress", linked_node_id="architect", started_at=datetime(2025,6,5)),
            ]:
                obj = ProjectRecord(user_id=user.id, profile_id=profile.id, **p)
                db.add(obj); P.append(obj)
            db.flush()

            for pid,c,r,ts,dt in [
                # 校园二手交易平台
                (P[0].id,"初始化：Spring Boot 2.7+MyBatis-Plus+Vue3","第一次搭前后端分离骨架","done",datetime(2024,9,3)),
                (P[0].id,"JWT+Redis会话管理","JWT无状态适合前后端分离","done",datetime(2024,9,10)),
                (P[0].id,"ES全文检索接入","查询DSL和SQL思维差异大","done",datetime(2024,9,25)),
                (P[0].id,"Redis分布式锁防超卖","最有价值的技术决策","done",datetime(2024,10,15)),
                (P[0].id,"Redisson重写分布式锁","三次重构，终于理解看门狗","done",datetime(2024,10,28)),
                (P[0].id,"WebSocket(STOMP)即时通讯","断线重连比想象复杂","done",datetime(2024,11,5)),
                (P[0].id,"JMeter压测1000并发","QPS决定硬件配置","done",datetime(2024,12,1)),
                (P[0].id,"上线部署+README文档","文档也是工程素养","done",datetime(2024,12,15)),

                # 分布式任务调度系统
                (P[1].id,"Quartz：CRUD+Cron表达式管理","API老派但稳定可靠","done",datetime(2025,1,8)),
                (P[1].id,"Mod分片算法实现","不重复不遗漏是关键","done",datetime(2025,1,20)),
                (P[1].id,"失败重试3次+指数退避+死信队列","容错比功能更重要","done",datetime(2025,2,10)),
                (P[1].id,"RabbitMQ延迟队列+超时检测","消息可靠性是难点","done",datetime(2025,2,25)),
                (P[1].id,"G1调优+连接池优化","Mixed GC对RT影响大","done",datetime(2025,3,5)),
                (P[1].id,"监控面板：成功/失败/耗时趋势","可视化展示也是沟通","done",datetime(2025,3,15)),

                # 微服务API网关
                (P[2].id,"Netty服务端基础搭建","EventLoop模型性能好","done",datetime(2025,4,3)),
                (P[2].id,"路由匹配+权重路由策略","参考SCG的优先级设计","done",datetime(2025,4,10)),
                (P[2].id,"令牌桶限流Redis+Lua脚本","Lua原子性是关键","done",datetime(2025,4,15)),
                (P[2].id,"JWT鉴权过滤器+黑名单","性能和扩展性的平衡","done",datetime(2025,4,22)),
                (P[2].id,"责任链模式重构过滤器","设计模式的实际应用","done",datetime(2025,4,28)),
                (P[2].id,"收尾：README+架构图+压测","文档=工程素养","done",datetime(2025,5,10)),

                # LeetCode打卡
                (P[3].id,"DP专题50题，正确率75%","状态定义是解题关键","done",datetime(2025,2,28)),
                (P[3].id,"图论20题","拓扑排序有实际应用","done",datetime(2025,3,31)),
                (P[3].id,"累计200题达成","每天1题的节奏最持久","done",datetime(2025,4,15)),
                (P[3].id,"滑动窗口专题15题","双指针思路要快","done",datetime(2025,5,20)),

                # 简易RPC框架
                (P[4].id,"Protobuf序列化定义","比JSON小3-10倍，性能提升明显","done",datetime(2025,5,18)),
                (P[4].id,"Netty通信层+编解码器","粘包拆包是基本功","done",datetime(2025,5,22)),
                (P[4].id,"ZK服务注册与发现","RPC的核心基础设施","done",datetime(2025,5,25)),
                (P[4].id,"负载均衡：随机+轮询+加权","从简单到复杂的演进","done",datetime(2025,5,28)),
                (P[4].id,"集成测试+容错处理","超时重试+熔断是生产要求","done",datetime(2025,5,30)),

                # 配置中心
                (P[5].id,"长轮询配置推送实现","与短轮询的取舍","in_progress",datetime(2025,6,8)),
                (P[5].id,"多环境管理(dev/staging/prod)","配置隔离是基本要求","in_progress",datetime(2025,6,15)),
            ]:
                db.add(ProjectLog(project_id=pid, content=c, reflection=r, task_status=ts, log_type="progress", created_at=dt))
            db.flush()
            print(f"[OK] {len(P)} projects + logs")
        else:
            print(f"[SKIP] {existing_p} projects exist")

        # ═══════════════════════════════════════════════════
        # 7. CareerGoal — 职业目标记录
        # ═══════════════════════════════════════════════════
        existing_cg = db.query(CareerGoal).filter(CareerGoal.user_id == user.id).count()
        if existing_cg == 0:
            goals = [
                CareerGoal(user_id=user.id, profile_id=profile.id,
                           target_node_id="senior-java-engineer", target_label="高级Java后端工程师",
                           target_zone="growth", from_node_id="java-mid",
                           gap_skills=["JVM调优","分布式理论","系统设计","MySQL优化"],
                           total_hours=200, safety_gain=25.0, salary_p50=30,
                           tag="", transition_probability=0.7,
                           is_primary=True, is_active=False),
                CareerGoal(user_id=user.id, profile_id=profile.id,
                           target_node_id="architect", target_label="架构师",
                           target_zone="stretch", from_node_id="senior-java-engineer",
                           gap_skills=["架构设计","DDD","高可用","技术决策","团队影响力"],
                           total_hours=500, safety_gain=35.0, salary_p50=50,
                           tag="", transition_probability=0.4,
                           is_primary=True, is_active=True),
            ]
            for g in goals:
                db.add(g)
            db.flush()
            print("[OK] 2 career goals")
        else:
            print(f"[SKIP] {existing_cg} career goals exist")

        db.commit()
        print(f"\n[DONE] Login: zhangmingyuan / test1234")
        print(f"       User ID: {user.id}  Profile ID: {profile.id}")
        print(f"\n成长阶段概览：")
        print(f"  Phase 0 建档(01/15)     readiness: 38% → 42%")
        print(f"  Phase 1 基础复盘(02月)   readiness: 47% → 55%  [可生成报告]")
        print(f"  Phase 2 核心突破(03月)   readiness: 59% → 67%  [可生成报告]")
        print(f"  Phase 3 冲刺期(04-05月)  readiness: 70% → 78%  [可生成报告]")
        print(f"  Phase 4 架构师(05-06月)  readiness: 52% → 64%  [新方向]")

    except Exception as e:
        db.rollback()
        print(f"[ERR] {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
