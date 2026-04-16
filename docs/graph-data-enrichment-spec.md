# 岗位图谱数据补充方案

## 背景与目标

审计 `data/graph.json`（45 个岗位节点、101 条边）对照项目需求，发现三处数据缺口：

| 需求 | 当前状态 | 缺口 |
|---|---|---|
| ≥10 岗位画像 | 45 个 | ✅ 满足 |
| 6 项软能力（证书/创新/学习/抗压/沟通/实习） | 仅有 communication/learning/resilience/innovation/collaboration；16/45 节点连 `soft_skills` 都没有 | ❌ 缺「证书」「实习」两项；16 个节点需补全 soft_skills |
| 每个岗位都有晋升路径 | `promotion_path` 数组已存在（5 级），但对应的 `vertical` 边只覆盖 16/45 节点 | ⚠ 元数据齐全，图边不全 |
| ≥5 岗位各 ≥2 条换岗路径 | 只有 cpp、systems-cpp 两个节点满足 | ❌ 严重不达标 |

本方案分 **A / B / C 三个独立子任务**，可分配给不同组员并行推进。

---

## 子任务 A：补齐软能力字段

### 目标

1. 在 node schema 里新增 `certificates`（证书要求）和 `internship_friendly`（实习适配度）两个字段
2. 给所有 45 个节点补齐这两个字段
3. 给 16 个目前没有 `soft_skills` 的节点补齐完整的 5 维评分

### 数据 schema 变更

在每个 node 里新增：

```jsonc
{
  // ... 原有字段保留不变
  "certificates": ["AWS Certified Solutions Architect", "软考高级（系统架构师）"],
  "internship_friendly": 75,   // 0-100，实习生是否容易上手这个岗
  "soft_skills": {
    "communication": 70,
    "learning": 85,
    "resilience": 75,
    "innovation": 80,
    "collaboration": 80,
    "stress_resilience": 75   // ← 新增，等同 resilience；或就此保留 resilience
  }
}
```

⚠ **关于 `stress_resilience`**：代码里现有字段名是 `resilience`（"抗压能力"），语义已对应需求里的"抗压"。不要重命名，避免破坏现有代码读取。spec 文档里直接把 `resilience` 标记为"抗压能力"即可。

### 16 个缺 `soft_skills` 的节点清单

执行前用这条命令列出精确清单：

```bash
python -c "
import json
d = json.load(open('data/graph.json', encoding='utf-8'))
for n in d['nodes']:
    if not n.get('soft_skills'):
        print(n['node_id'], '|', n.get('label',''), '|', n.get('role_family',''))
"
```

预期包含：`server-side-game-developer`、`ai-data-scientist`、`ai-agents`、`bi-analyst`、`ai-red-teaming`、`blockchain`、`product-manager`、`technical-writer`、`devrel`、`ux-design` 等。

### 执行步骤

1. **写脚本 `scripts/enrich_graph_soft_skills.py`**（可以参考已有 `scripts/gen_soft_skills.py` 的风格）：
   - 读取 `data/graph.json`
   - 对每个节点，根据 `role_family` + `career_level` 用 LLM（qwen-plus 即可）产出候选 `soft_skills` / `certificates` / `internship_friendly`
   - 输出到 **新文件** `data/graph_soft_skills_draft.json`（先不覆盖原文件）
   - LLM prompt 参考：
     ```
     你是一名资深 HR，请根据岗位"{label}"（职级 L{career_level}，家族 {role_family}），
     给出：
     1. 最常见的 2-3 个证书要求（中国语境，可以是软考/AWS/CNCF/行业认证）
     2. 实习生是否容易上手（0-100 整数）
     3. 5 项软能力评分（沟通/学习/抗压/创新/协作，各 0-100）
     输出纯 JSON，不要 markdown。
     ```
