# -*- coding: utf-8 -*-
"""
用 LLM 从八股文原始文本中提取面试题。

读取 scripts/bagu_raw_*.txt，每次发送一段给 LLM，
让 LLM 识别出面试题并输出 JSON，最后合并为 CSV。

用法:
    python scripts/llm_extract_questions.py
"""
import json
import csv
import os
import glob
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.nodes.utils import get_llm_client

SYSTEM_PROMPT = """你是一个面试题提取专家。用户会给你一段计算机面试八股文的原始文本。

你的任务：从文本中识别出所有可以作为面试题的问题，并提取出来。

规则：
1. 只提取真正的面试题（如"TCP三次握手的过程是什么？"、"索引有哪些类别？"），不要提取描述性句子
2. 每道题要有完整的问句表述，不能是半句话
3. 如果原文标题不是问句形式，改写为问句（如 "DNS解析过程" → "DNS的解析过程是什么？"）
4. 为每道题标注难度：easy/medium/hard
5. 提取对应的答案要点（简洁版，不超过200字）

输出严格 JSON 数组：
[
  {
    "question": "TCP三次握手的过程是什么？",
    "answer_key": "第一次握手：客户端发送SYN...",
    "difficulty": "medium"
  }
]

只输出 JSON，不要其他内容。"""


def extract_from_chunk(text: str, category: str, chunk_idx: int) -> list[dict]:
    """Send a text chunk to LLM and extract questions."""
    client = get_llm_client()
    if not client:
        print(f"  [!] LLM client not available, skipping chunk {chunk_idx}")
        return []

    user_prompt = f"以下是「{category}」分类的面试八股文内容，请提取面试题：\n\n{text}"

    try:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4000,
        )
        content = response.choices[0].message.content.strip()

        # Parse JSON from response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        questions = json.loads(content)
        return questions if isinstance(questions, list) else []
    except json.JSONDecodeError as e:
        print(f"  [!] JSON parse error in chunk {chunk_idx}: {e}")
        return []
    except Exception as e:
        print(f"  [!] LLM error in chunk {chunk_idx}: {e}")
        return []


def process_category(filepath: str, category: str) -> list[dict]:
    """Process one category file, splitting into chunks for LLM."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Split into ~3000 char chunks (LLM context limit friendly)
    chunk_size = 3000
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        # Try to break at newline
        if i + chunk_size < len(text):
            last_newline = chunk.rfind('\n')
            if last_newline > chunk_size * 0.5:
                chunk = chunk[:last_newline]
        chunks.append(chunk)

    print(f"\n{'='*50}")
    print(f"分类: {category} | 文件: {os.path.basename(filepath)}")
    print(f"总字符: {len(text)} | 分块数: {len(chunks)}")

    all_questions = []
    for idx, chunk in enumerate(chunks):
        print(f"  处理块 {idx+1}/{len(chunks)}...", end=" ", flush=True)
        questions = extract_from_chunk(chunk, category, idx)
        print(f"提取到 {len(questions)} 题")
        for q in questions:
            q['skill_tag'] = category
        all_questions.extend(questions)
        time.sleep(0.5)  # Rate limit

    print(f"  小计: {len(all_questions)} 题")
    return all_questions


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_files = sorted(glob.glob(os.path.join(script_dir, 'bagu_raw_*.txt')))

    if not raw_files:
        print("未找到 bagu_raw_*.txt 文件，请先运行 extract_bagu_questions.py")
        sys.exit(1)

    print(f"找到 {len(raw_files)} 个分类文件")

    all_questions = []
    for filepath in raw_files:
        # Extract category from filename: bagu_raw_计算机网络.txt -> 计算机网络
        basename = os.path.basename(filepath)
        category = basename.replace('bagu_raw_', '').replace('.txt', '')
        questions = process_category(filepath, category)
        all_questions.extend(questions)

    # Deduplicate
    seen = set()
    unique = []
    for q in all_questions:
        key = q['question'].strip().lower()
        if key not in seen and len(q['question']) >= 6:
            seen.add(key)
            unique.append(q)

    print(f"\n{'='*50}")
    print(f"总计: {len(unique)} 道去重后面试题")

    # Category breakdown
    from collections import Counter
    cats = Counter(q['skill_tag'] for q in unique)
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")

    # Write CSV
    output = os.path.join(script_dir, 'bagu_questions_llm.csv')
    with open(output, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'node_id', 'skill_tag', 'question', 'question_type', 'difficulty', 'answer_key'
        ])
        writer.writeheader()
        for q in unique:
            writer.writerow({
                'node_id': '',
                'skill_tag': q['skill_tag'],
                'question': q['question'],
                'question_type': 'technical',
                'difficulty': q.get('difficulty', 'medium'),
                'answer_key': q.get('answer_key', '')[:500],
            })

    print(f"\n已写入: {output}")
    print(f"导入命令: python scripts/import_interview_questions.py {output}")


if __name__ == '__main__':
    main()
