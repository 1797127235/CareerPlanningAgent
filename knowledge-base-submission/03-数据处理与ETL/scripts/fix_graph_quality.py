"""
Fix graph.json data quality:
1. Rebuild skill_tiers.core from must_skills (authoritative, manual)
2. Clean cross-domain contamination in important/bonus tiers
3. Fill empty core_tiers for non-engineering roles
"""
import json
from pathlib import Path

GRAPH_PATH = Path(r'C:\Users\liu\Desktop\CareerPlanningAgent\data\graph.json')

with open(GRAPH_PATH, encoding='utf-8') as f:
    g = json.load(f)

# ── Contamination filters ──────────────────────────────────────────────────────
# Skills that should NOT appear in non-embedded nodes' important/bonus tiers
EMBEDDED_SKILLS = {'嵌入式', 'RTOS', '驱动', '单片机', '固件', '裸机', '汇编', '内核', '总线',
                   'CAN', 'SPI', 'I2C', 'UART', 'GPIO', 'STM32', 'ARM Cortex', 'FreeRTOS'}

# Java-ecosystem skills that contaminate non-Java nodes
JAVA_ECOSYSTEM = {'Java', 'SpringBoot', 'Spring Boot', 'Spring Cloud', 'MyBatis', 'Maven',
                  'JVM', 'Dubbo', 'Struts', 'Hibernate', 'Tomcat', 'JUnit', 'Gradle',
                  'Spring Framework', 'Spring MVC'}

# Android skills contaminating iOS/Flutter/RN
ANDROID_ONLY = {'Android', 'Kotlin', 'Android Studio', 'Gradle'}

# Domain assignments: which nodes are allowed to have these contaminations
EMBEDDED_ALLOWED = {'cpp', 'embedded-cpp', 'infrastructure-engineer', 'storage-database-kernel',
                    'search-engine-engineer', 'systems-cpp'}
JAVA_ALLOWED = {'java', 'android', 'full-stack', 'software-architect', 'engineering-manager',
                'data-engineer', 'data-architect', 'ml-architect', 'backend'}
ANDROID_ALLOWED = {'android', 'flutter', 'react-native', 'full-stack'}


def clean_tier(skills_list, node_id, tier_name):
    """Remove cross-domain contamination from a tier's skill list."""
    if not skills_list:
        return skills_list

    cleaned = []
    removed = []
    for s in skills_list:
        name = s.get('name', '') if isinstance(s, dict) else str(s)
        skip = False

        if name in EMBEDDED_SKILLS and node_id not in EMBEDDED_ALLOWED:
            skip = True
        if name in JAVA_ECOSYSTEM and node_id not in JAVA_ALLOWED:
            skip = True
        if name in ANDROID_ONLY and node_id not in ANDROID_ALLOWED:
            skip = True

        if skip:
            removed.append(name)
        else:
            cleaned.append(s)

    if removed:
        print(f'  [{node_id}] {tier_name}: removed contamination {removed}')
    return cleaned


def build_core_from_must(must_skills, existing_core):
    """Build skill_tiers.core from must_skills with synthetic frequencies.

    Use must_skills as the definitive source. Preserve existing freq values
    for must_skills that already appear in core (for continuity), assign
    descending synthetic values for the rest.
    """
    if not must_skills:
        return existing_core  # can't improve without must_skills

    # Map existing core names → freq for skills that ARE must_skills
    existing_map = {}
    for s in (existing_core or []):
        if isinstance(s, dict):
            name = s.get('name', '')
            freq = s.get('freq', 0)
            must_lower = {m.lower() for m in must_skills}
            if name.lower() in must_lower:
                existing_map[name.lower()] = freq

    result = []
    base_freqs = [0.82, 0.74, 0.68, 0.62, 0.56, 0.50]
    for i, skill in enumerate(must_skills[:6]):
        freq = existing_map.get(skill.lower(), base_freqs[min(i, len(base_freqs)-1)])
        result.append({'name': skill, 'freq': round(freq, 4)})

    return result


