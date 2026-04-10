# -*- coding: utf-8 -*-
"""
从八股文 PDF 中提取面试题，输出为可导入的 CSV。

用法:
    python scripts/extract_bagu_questions.py "E:\...\计算机基础篇（最强八股文）第五版 .pdf"

输出:
    scripts/bagu_questions.csv  (可直接用 import_interview_questions.py 导入)
"""
import sys
import csv
import re
from pathlib import Path

import PyPDF2


# ── 页码范围 → 技能分类映射 ──
PAGE_CATEGORIES = [
    (1,   100, "计算机网络", "networking"),
    (100, 155, "计算机网络", "networking"),
    (155, 210, "操作系统",   "operating_system"),
    (210, 250, "操作系统",   "operating_system"),
    (250, 300, "MySQL",      "database"),
    (300, 340, "Redis",      "redis"),
    (340, 356, "计算机组成原理", "computer_architecture"),
]


def get_category(page_num: int) -> tuple[str, str]:
    """Return (skill_tag, node_hint) for a given 1-based page number."""
    for start, end, tag, hint in PAGE_CATEGORIES:
        if start <= page_num < end:
            return tag, hint
    return "计算机基础", "cs_fundamentals"


def is_question_header(line: str, prev_line: str, next_line: str) -> bool:
    """Heuristic: is this line a section header / interview question?"""
    line = line.strip()
    if not line or len(line) < 3:
        return False
    # Too long to be a header
    if len(line) > 80:
        return False
    # Skip pure numbering or code
    if re.match(r'^[\d.、\s]+$', line):
        return False
    if line.startswith(('#', '//', '/*', 'int ', 'void ', 'class ', '{', '}', 'import ')):
        return False
    if line.startswith('http') or line.startswith('www'):
        return False

    # Strong signals: ends with question mark
    if '？' in line or '?' in line:
        return True
    # Strong signals: starts with question keyword
    q_starts = ['什么是', '为什么', '如何', '怎么', '怎样', '哪些', '解释',
                '描述', '说说', '讲讲', '谈谈', '列举', '对比', '区别',
                '简述', '介绍', '总结']
    for qs in q_starts:
        if line.startswith(qs):
            return True

    # Medium signals: short standalone title line (likely a topic header)
    # Only accept if it looks like a real topic title, not a sentence fragment
    if len(line) <= 45:
        # Reject numbered list items
        if re.match(r'^\d+[.、）)]\s', line):
            return False
        # Reject fragments (ends with punctuation that continues a sentence)
        if line[-1] in '，；、：:,;。的了着过呢吗和与或及':
            return False
        # Reject lines that are clearly continuations
        if line[0] in '如果但是因为所以并且而且然而不过其中例如比如即也就':
            return False
        # Reject very short generic lines
        if len(line) < 6:
            return False
        # Must look like a topic: contains a noun-like structure
        # Accept patterns like "XXX是什么", "XXX的YYY", "XXX和YYY的区别"
        topic_patterns = [
            r'是什么', r'的区别', r'的原理', r'的过程', r'的作用',
            r'有哪些', r'的特点', r'的优缺点', r'的实现', r'的机制',
            r'和.*的区别', r'与.*的区别', r'VS', r'vs',
        ]
        for pat in topic_patterns:
            if re.search(pat, line):
                return True
        # Accept if it looks like a standalone topic name (no verb-heavy sentence)
        if re.search(r'[\u4e00-\u9fff]', line) and not re.search(r'[，。；]', line):
            # Must not be a sentence (heuristic: no common sentence particles)
            if not any(w in line for w in ['可以', '需要', '就会', '然后', '通过', '进行', '使用', '用于', '也是', '就是', '还有', '以及']):
                return True

    return False


