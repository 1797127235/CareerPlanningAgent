#!/usr/bin/env python3
"""打包知识库资料用于比赛交付。排除 .firecrawl/ 和 _bmad-output/。"""

import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path('.')
OUT = ROOT / 'knowledge-base-submission'
ZIP_NAME = 'knowledge-base-submission.zip'

def rm_and_mkdir(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)

def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f'  {src} -> {dst}')

def copy_tree(src: Path, dst: Path, skip=None):
    if not src.exists():
        print(f'  SKIP (missing): {src}')
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob('*'):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        if skip and skip(str(rel)):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
    print(f'  {src}/ -> {dst}/')

# ───────────────────────────────────────────────
print('=== Step 1: 清理输出目录 ===')
rm_and_mkdir(OUT)

# ───────────────────────────────────────────────
print('\n=== Step 2: 01-核心知识资产 ===')
core_dir = OUT / '01-核心知识资产'
core_files = {
    'graph/graph.json': ROOT / 'data/graph.json',
    'skills/skill_taxonomy.csv': ROOT / 'data/skill_taxonomy.csv',
    'skills/skills_to_score.csv': ROOT / 'data/skills_to_score.csv',
    'skills/skill_frequencies.json': ROOT / 'data/skill_frequencies.json',
    'skills/skill_fill_path_tags.json': ROOT / 'data/skill_fill_path_tags.json',
    'skills/level_skills.json': ROOT / 'data/level_skills.json',
    'embeddings/node_embeddings.json': ROOT / 'data/node_embeddings.json',
    'embeddings/skill_embeddings.json': ROOT / 'data/skill_embeddings.json',
    'learning/learning_paths.json': ROOT / 'data/learning_paths.json',
    'learning/learning_topics.json': ROOT / 'data/learning_topics.json',
    'learning/learning_resources.csv': ROOT / 'data/learning_resources.csv',
    'market/market_signals.json': ROOT / 'data/market_signals.json',
    'market/market_timeline.json': ROOT / 'data/market_timeline.json',
    'market/industry_signals.json': ROOT / 'data/industry_signals.json',
    'roadmap/roadmap_skills.json': ROOT / 'data/roadmap_skills.json',
    'roles/role_intros.json': ROOT / 'data/role_intros.json',
    'assessment/sjt_templates.json': ROOT / 'data/sjt_templates.json',
    'transitions/transition_model_coefficients.json': ROOT / 'data/transition_model_coefficients.json',
    'mappings/esco_node_mapping.json': ROOT / 'data/esco_node_mapping.json',
    'mappings/onet_mapping.json': ROOT / 'data/onet_mapping.json',
    'mappings/onet_cn_index.json': ROOT / 'data/onet_cn_index.json',
    'mappings/onet_node_skills.csv': ROOT / 'data/onet_node_skills.csv',
    'mappings/onet_skill_framework.csv': ROOT / 'data/onet_skill_framework.csv',
}
for dst_rel, src in core_files.items():
    copy_file(src, core_dir / dst_rel)

# ───────────────────────────────────────────────
print('\n=== Step 3: 02-原始第三方数据来源 ===')
raw_dir = OUT / '02-原始第三方数据来源'

copy_tree(ROOT / 'data/ESCO dataset - v1.2.1 - classification - en - csv', raw_dir / 'esco')
copy_tree(ROOT / 'data/db_30_2_text', raw_dir / 'onet')

domestic_dir = raw_dir / 'domestic'
domestic_dir.mkdir(parents=True, exist_ok=True)
for f in ['岗位数据.csv', '节点数据.csv', '节点边.csv']:
    src = ROOT / 'data' / f
    if src.exists():
        copy_file(src, domestic_dir / f)

copy_tree(ROOT / 'data/EconomicIndex', raw_dir / 'aei', skip=lambda p: '/.git/' in p)