2. **人工审核** `data/graph_soft_skills_draft.json`：LLM 产出的证书名、评分要被人看一眼，避免出现不存在的证书或评分不合理的情况（例如算法岗"抗压"打 30 显然不对）
3. **合并到 `data/graph.json`**：写合并脚本或手动把 draft 里的三个字段 merge 进原节点，不覆盖其它字段
4. **同步 DB**：`python -m scripts.sync_graph_to_db`
   - ⚠ 注意：`JobNode` / `JobScore` 表里目前可能没有 `certificates` / `internship_friendly` 列。如果后端要透出这两个字段到 API，需要同步加列（见"后端暴露字段"一节）。如果只在前端读 graph.json，可以暂时不动 DB schema。

### 后端暴露字段（可选）

如果需要在 API 里返回这两个字段：

- `backend/db_models.py`：`JobNode` 增加 `certificates: Mapped[list]`、`internship_friendly: Mapped[int]`
- `backend/routers/graph.py` 第 109 行附近：在 node 序列化 dict 里加 `"certificates": node.get("certificates", [])`、`"internship_friendly": node.get("internship_friendly", 50)`
- `scripts/sync_graph_to_db.py` 的 `sync_nodes` 函数：存 `certificates`、`internship_friendly`

如果前端直接读 graph.json（当前 Coverflow 就是），后端改动可以跳过。

### 验收

```bash
python -c "
import json
d = json.load(open('data/graph.json', encoding='utf-8'))
no_soft = [n['node_id'] for n in d['nodes'] if not n.get('soft_skills')]
no_cert = [n['node_id'] for n in d['nodes'] if not n.get('certificates')]
no_intern = [n['node_id'] for n in d['nodes'] if n.get('internship_friendly') is None]
print(f'缺 soft_skills: {len(no_soft)} 个')
print(f'缺 certificates: {len(no_cert)} 个')
print(f'缺 internship_friendly: {len(no_intern)} 个')
"
# 期望三行都输出 0 个
```

---

## 子任务 B：展示垂直晋升路径

### 目标

让每个岗位的晋升路径对用户可见，满足"涵盖岗位描述、岗位晋升路径关联信息"要求。

### 推荐方案（B1，零数据改动）

所有 45 个节点 `promotion_path` 已存在（5 级文本数组），**直接在前端岗位详情页 `frontend/src/pages/RoleDetailPage.tsx` 渲染成阶梯图**。无需改 graph.json、无需改后端、无需加边。

### 执行步骤

1. **在 `RoleDetailPage.tsx` 数据解析处**确认 `promotion_path` 已经传到组件（如果 `/graph/node/:id` 的 API 没返回，去 `backend/routers/graph.py` 加上 `"promotion_path": node.get("promotion_path", [])`）
2. **新增一个阶梯组件**：`frontend/src/components/role/PromotionLadder.tsx`，输入 `string[]`（比如 `["初级前端工程师","前端工程师","高级前端工程师","前端技术专家","前端架构师"]`），输出一个纵向阶梯 UI。当前 `career_level` 对应的阶梯高亮
3. **在 `RoleDetailPage.tsx` 的某个合适 section 插入 `<PromotionLadder path={data.promotion_path} currentLevel={data.career_level} />`**
4. **视觉风格**：保持和现有 role detail 页一致的冷色玻璃风（参考 Coverflow），不要引入暖色/纸质等异质材质

### 不做 B2

B2（从 `promotion_path` 自动生成同家族垂直边）**不做**。理由：
- `promotion_path` 是同一岗位的职级进阶（初级/中级/高级），本质是 career_level 维度
- 如果硬塞进 graph.json 的 edges，会造出大量机械边（5 级 × 45 节点 ≈ 180 条边），稀释有意义的 `lateral` 换岗信号
- 前端直接渲染数组即可，不需要把它编码成图结构

### 验收

- 进 `/role/:id` 任意岗位页，能看到 5 级阶梯且当前职级高亮
- 所有 45 个节点都能显示，无空数组

---

## 子任务 C：补换岗路径（最关键）

### 目标

让 **≥5 个岗位节点各自拥有 ≥2 条跨家族换岗路径**（即 `edge_type: "lateral"` 且源和目标的 `role_family` 不同）。