def extract_questions(pdf_path: str) -> list[dict]:
    """Extract Q&A pairs from the PDF."""
    reader = PyPDF2.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"PDF 页数: {total_pages}")

    # First, extract all text with page numbers
    all_lines: list[tuple[int, str]] = []  # (page_num, line_text)
    for i in range(total_pages):
        text = reader.pages[i].extract_text()
        if not text:
            continue
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped:
                all_lines.append((i + 1, stripped))

    print(f"总行数: {len(all_lines)}")

    # Identify headers
    questions = []
    header_indices = []

    for idx in range(len(all_lines)):
        page, line = all_lines[idx]
        prev = all_lines[idx - 1][1] if idx > 0 else ""
        nxt = all_lines[idx + 1][1] if idx < len(all_lines) - 1 else ""

        if is_question_header(line, prev, nxt):
            header_indices.append(idx)

    print(f"识别到的标题/问题数: {len(header_indices)}")

    # Extract Q&A pairs: question = header, answer = text until next header
    for i, h_idx in enumerate(header_indices):
        page, question = all_lines[h_idx]
        skill_tag, _ = get_category(page)

        # Collect answer lines until next header
        end_idx = header_indices[i + 1] if i + 1 < len(header_indices) else len(all_lines)
        answer_lines = []
        for j in range(h_idx + 1, min(end_idx, h_idx + 30)):  # Cap at 30 lines per answer
            answer_lines.append(all_lines[j][1])

        answer = '\n'.join(answer_lines).strip()

        # Filter: skip if answer is too short (likely a sub-header with no content)
        if len(answer) < 20:
            continue
        # Filter: skip category names, section labels, generic text
        skip_patterns = [
            r'^计算机[⽹网]络$', r'^操作系统$', r'^MySQL$', r'^Redis$',
            r'^计算机组成原理$', r'^HTTP', r'^TCP$', r'^UDP$', r'^DNS$',
            r'^基础知识', r'^总结[：:]?$', r'^注[：:]', r'^注意',
            r'^解释[：:]$', r'^补充', r'^扩展', r'^延伸', r'^参考',
            r'^⼀问⼀答', r'^[⾼高]频[重]点', r'^讲解', r'^章节',
            r'^\d+[、.）)]', r'^[\(（]\d',  # Numbered items
            r'^这[⾥里]', r'^这⼀步', r'^这[个道是]',  # Sentence continuations starting with 这
        ]
        skip = False
        for pat in skip_patterns:
            if re.search(pat, question):
                skip = True
                break
        if skip:
            continue
        # Skip if question is too generic (< 5 meaningful chars)
        clean = re.sub(r'[^\u4e00-\u9fff\w]', '', question)
        if len(clean) < 5:
            continue
        # Skip lines that are clearly sentence fragments (contain "的" at end)
        if question.endswith('的') or question.endswith('是'):
            continue

        # Determine difficulty based on answer length
        if len(answer) > 500:
            difficulty = 'hard'
        elif len(answer) > 200:
            difficulty = 'medium'
        else:
            difficulty = 'easy'

        questions.append({
            'skill_tag': skill_tag,
            'question': question,
            'answer_key': answer[:500],  # Truncate very long answers
            'difficulty': difficulty,
            'page': page,
        })

    # Deduplicate by question text
    seen = set()
    unique = []
    for q in questions:
        key = q['question'].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    print(f"去重后题目数: {len(unique)}")
    return unique


def write_csv(questions: list[dict], output_path: str):
    """Write questions to CSV in import format."""
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'node_id', 'skill_tag', 'question', 'question_type', 'difficulty', 'answer_key'
        ])
        writer.writeheader()
        for q in questions:
            writer.writerow({
                'node_id': '',  # Will be matched during import
                'skill_tag': q['skill_tag'],
                'question': q['question'],
                'question_type': 'technical',
                'difficulty': q['difficulty'],
                'answer_key': q['answer_key'],
            })
    print(f"已写入: {output_path}")


def main():
    if len(sys.argv) < 2:
        pdf_path = r'E:\BaiduNetdiskDownload\八股文（计算机篇）\计算机基础篇（最强八股文）第五版 .pdf'
    else:
        pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"文件不存在: {pdf_path}")
        sys.exit(1)

    questions = extract_questions(pdf_path)

    # Show category breakdown
    from collections import Counter
    cats = Counter(q['skill_tag'] for q in questions)
    print("\n分类统计:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count} 题")

    # Show some samples
    print("\n示例题目:")
    for q in questions[:10]:
        print(f"  [{q['difficulty']}] {q['skill_tag']}: {q['question']}")

    output = Path(__file__).parent / 'bagu_questions.csv'
    write_csv(questions, str(output))
    print(f"\n完成！共 {len(questions)} 道题")
    print(f"下一步：python scripts/import_interview_questions.py scripts/bagu_questions.csv")


if __name__ == '__main__':
    main()
