# 知识库资料索引

## 01-核心知识资产
项目运行时直接读取的核心数据资产。

| 文件 | 说明 |
|------|------|
| graph/graph.json | 职业图谱主数据（节点+边） |
| skills/*.csv/json | 技能分类体系、评分表、频率统计、等级映射 |
| embeddings/*.json | 节点/技能向量嵌入（node2vec） |
| learning/*.json/csv | 学习路径、学习主题、学习资源库 |
| market/*.json | 市场信号、行业信号、时间线 |
| roadmap/*.json | 开发者路线图技能树映射 |
| roles/*.json | 各角色简介 |
| assessment/*.json | 情景判断题(SJT)模板 |
| transitions/*.json | 转岗概率模型系数 |
| mappings/*.json/csv | ESCO、O*NET 映射关系 |

## 02-原始第三方数据来源
| 目录 | 来源 | 说明 |
|------|------|------|
| esco/ | EU ESCO v1.2.1 | 欧洲职业/技能/资格标准 |
| onet/ | US O*NET db_30_2_text | 美国职业信息网全量文本 |
| domestic/ | 国内爬取/采购 | 中文岗位数据、节点数据、边数据 |
| aei/ | Anthropic Economic Index | AI 经济影响指数，含 4 个 release + labor market impacts |

## 03-数据处理与ETL
| 文件 | 说明 |
|------|------|
| etl/01_classify.py | 岗位分类（ESCO/O*NET 映射） |
| etl/02_aggregate.py | 聚合统计 |
| etl/03_signals.py | 市场信号生成 |
| etl/04_skill_frequency.py | 技能频率统计 |
| knowledge-base/build_kb.py | 知识库构建 |
| knowledge-base/vector_store.py | 向量存储管理 |
| scripts/*.py | 各类导入、增强、翻译、修复脚本 |

## 04-ETL中间产物
| 文件 | 说明 |
|------|------|
| classified.parquet | 岗位分类结果（157MB） |
| classified_listed.parquet | 上市公司岗位分类（99MB） |
| contextual_narrative_*.json | 上下文叙事生成草稿 |
| edge_review/ | 图谱边质量审核 batch 记录（prompt + result） |

## 05-Pipeline产物
| 文件 | 说明 |
|------|------|
| graph.json | pipeline 产出的图谱 |
| profiles.json | 候选人画像 |
| jobs.jsonl | 处理后的岗位 |
| evidence.jsonl | 边证据 |
| validated_edges.json | 审核通过的边 |
| communities.json | 社区发现结果 |
| directions.json | 转岗方向 |
| candidate_pairs.json | 候选人对 |
| role_family.json | 角色族 |

## 06-其他辅助数据
| 文件 | 说明 |
|------|------|
| jobs_data_clean.jsonl | 清洗后全量岗位数据 |
| graph_nodes.txt | 图谱节点清单 |