### 候选边清单（直接入库）

以下是审核过的候选换岗边，共 7 个起点 × 2 条 = **14 条新 lateral 边**，远超要求 5 个起点的下限。每条边写明共享技能和换岗难度。

| # | 起点 node_id（家族） | 终点 node_id（家族） | 共享技能 | 难度 |
|---|---|---|---|---|
| 1 | `data-analyst`（数据） | `machine-learning`（AI/ML） | Python、SQL、统计学、数据清洗 | 中 |
| 2 | `data-analyst`（数据） | `product-manager`（产品） | 数据敏感度、业务沟通、需求分析 | 中 |
| 3 | `python`（后端） | `machine-learning`（AI/ML） | Python、Linux、算法基础 | 中 |
| 4 | `python`（后端） | `data-engineer`（数据） | Python、SQL、ETL、Airflow | 易 |
| 5 | `java`（后端） | `devops`（运维/DevOps） | Linux、K8s、CI/CD、JVM 调优 | 中 |
| 6 | `java`（后端） | `data-engineer`（数据） | SQL、Spark、Kafka、分布式 | 中 |
| 7 | `qa`（测试开发） | `devops`（运维/DevOps） | CI/CD、Shell、自动化框架 | 中 |
| 8 | `qa`（测试开发） | `python`（后端） | Python、自动化测试、接口测试 | 易 |
| 9 | `devops`（运维/DevOps） | `cyber-security`（安全） | Linux、网络、日志审计 | 中 |
| 10 | `devops`（运维/DevOps） | `infrastructure-engineer`（系统架构） | K8s、分布式、Linux 内核 | 中 |
| 11 | `frontend`（前端开发） | `full-stack`（全栈开发） | JS、React、Node.js、HTTP | 易 |
| 12 | `frontend`（前端开发） | `ux-design`（设计） | 审美、交互、原型工具 | 难 |
| 13 | `machine-learning`（AI/ML） | `data-engineer`（数据） | Python、Spark、特征工程、数据管道 | 中 |
| 14 | `machine-learning`（AI/ML） | `product-manager`（产品） | 建模思维、业务沟通、AB 测试 | 难 |

7 个起点节点分别是：`data-analyst`、`python`、`java`、`qa`、`devops`、`frontend`、`machine-learning`，每个都有 2 条外向换岗边，满足"≥5 岗位各 ≥2 条"要求。

### 边的 JSON 格式

在 `data/graph.json` 的 `edges` 数组里追加，每条边格式：

```jsonc
{
  "source": "data-analyst",
  "target": "machine-learning",
  "edge_type": "lateral",
  "difficulty": "中",
  "shared_skills": ["Python", "SQL", "统计学", "数据清洗"],
  "transition_note": "数据分析师向机器学习转型是常见路径，需补齐算法原理和建模经验"
}
```

⚠ **字段说明**：
- `edge_type` 必须是 `"lateral"`（和现有分类对齐）
- `difficulty` 枚举：`"易" | "中" | "难"`
- `shared_skills` 是 string 数组，前端可以直接展示"共享 N 个技能"
- `transition_note` 是一句话说明，非必需字段但强烈建议填

### 执行步骤

1. **验证 node_id 存在**：上表 14 条边的 source/target 必须在当前 graph.json 的 nodes 数组里存在。跑：
   ```bash
   python -c "
   import json
   d = json.load(open('data/graph.json', encoding='utf-8'))
   ids = {n['node_id'] for n in d['nodes']}
   pairs = [('data-analyst','machine-learning'),('data-analyst','product-manager'),
            ('python','machine-learning'),('python','data-engineer'),
            ('java','devops'),('java','data-engineer'),
            ('qa','devops'),('qa','python'),
            ('devops','cyber-security'),('devops','infrastructure-engineer'),
            ('frontend','full-stack'),('frontend','ux-design'),
            ('machine-learning','data-engineer'),('machine-learning','product-manager')]
   for s,t in pairs:
       print('OK' if (s in ids and t in ids) else 'MISSING', s, '->', t)
   "
   ```
   期望全部 `OK`
