"""Split the cpp node into 嵌入式工程师 and 系统C++工程师."""
import json

GRAPH_PATH = r'C:\Users\liu\Desktop\CareerPlanningAgent\data\graph.json'

with open(GRAPH_PATH, encoding='utf-8') as f:
    g = json.load(f)

# ── 1. Reclassify cpp → 嵌入式工程师 ─────────────────────────────────────────
for n in g['nodes']:
    if n['node_id'] == 'cpp':
        n['label'] = '嵌入式工程师'
        n['role_family'] = '嵌入式/硬件'
        n['must_skills'] = ['C++', '嵌入式Linux', 'RTOS', '驱动开发', '单片机', '操作系统']
        n['core_tasks'] = ['驱动开发', '嵌入式系统', '硬件接口', '实时操作系统', '固件开发']
        n['salary_p50'] = 22000
        n['zone'] = 'thrive'
        n['description'] = (
            '岗位中文名：嵌入式工程师。\n\n'
            '嵌入式工程师专注于硬件与软件的交叉领域，负责在资源受限的设备上开发软件。'
            '主要使用 C/C++ 编写底层驱动、实时操作系统（RTOS）和固件，广泛应用于'
            '汽车电子、消费电子、工业控制和物联网（IoT）领域。'
        )
        n['market_insight'] = (
            '嵌入式方向在汽车电子（新能源车）、工业自动化、消费电子领域需求稳定。'
            '车载系统（AUTOSAR/ISO 26262）是当前增长最快的细分方向。'
            '招聘方：比亚迪、华为车BU、大疆、海康威视、汇川技术。'
        )
        n['distinguishing_features'] = ['嵌入式Linux驱动开发', 'RTOS/裸机开发', '车载/工业控制场景']
        n['not_this_role_if'] = ['主要做后端服务', '无硬件接口经验', '不接触操作系统底层']
        n['promotion_path'] = [
            {'level': 1, 'title': '初级嵌入式工程师'},
            {'level': 2, 'title': '嵌入式工程师'},
            {'level': 3, 'title': '高级嵌入式工程师'},
            {'level': 4, 'title': '嵌入式技术专家'},
            {'level': 5, 'title': '硬件架构师'},
        ]
        n['typical_employers'] = ['比亚迪', '华为', '大疆', '海康威视', '汇川技术', '中兴', '联发科', '高通']
        n['skill_tiers'] = {
            'core': [
                {'name': '嵌入式', 'freq': 0.72},
                {'name': 'C++',    'freq': 0.65},
                {'name': 'Linux',  'freq': 0.55},
            ],
            'important': [
                {'name': '驱动',     'freq': 0.42},
                {'name': 'RTOS',    'freq': 0.38},
                {'name': '操作系统', 'freq': 0.35},
                {'name': '单片机',  'freq': 0.30},
            ],
            'bonus': [
                {'name': 'TCP/IP', 'freq': 0.18},
                {'name': '汇编',   'freq': 0.15},
                {'name': '内核',   'freq': 0.14},
                {'name': 'Python', 'freq': 0.10},
            ],
            'total_jds': 12000,
            'year_range': '2021-2024',
        }
        print('OK: cpp -> 嵌入式工程师 updated')
        break

# ── 2. Add systems-cpp node ───────────────────────────────────────────────────
systems_cpp = {
    'node_id': 'systems-cpp',
    'label': '系统C++工程师',
    'role_family': '后端开发',
    'zone': 'safe',
    'career_level': 2,
    'replacement_pressure': 28.0,
    'human_ai_leverage': 90.0,
    'onet_codes': ['15-1252', '15-1241'],
    'must_skills': ['C++', '多线程', 'Linux', '网络编程', 'STL', '性能优化'],
    'core_tasks': ['高并发服务端', '网络框架开发', '内存管理', '性能调优', '基础组件'],
    'soft_skills': {'communication': 2, 'learning': 3, 'resilience': 3, 'innovation': 3, 'collaboration': 2},
    'salary_p50': 28000,
    'routine_score': 40,
    'is_milestone': False,
    'skill_count': 6,
    'promotion_path': [
        {'level': 1, 'title': '初级系统C++工程师'},
        {'level': 2, 'title': '系统C++工程师'},
        {'level': 3, 'title': '高级系统C++工程师'},
        {'level': 4, 'title': 'C++技术专家'},
        {'level': 5, 'title': '基础架构架构师'},
    ],
    'description': (
        '岗位中文名：系统C++工程师。\n\n'
        '系统C++工程师专注于高性能后端系统和基础组件开发，使用C++构建网络框架、'
        '内存池、消息队列等核心基础设施。这个方向注重底层系统能力：多线程并发、'
        '网络I/O模型（Reactor/Proactor）、内存管理和极致性能调优。'
        '广泛应用于互联网中间件、搜索引擎、数据库内核、游戏服务端和金融系统。'
    ),
    'market_insight': (
        '系统C++工程师在大厂基础架构团队（字节/阿里/腾讯/百度）、'
        '数据库公司（PingCAP/OceanBase/StarRocks）、游戏服务端和量化交易领域需求稳健。'
        '入门门槛高但竞争对手少于Java，薪资普遍高10-15%。'
        '项目质量是核心竞争力：高并发内存池、Reactor网络框架是有力背书。'
    ),
    'ai_impact_narrative': (
        'AI对系统C++的影响最小——自动生成的代码在高并发和内存安全场景下往往有严重问题。'
        'C++工程师的核心价值在于对系统底层的深度理解：cache line优化、无锁数据结构、'
        'NUMA感知内存分配。'
    ),
    'differentiation_advice': (
        '做一个真实有挑战的C++项目：高并发内存池（参考tcmalloc）、'
        '基于Reactor模型的网络库（参考muduo）。'
        '关键是要有benchmark数据、压测分析和性能对比。'
    ),
    'typical_employers': ['字节跳动', '腾讯', '百度', '阿里巴巴', 'PingCAP', 'OceanBase', '网易互娱'],
    'entry_barrier': 'high',
    'career_ceiling': '3年到高级工程师，50-80万。5年到C++技术专家/基础架构架构师，80-150万。',
    'related_majors': ['计算机科学', '软件工程', '电子信息'],
    'min_experience': 0,
    'distinguishing_features': ['Reactor/Proactor网络模型', '高并发内存池/协程', '自研基础组件'],
    'not_this_role_if': ['主要做业务CRUD', '无C++多线程/网络项目', '主要用Java/Python'],
    'project_recommendations': [
        {
            'name': '基于Reactor模型的C++高性能网络库',
            'why': 'epoll/非阻塞IO/定时器/缓冲区管理——全是系统C++面试必考点。',
            'difficulty': 'hard',
        },
        {
            'name': 'C++高并发内存池（参考tcmalloc）',
            'why': '内存管理是C++核心差异化能力。多级缓存设计、线程安全、与系统分配器的性能对比。',
            'difficulty': 'hard',
        },
    ],
    'skill_tiers': {
        'core': [
            {'name': 'C++',    'freq': 0.82},
            {'name': '多线程', 'freq': 0.68},
            {'name': 'Linux',  'freq': 0.62},
            {'name': '网络编程','freq': 0.55},
        ],
        'important': [
            {'name': 'STL',    'freq': 0.45},
            {'name': '高并发', 'freq': 0.40},
            {'name': '性能优化','freq': 0.38},
            {'name': '内存管理','freq': 0.32},
            {'name': 'GDB',    'freq': 0.22},
            {'name': 'CMake',  'freq': 0.20},
        ],
        'bonus': [
            {'name': '分布式系统','freq': 0.18},
            {'name': '数据结构', 'freq': 0.16},
            {'name': '协程',    'freq': 0.14},
            {'name': '消息队列', 'freq': 0.12},
            {'name': 'gRPC',   'freq': 0.10},
        ],
        'total_jds': 8000,
        'year_range': '2021-2024',
    },
}