# ── Node-specific manual overrides for empty-tier non-engineering roles ────────
MANUAL_TIERS = {
    'engineering-manager': {
        'core': [
            {'name': '团队管理', 'freq': 0.85},
            {'name': '项目管理', 'freq': 0.80},
            {'name': '技术规划', 'freq': 0.70},
        ],
        'important': [
            {'name': '绩效管理', 'freq': 0.55},
            {'name': '招聘面试', 'freq': 0.50},
            {'name': '跨团队协作', 'freq': 0.45},
            {'name': '技术方案评审', 'freq': 0.40},
        ],
        'bonus': [
            {'name': '敏捷开发', 'freq': 0.35},
            {'name': 'OKR', 'freq': 0.28},
        ],
    },
    'product-manager': {
        'core': [
            {'name': '需求分析', 'freq': 0.88},
            {'name': '产品规划', 'freq': 0.82},
            {'name': '用户研究', 'freq': 0.72},
        ],
        'important': [
            {'name': 'Axure', 'freq': 0.55},
            {'name': 'Figma', 'freq': 0.48},
            {'name': '数据分析', 'freq': 0.45},
            {'name': '竞品分析', 'freq': 0.42},
        ],
        'bonus': [
            {'name': 'SQL', 'freq': 0.30},
            {'name': 'A/B测试', 'freq': 0.25},
        ],
    },
    'ux-design': {
        'core': [
            {'name': 'Figma', 'freq': 0.88},
            {'name': 'UI设计', 'freq': 0.82},
            {'name': '用户研究', 'freq': 0.70},
        ],
        'important': [
            {'name': 'Sketch', 'freq': 0.52},
            {'name': '原型设计', 'freq': 0.48},
            {'name': '交互设计', 'freq': 0.45},
            {'name': 'Adobe XD', 'freq': 0.38},
        ],
        'bonus': [
            {'name': 'After Effects', 'freq': 0.28},
            {'name': 'Design System', 'freq': 0.25},
        ],
    },
    'cto': {
        'core': [
            {'name': '技术战略', 'freq': 0.88},
            {'name': '架构设计', 'freq': 0.82},
            {'name': '团队建设', 'freq': 0.75},
        ],
        'important': [
            {'name': '技术规划', 'freq': 0.60},
            {'name': '预算管理', 'freq': 0.52},
            {'name': '业务理解', 'freq': 0.48},
        ],
        'bonus': [
            {'name': '创业经验', 'freq': 0.35},
            {'name': '融资对接', 'freq': 0.28},
        ],
    },
    'technical-writer': {
        'core': [
            {'name': 'Markdown', 'freq': 0.85},
            {'name': '技术文档', 'freq': 0.80},
            {'name': 'API文档', 'freq': 0.68},
        ],
        'important': [
            {'name': 'Git', 'freq': 0.55},
            {'name': 'Confluence', 'freq': 0.48},
            {'name': '技术理解', 'freq': 0.45},
        ],
        'bonus': [
            {'name': 'Docusaurus', 'freq': 0.28},
            {'name': 'Sphinx', 'freq': 0.22},
        ],
    },
    'devrel': {
        'core': [
            {'name': '技术布道', 'freq': 0.85},
            {'name': '社区运营', 'freq': 0.78},
            {'name': '公开演讲', 'freq': 0.68},
        ],
        'important': [
            {'name': '开源贡献', 'freq': 0.55},
            {'name': '技术写作', 'freq': 0.50},
            {'name': '开发者关系', 'freq': 0.45},
        ],
        'bonus': [
            {'name': 'Demo开发', 'freq': 0.35},
            {'name': 'SDK集成', 'freq': 0.28},
        ],
    },
    'game-developer': {
        'core': [
            {'name': 'C++', 'freq': 0.80},
            {'name': 'Unreal', 'freq': 0.72},
            {'name': 'Unity', 'freq': 0.65},
        ],
        'important': [
            {'name': '图形渲染', 'freq': 0.55},
            {'name': '性能优化', 'freq': 0.50},
            {'name': 'OpenGL', 'freq': 0.42},
            {'name': 'Lua', 'freq': 0.38},
        ],
        'bonus': [
            {'name': 'Python', 'freq': 0.30},
            {'name': '物理引擎', 'freq': 0.25},
            {'name': 'Shader', 'freq': 0.22},
        ],
    },
    'server-side-game-developer': {
        'core': [
            {'name': 'C++', 'freq': 0.78},
            {'name': '多线程', 'freq': 0.70},
            {'name': '网络编程', 'freq': 0.65},
        ],
        'important': [
            {'name': 'Linux', 'freq': 0.58},
            {'name': '高并发', 'freq': 0.50},
            {'name': 'Redis', 'freq': 0.45},
            {'name': 'MySQL', 'freq': 0.40},
        ],
        'bonus': [
            {'name': 'Lua', 'freq': 0.35},
            {'name': 'Protobuf', 'freq': 0.28},
            {'name': 'Go', 'freq': 0.22},
        ],
    },
    'cyber-security': {
        'core': [
            {'name': 'Python', 'freq': 0.78},
            {'name': '渗透测试', 'freq': 0.72},
            {'name': '漏洞分析', 'freq': 0.65},
        ],
        'important': [
            {'name': 'Linux', 'freq': 0.60},
            {'name': '网络协议', 'freq': 0.55},
            {'name': 'CTF', 'freq': 0.45},
            {'name': 'Burp Suite', 'freq': 0.40},
        ],
        'bonus': [
            {'name': 'C', 'freq': 0.35},
            {'name': '逆向工程', 'freq': 0.30},
            {'name': 'Metasploit', 'freq': 0.25},
        ],
    },
    'ai-red-teaming': {
        'core': [
            {'name': 'Python', 'freq': 0.82},
            {'name': 'AI安全', 'freq': 0.75},
            {'name': '红队测试', 'freq': 0.68},
        ],
        'important': [
            {'name': 'LLM', 'freq': 0.60},
            {'name': '对抗样本', 'freq': 0.50},
            {'name': '渗透测试', 'freq': 0.45},
        ],
        'bonus': [
            {'name': 'PyTorch', 'freq': 0.38},
            {'name': '提示注入', 'freq': 0.32},
        ],
    },
    'blockchain': {
        'core': [
            {'name': 'Solidity', 'freq': 0.80},
            {'name': '智能合约', 'freq': 0.72},
            {'name': 'Web3.js', 'freq': 0.62},
        ],
        'important': [
            {'name': 'Ethereum', 'freq': 0.55},
            {'name': 'Hardhat', 'freq': 0.45},
            {'name': 'Go', 'freq': 0.40},
            {'name': 'Rust', 'freq': 0.35},
        ],
        'bonus': [
            {'name': 'DeFi', 'freq': 0.30},
            {'name': 'NFT', 'freq': 0.25},
            {'name': 'Layer2', 'freq': 0.22},
        ],
    },
    'security-architect': {
        'core': [
            {'name': '安全架构', 'freq': 0.85},
            {'name': '零信任', 'freq': 0.72},
            {'name': '威胁建模', 'freq': 0.65},
        ],
        'important': [
            {'name': 'SIEM', 'freq': 0.55},
            {'name': '合规审计', 'freq': 0.50},
            {'name': 'PKI', 'freq': 0.42},
        ],
        'bonus': [
            {'name': 'CISSP', 'freq': 0.38},
            {'name': 'ISO 27001', 'freq': 0.30},
        ],
    },
}