2. **写入 graph.json**：手动编辑或写个脚本往 `edges` 数组 append 上面 14 条，不要覆盖已有边。
3. **去重检查**：避免和已有 lateral 边重复：
   ```bash
   python -c "
   import json
   d = json.load(open('data/graph.json', encoding='utf-8'))
   seen = set()
   dups = []
   for e in d['edges']:
       key = (e['source'], e['target'], e.get('edge_type'))
       if key in seen: dups.append(key)
       seen.add(key)
   print('重复边:', dups or '无')
   "
   ```
4. **同步 DB**：`python -m scripts.sync_graph_to_db`
5. **前端展示**：岗位详情页增加一个"可换方向"区域，列出本岗位所有 `edge_type: "lateral"` 出边，显示目标岗位 label、共享技能 chip、难度 badge、transition_note。组件放在 `frontend/src/components/role/LateralSwitchList.tsx`。

### 验收

跑这条命令确认 ≥5 个节点各有 ≥2 条跨家族换岗边：

```bash
python -c "
import json
from collections import defaultdict
d = json.load(open('data/graph.json', encoding='utf-8'))
fam = {n['node_id']: n.get('role_family','') for n in d['nodes']}
out_cross = defaultdict(int)
for e in d['edges']:
    if e.get('edge_type') != 'lateral': continue
    s, t = e['source'], e['target']
    if fam.get(s) and fam.get(t) and fam[s] != fam[t]:
        out_cross[s] += 1
qualified = [nid for nid, c in out_cross.items() if c >= 2]
print(f'满足 ≥2 跨家族换岗边的节点数: {len(qualified)}')
print('节点:', qualified)
"
# 期望输出至少 7 个节点，包含上表 7 个起点
```

---

## 分工建议

| 子任务 | 预计工作量 | 技能要求 | 可并行 |
|---|---|---|---|
| A（软能力字段） | 1-2 天（含 LLM 跑批 + 人工审） | Python、prompt 调试 | ✅ |
| B1（晋升路径 UI） | 0.5-1 天 | React/TS + 基础样式 | ✅ |
| C（换岗路径） | 1 天（数据） + 1 天（UI） | 产品判断 + React/TS | 数据先做，UI 等 C 数据 |

A 和 B1 完全独立可并行。C 的数据部分独立，C 的前端部分要等 C 的数据入库。

## 非目标（不要做）

- ❌ 不要改 `data/graph.json` 里已有的 nodes / edges 字段（只做追加/补充）
- ❌ 不要动 `replacement_pressure` / `human_ai_leverage` / `zone` 这些已有指标
- ❌ 不要给 B 任务造垂直边（B2 方案不做）
- ❌ 不要把换岗边的 `difficulty` 枚举扩展成 4 级以上，保持三档 `易/中/难`
- ❌ 不要动 `developer-roadmap/` 目录
- ❌ 证书列表不要写虚构的（如"某不存在的认证"），只写真实存在的（AWS/CNCF/软考/Oracle 等）

## 完成后的交付物

- `data/graph.json`：新增 `certificates`、`internship_friendly`、补全 `soft_skills`；edges 数组追加 14 条 lateral 边
- `scripts/enrich_graph_soft_skills.py`：软能力批量生成脚本
- `frontend/src/components/role/PromotionLadder.tsx`：晋升阶梯组件
- `frontend/src/components/role/LateralSwitchList.tsx`：换岗路径组件
- `RoleDetailPage.tsx`：集成以上两个组件

完成后 `git status` 预期：
```
M data/graph.json
M frontend/src/pages/RoleDetailPage.tsx
?? scripts/enrich_graph_soft_skills.py
?? frontend/src/components/role/PromotionLadder.tsx
?? frontend/src/components/role/LateralSwitchList.tsx
```

DB 通过 `python -m scripts.sync_graph_to_db` 刷新，不在 git 里。
