import zipfile, os

files = [
    'data/graph.json', 'data/level_skills.json', 'data/market_signals.json',
    'data/industry_signals.json', 'data/learning_paths.json', 'data/role_intros.json',
    'data/sjt_templates.json', 'data/roadmap_skills.json', 'data/node_embeddings.json',
    'data/skill_embeddings.json', 'data/skill_frequencies.json',
    'data/transition_model_coefficients.json', 'data/skill_fill_path_tags.json',
    'data/onet_cn_index.json', 'data/onet_mapping.json', 'data/skill_taxonomy.csv',
    'data/skills_to_score.csv', 'data/esco_node_mapping.json', 'data/market_timeline.json',
    'data/learning_topics.json', 'data/learning_resources.csv'
]

with zipfile.ZipFile('data-deploy.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in files:
        if os.path.exists(f):
            zf.write(f)
            print(f'  added {f} ({os.path.getsize(f)//1024}KB)')
        else:
            print(f'  MISSING {f}')

size = os.path.getsize('data-deploy.zip')
print(f'done: {size//1024}KB ({size//1024//1024}MB)')
