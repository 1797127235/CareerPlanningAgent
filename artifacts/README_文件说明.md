# artifacts 文件说明

> 这份说明解释 `artifacts/` 根目录下各个文件和子目录是干什么的。  
> 重点是帮你快速判断：**哪个是当前在用的结果，哪个是历史产物，哪个目录里放的是流水线中间文件。**

---

## 一、先看结论

如果你现在主要关心“项目正在使用哪份职业图谱”，优先看这几个：

- `graph.json`
- `pipeline/`
- `pipeline/graph.json`
- `pipeline/README_文件说明.md`

其中：

- `artifacts/graph.json` 是**根目录快捷副本**，方便前端、后端或人工直接查看
- `artifacts/pipeline/graph.json` 是**当前正式流水线输出**
- `artifacts/pipeline/` 里还保留了从 Step 3 到 Step 10 的关键中间结果

---

## 二、根目录文件逐个说明

## 1. `graph.json`

### 作用

这是当前项目最常用的**最终图谱文件副本**。  
内容和 `artifacts/pipeline/graph.json` 同源，包含：

- `metadata`
- `nodes`
- `edges`
- `communities`

### 什么时候会用到

- 前端直接读取图谱时
- 后端 / Agent 需要一份固定路径的图谱时
- 你手工检查最终结果时

### 现在建议

**保留。**  
它相当于“当前正式图谱的入口文件”。

---

## 2. `job_evidence_enhanced_final_verified.jsonl`

### 作用

这是一份**逐条 JD 的结构化证据数据**，每一行是一条岗位记录。  
从内容看，它保存的是：

- 原始岗位标题、描述、公司、地点、薪资、行业
- 清洗后的标题和描述
- 抽取出的 `explicit_skills`、`explicit_tasks`、`signals`
- 学历、经验、薪资结构化字段
- 抽取引擎信息和是否需要人工复查

### 什么时候会用到

- 想逐条检查某条 JD 到底抽出了什么
- 想做证据级别的审计
- 想和 `pipeline/evidence.jsonl` 或 Step 2 的结果做对照时

### 现在建议

**保留，但视为“明细证据文件”而不是当前图谱主入口。**

它更像是“证据仓库”或“历史增强版抽取结果”，不是前后端直接消费的最终图谱。

---

## 3. `pipeline_5k_graph.json`

### 作用

这是一个**5k 快照版本的历史图谱文件**。  
从内容看，它和当前 `graph.json` 不同，例如：

- 社区数量不同
- 边数量更少
- 节点标签还保留过旧版本风格

### 什么时候会用到

- 回看旧实验结果
- 和当前图谱做前后版本对比
- 论文/答辩里展示“优化前 vs 优化后”时

### 现在建议

**可保留。**

如果你后面还要做版本对比，它有价值；  
如果你已经完全确认不再参考旧 5k 版本，也可以删，但删除前建议先确认没有别的文档或脚本引用它。

---

## 三、子目录说明

## 4. `pipeline/`

### 作用

这是**当前正式流水线输出目录**。  
里面保存了从中间结果到最终图谱的核心文件，例如：

- `directions.json`
- `profiles.json`
- `role_family.json`
- `candidate_pairs.json`
- `llm_edges.json`
- `validated_edges.json`
- `communities.json`
- `graph.json`

### 什么时候会用到

- 你要排查图谱质量问题时
- 你要只重跑 Step 9 / Step 10 这类局部步骤时
- 你要追踪“某个节点/社区/边是怎么来的”时

### 现在建议

**必须保留。**

另外，这个目录里已经有一份更详细的逐文件说明：

- `pipeline/README_文件说明.md`

如果你想看每个中间产物的上下游依赖，直接打开那份即可。

---

## 5. `pipeline_5k/`

### 作用

这是一个**5k 样本快照目录**。  
它不是当前正式全量流水线目录，而是某次导出的子集实验产物。

里面的文件包括：

- `jobs.jsonl`
- `evidence.jsonl`
- `directions.json`
- `profiles.json`
- `role_family.json`
- `candidate_pairs.json`
- `llm_edges.json`
- `validated_edges.json`
- `communities.json`
- `graph.json`
- `snapshot_meta.json`

其中 `snapshot_meta.json` 记录了这次快照的来源，例如：

- 从哪个目录导出
- 导出了多少条 JD
- 使用了哪个缓存文件

### 什么时候会用到

- 做“小样本试验”
- 跑验证用的小图谱
- 对比 `pipeline/` 与 `pipeline_5k/` 的结果差异

### 现在建议

**建议保留。**

因为它适合做低成本实验，比直接动全量目录更安全。

---

## 四、怎么理解这几份图谱的关系

可以把它们理解成：

| 路径 | 身份 | 用途 |
|------|------|------|
| `artifacts/graph.json` | 当前正式图谱的副本 | 方便项目直接读取 |
| `artifacts/pipeline/graph.json` | 当前正式流水线最终产物 | 最权威来源 |
| `artifacts/pipeline_5k/graph.json` | 5k 快照目录内最终图谱 | 小样本实验结果 |
| `artifacts/pipeline_5k_graph.json` | 旧版/额外导出的 5k 图谱副本 | 版本对比或历史保留 |

如果你只认一份“当前正式结果”，那就是：

- `artifacts/pipeline/graph.json`

而 `artifacts/graph.json` 可以看成它的同步副本。

---

## 五、建议的保留策略

### 必留

- `graph.json`
- `pipeline/`
- `pipeline_5k/`

### 建议留

- `job_evidence_enhanced_final_verified.jsonl`
- `pipeline_5k_graph.json`

### 可以等你确认后再考虑删

- 明显重复、且你确定不再使用的旧版本图谱副本

但目前从你这个项目状态看，**先别急着删根目录这些文件**，因为它们还承担着：

- 当前图谱入口
- 历史实验结果保留
- 证据级审计数据留档

---

## 六、一句话总结

`artifacts/` 根目录更像是“结果总览区”，`pipeline/` 是“当前正式产物区”，`pipeline_5k/` 是“5k 实验快照区”。
