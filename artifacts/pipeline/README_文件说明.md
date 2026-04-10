# artifacts/pipeline 文件说明

> 这份说明专门解释 `artifacts/pipeline/` 目录里各个中间产物和最终产物的作用。  
> 重点不是流水线原理，而是：**这个文件是干什么的、什么时候会被用到、现在能不能删。**

---

## 一、先看结论

如果你当前已经完成了 **Step 2**，并且 `evidence.jsonl` 行数已经和 `jobs.jsonl` 对齐，那么：

### 现在优先保留

- `jobs.jsonl`
- `evidence.jsonl`
- `directions.json`
- `assignments.jsonl`
- `profiles.json`
- `role_family.json`
- `candidate_pairs.json`
- `graph.json`

### 现在可以删的候选

- `step2_llm_checkpoint.jsonl`
- `step2_llm_checkpoint.jsonl.bak`

### 可留可删

- `step2_llm_content_cache.json`
- `llm_edges_cache.json`

是否删除取决于你后面还要不要重跑 Step 2 / Step 7。

---

## 二、文件逐个解释

## 1. `jobs.jsonl`

### 作用

这是 Step 1 的输出，表示原始岗位数据转成的标准化 JD 列表。  
后续所有步骤都从它间接出发。

### 什么时候会用到

- 重跑 Step 2 时会用到
- 想重新做全量抽取时必须保留

### 现在建议

**保留。**

---

## 2. `evidence.jsonl`

### 作用

这是 Step 2 的最终产物。  
每条 JD 都会被抽成结构化证据，包括：

- 技能
- 任务
- 经验
- 学历
- 薪资
- 岗位性质标签

### 什么时候会用到

- Step 3~10 都依赖它
- 后续图谱质量问题排查也会回看它

### 现在建议

**必须保留。**

---

## 3. `step2_llm_checkpoint.jsonl`

### 作用

这是 Step 2 的**断点续跑缓存**。  
每当一批 JD 的 LLM 抽取完成，就会把：

- 外层 `job_id`
- 内层 `result`

追加写到这个文件里。

### 什么时候会用到

- 只有 **Step 2 尚未跑完**，或者你准备继续 `--resume` 跑 Step 2 时才有用

### 现在建议

如果：

- `evidence.jsonl` 已完整产出
- 且行数和 `jobs.jsonl` 一致

那么这个文件已经**完成历史使命**。

**建议：可以删除。**

---

## 4. `step2_llm_checkpoint.jsonl.bak`

### 作用

这是你之前修复 checkpoint 损坏记录时留下的备份文件。

### 什么时候会用到

- 只有在怀疑当前 `step2_llm_checkpoint.jsonl` 被误修坏，想回滚时才有用

### 现在建议

当前 Step 2 已经跑完并产出完整 `evidence.jsonl`，这个备份基本已经没价值。

**建议：可以删除。**

---

## 5. `step2_llm_content_cache.json`

### 作用

这是 Step 2 的**内容缓存**。  
不是按 `job_id` 缓存，而是按 JD 内容 hash 缓存。

它的意义是：

- 即使 `job_id` 不同
- 但如果 JD 正文相同或相似
- 也可以复用以前的 LLM 抽取结果

### 什么时候会用到

- 以后重新跑 Step 2
- 重建 evidence
- 跑新的 snapshot

### 现在建议

如果你后面**还可能重跑 Step 2**，建议保留。  
如果你确定短期内不会再重跑 Step 2，只想省空间，也可以删。

**建议：可留可删，偏向保留。**

---

## 6. `directions.json`

### 作用

这是 Step 3 的产物，表示岗位方向定义。  
核心内容包括：

- direction_id
- O*NET 映射
- 合并后的岗位方向
- 匹配方式

### 什么时候会用到

- Step 4 聚合画像时会用
- 排查“节点 label 为什么变成 O*NET 编码”时也会回看

### 现在建议

**保留。**

---

## 7. `assignments.jsonl`

### 作用

这是 Step 3 的另一份核心产物。  
它记录的是：

- 每条 JD
- 最终被分配到哪个 `direction_id`

### 什么时候会用到

- Step 4 聚合画像必须依赖它
- 排查“某个 JD 被归到哪个方向”时会用到