# Avoid duplicates
if not any(n['node_id'] == 'systems-cpp' for n in g['nodes']):
    g['nodes'].append(systems_cpp)
    print('OK: systems-cpp node added')
else:
    print('SKIP: systems-cpp already exists')

# ── 3. Update edges ───────────────────────────────────────────────────────────
remove_edges = {
    ('cpp', 'game-developer'),
    ('cpp', 'server-side-game-developer'),
    ('cpp', 'golang'),
    ('cpp', 'search-engine-engineer'),
    ('cpp', 'storage-database-kernel'),
    ('cpp', 'software-architect'),
}
before = len(g['edges'])
g['edges'] = [e for e in g['edges'] if (e['source'], e['target']) not in remove_edges]
print(f'OK: removed {before - len(g["edges"])} cpp edges')

new_edges = [
    # 嵌入式 can pivot to systems C++ or Rust
    {'source': 'cpp',         'target': 'systems-cpp',            'edge_type': 'lateral',  'gap_skills': ['网络编程', '高并发', '多线程'], 'estimated_hours': 300},
    {'source': 'cpp',         'target': 'rust',                   'edge_type': 'lateral',  'gap_skills': ['Rust', '所有权模型'],          'estimated_hours': 200},
    # systems-cpp edges
    {'source': 'systems-cpp', 'target': 'golang',                 'edge_type': 'natural',  'gap_skills': ['Go', 'gRPC', 'Kubernetes'],    'estimated_hours': 200},
    {'source': 'systems-cpp', 'target': 'rust',                   'edge_type': 'lateral',  'gap_skills': ['Rust', '所有权模型'],          'estimated_hours': 180},
    {'source': 'systems-cpp', 'target': 'search-engine-engineer', 'edge_type': 'lateral',  'gap_skills': ['倒排索引', '分布式检索'],       'estimated_hours': 400},
    {'source': 'systems-cpp', 'target': 'storage-database-kernel','edge_type': 'lateral',  'gap_skills': ['存储引擎', 'LSM Tree', 'MVCC'],'estimated_hours': 500},
    {'source': 'systems-cpp', 'target': 'infrastructure-engineer','edge_type': 'lateral',  'gap_skills': ['Kubernetes', 'Docker', '云原生'],'estimated_hours': 350},
    {'source': 'systems-cpp', 'target': 'software-architect',     'edge_type': 'vertical', 'gap_skills': ['架构设计', '系统设计'],         'estimated_hours': 800},
    {'source': 'systems-cpp', 'target': 'game-developer',         'edge_type': 'lateral',  'gap_skills': ['Unreal', '图形渲染'],          'estimated_hours': 400},
]

# Avoid duplicates
existing = {(e['source'], e['target']) for e in g['edges']}
added = 0
for e in new_edges:
    if (e['source'], e['target']) not in existing:
        g['edges'].append(e)
        existing.add((e['source'], e['target']))
        added += 1
print(f'OK: added {added} new edges')

# ── 4. Invalidate profile cache (clear _ROLE_LIST_CACHE note) ─────────────────
with open(GRAPH_PATH, 'w', encoding='utf-8') as f:
    json.dump(g, f, ensure_ascii=False, indent=2)

print(f'DONE: {len(g["nodes"])} nodes, {len(g["edges"])} edges written to graph.json')