# ── Process all nodes ──────────────────────────────────────────────────────────
fixed_count = 0
for n in g['nodes']:
    nid = n['node_id']
    must = n.get('must_skills', [])
    tiers = n.get('skill_tiers', {})

    if not isinstance(tiers, dict):
        tiers = {}

    # Use manual override if available
    if nid in MANUAL_TIERS:
        n['skill_tiers'] = {
            **MANUAL_TIERS[nid],
            'total_jds': tiers.get('total_jds', 0),
            'year_range': tiers.get('year_range', '2021-2024'),
        }
        print(f'[{nid}] Applied manual skill_tiers override')
        fixed_count += 1
        continue

    existing_core = tiers.get('core', [])
    existing_imp = tiers.get('important', [])
    existing_bonus = tiers.get('bonus', [])

    # Check if core needs rebuilding
    must_set = {s.lower() for s in must}
    core_names = {(c.get('name','') if isinstance(c, dict) else c).lower() for c in existing_core}
    core_overlap = must_set & core_names

    new_core = existing_core
    changed = False

    if not core_overlap and must:
        # Core is contaminated or empty — rebuild from must_skills
        new_core = build_core_from_must(must, existing_core)
        print(f'[{nid}] Rebuilt core from must_skills: {[s["name"] for s in new_core]}')
        changed = True
    elif must and existing_core:
        # Core has some overlap but might be ordered wrong — ensure must[0] is first
        first_core_name = (existing_core[0].get('name') if isinstance(existing_core[0], dict) else existing_core[0]).lower()
        if first_core_name not in must_set:
            # Must_skills primary isn't first — rebuild to ensure correct ordering
            new_core = build_core_from_must(must, existing_core)
            print(f'[{nid}] Reordered core (was {first_core_name!r}, now {must[0]!r} first)')
            changed = True

    # Clean contamination from all tiers
    cleaned_core = clean_tier(new_core, nid, 'core')
    cleaned_imp = clean_tier(existing_imp, nid, 'important')
    cleaned_bonus = clean_tier(existing_bonus, nid, 'bonus')

    if (cleaned_core != new_core or cleaned_imp != existing_imp or
            cleaned_bonus != existing_bonus or changed):
        n['skill_tiers'] = {
            'core': cleaned_core,
            'important': cleaned_imp,
            'bonus': cleaned_bonus,
            'total_jds': tiers.get('total_jds', 0),
            'year_range': tiers.get('year_range', '2021-2024'),
        }
        fixed_count += 1

print(f'\nFixed {fixed_count} nodes out of {len(g["nodes"])} total')

# ── Write back ─────────────────────────────────────────────────────────────────
with open(GRAPH_PATH, 'w', encoding='utf-8') as f:
    json.dump(g, f, ensure_ascii=False, indent=2)
print(f'Written to {GRAPH_PATH}')