### 现在建议

**保留。**

---

## 8. `profiles.json`

### 作用

这是 Step 4 的核心画像文件。  
每个方向会被聚合成一个 profile，里面有：

- top_skills
- top_tasks
- experience
- education
- salary
- job_nature_tags
- 城市 / 行业分布

### 什么时候会用到

- Step 5~10 都会用
- 也是排查 `graph.json` 节点画像质量时最重要的上游文件

### 现在建议

**必须保留。**

---

## 9. `role_family.json`

### 作用

这是 Step 5 的产物。  
给每个岗位方向打一个岗位族标签，比如：

- software_development
- algorithm_ai
- quality_assurance
- delivery_and_support

### 什么时候会用到

- Step 6 预筛候选对
- Step 9 命名社区
- Step 10 输出节点 family

### 现在建议

**保留。**

---

## 10. `candidate_pairs.json`

### 作用

这是 Step 6 的产物。  
它是送给 Step 7 做 LLM 判边的候选岗位对。

### 什么时候会用到

- 重跑 Step 7 时会用
- 排查“为什么这两个岗位之间会有边/没边”时会用

### 现在建议

**保留。**

---

## 11. `llm_edges_cache.json`

### 作用

这是 Step 7 判边时的缓存文件。  
它的目的和 Step 2 的内容缓存类似：

- 防止同样的候选对反复调 LLM

### 什么时候会用到

- 重跑 Step 7
- 调整 step8/step9/step10 前，想复用之前的判边结果

### 现在建议

如果你后面还会继续重跑 Step 7，**建议保留**。  
如果你确定后面不会再重跑判边，想省空间，可以删。

**建议：可留可删，偏向保留。**

---

## 12. `graph.json`

### 作用

这是当前目录下最重要的最终产物。  
它是 Step 10 的输出，包含：

- 节点
- 边
- 社区

### 什么时候会用到

- 前端职业图谱展示
- 后端 / Agent 读取
- 质量审核与人工检查

### 现在建议

**必须保留。**

---

## 三、当前目录里哪些是“真没用了”

在你现在这个状态下，最明确可以删的是：

| 文件 | 原因 |
|------|------|
| `step2_llm_checkpoint.jsonl` | Step 2 已完成，`evidence.jsonl` 已完整生成，断点续跑缓存已无必要 |
| `step2_llm_checkpoint.jsonl.bak` | 只是修损坏记录时留下的备份，当前已无实际用途 |

---

## 四、当前目录里哪些“不是必须，但删了以后会后悔”

这两个文件不是最终产物，但经常能省很多时间：

| 文件 | 建议 |
|------|------|
| `step2_llm_content_cache.json` | 建议保留。以后重跑 Step 2 会明显加速 |
| `llm_edges_cache.json` | 建议保留。以后重跑 Step 7 会明显加速 |

如果你现在空间不紧张，优先保留。

---

## 五、建议的保留策略

### 最稳妥方案

保留所有文件，只删除：

- `step2_llm_checkpoint.jsonl`
- `step2_llm_checkpoint.jsonl.bak`

### 偏省空间方案

保留：

- `jobs.jsonl`
- `evidence.jsonl`
- `directions.json`
- `assignments.jsonl`
- `profiles.json`
- `role_family.json`
- `candidate_pairs.json`
- `graph.json`

删除：

- `step2_llm_checkpoint.jsonl`
- `step2_llm_checkpoint.jsonl.bak`
- `step2_llm_content_cache.json`
- `llm_edges_cache.json`

但这样后面如果重跑 Step 2 或 Step 7，就会慢很多。

---

## 六、如果你现在只想删最没用的

直接删这两个最安全：

```powershell
del artifacts\\pipeline\\step2_llm_checkpoint.jsonl
del artifacts\\pipeline\\step2_llm_checkpoint.jsonl.bak
```

---

## 七、备注

如果后面你重新跑：

- `Step 3~10`  
  这些中间文件会被覆盖更新

如果你重新跑：

- `Step 2`  
  那么 `step2_llm_content_cache.json` 仍然很有价值

所以“要不要删”本质上取决于：

- 你后面还会不会频繁重跑某一步