# ───────────────────────────────────────────────
print('\n=== Step 4: 03-数据处理与ETL ===')
etl_dir = OUT / '03-数据处理与ETL'
etl_scripts = {
    'etl/01_classify.py': ROOT / 'etl/01_classify.py',
    'etl/02_aggregate.py': ROOT / 'etl/02_aggregate.py',
    'etl/03_signals.py': ROOT / 'etl/03_signals.py',
    'etl/04_skill_frequency.py': ROOT / 'etl/04_skill_frequency.py',
    'etl/config/role_family_rules.yaml': ROOT / 'etl/config/role_family_rules.yaml',
    'knowledge-base/build_kb.py': ROOT / 'knowledge_base/build_kb.py',
    'knowledge-base/vector_store.py': ROOT / 'knowledge_base/vector_store.py',
    'scripts/import_onet_data.py': ROOT / 'scripts/import_onet_data.py',
    'scripts/build_roadmap_graph.py': ROOT / 'scripts/build_roadmap_graph.py',
    'scripts/enrich_graph_strategic.py': ROOT / 'scripts/enrich_graph_strategic.py',
    'scripts/enrich_level_skills.py': ROOT / 'scripts/enrich_level_skills.py',
    'scripts/gen_contextual_narrative.py': ROOT / 'scripts/gen_contextual_narrative.py',
    'scripts/gen_missing_learning_paths.py': ROOT / 'scripts/gen_missing_learning_paths.py',
    'scripts/gen_promotion_paths.py': ROOT / 'scripts/gen_promotion_paths.py',
    'scripts/import_roadmap_content.py': ROOT / 'scripts/import_roadmap_content.py',
    'scripts/import_roadmap_resources.py': ROOT / 'scripts/import_roadmap_resources.py',
    'scripts/translate_skills.py': ROOT / 'scripts/translate_skills.py',
    'scripts/seed_ai_tool_mappings.py': ROOT / 'scripts/seed_ai_tool_mappings.py',
    'scripts/regen_edges.py': ROOT / 'scripts/regen_edges.py',
    'scripts/fix_graph_quality.py': ROOT / 'scripts/fix_graph_quality.py',
}
for dst_rel, src in etl_scripts.items():
    if src.exists():
        copy_file(src, etl_dir / dst_rel)

# ───────────────────────────────────────────────
print('\n=== Step 5: 04-ETL中间产物（全交）===')
mid_dir = OUT / '04-ETL中间产物'
mid_files = {
    'classified.parquet': ROOT / 'data/classified.parquet',
    'classified_listed.parquet': ROOT / 'data/classified_listed.parquet',
    'contextual_narrative_draft.json': ROOT / 'data/contextual_narrative_draft.json',
    'contextual_narrative_batch2.json': ROOT / 'data/contextual_narrative_batch2.json',
}
for dst_rel, src in mid_files.items():
    if src.exists():
        copy_file(src, mid_dir / dst_rel)

copy_tree(ROOT / 'data/edge_review', mid_dir / 'edge_review')

# ───────────────────────────────────────────────
print('\n=== Step 6: 05-Pipeline产物 ===')
pipeline_dir = OUT / '05-Pipeline产物'
copy_tree(ROOT / 'artifacts/pipeline', pipeline_dir)

# ───────────────────────────────────────────────
print('\n=== Step 7: 06-其他辅助数据 ===')
aux_dir = OUT / '06-其他辅助数据'
aux_files = {
    'jobs_data_clean.jsonl': ROOT / 'data/jobs_data_clean.jsonl',
    'graph_nodes.txt': ROOT / 'graph_nodes.txt',
    'data/README.md': ROOT / 'data/README.md',
}
for dst_rel, src in aux_files.items():
    if src.exists():
        copy_file(src, aux_dir / dst_rel)

# ───────────────────────────────────────────────
print('\n=== Step 8: 生成 INDEX.md ===')
index_md = """# 知识库资料索引

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
"""
(OUT / 'INDEX.md').write_text(index_md, encoding='utf-8')
print('  已生成 INDEX.md')

# ───────────────────────────────────────────────
print('\n=== Step 9: 统计 ===')
total_size = 0
file_count = 0
for p in OUT.rglob('*'):
    if p.is_file():
        total_size += p.stat().st_size
        file_count += 1
print(f'总文件数: {file_count}')
print(f'总大小: {total_size // 1024 // 1024} MB ({total_size // 1024} KB)')

# ───────────────────────────────────────────────
print('\n=== Step 10: 打包 zip ===')
if (ROOT / ZIP_NAME).exists():
    os.remove(ROOT / ZIP_NAME)

with zipfile.ZipFile(ROOT / ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in OUT.rglob('*'):
        if p.is_file():
            zf.write(p, p.relative_to(ROOT))

zip_size = (ROOT / ZIP_NAME).stat().st_size
print(f'打包完成: {ZIP_NAME}')
print(f'压缩后大小: {zip_size // 1024 // 1024} MB ({zip_size // 1024} KB)')
print('\n✅ 知识库资料整理完毕！')
