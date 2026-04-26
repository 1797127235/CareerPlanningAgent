import re

with open('src/components/ChatPanel.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r'var\(--blue\)', 'var(--chestnut)'),
    (r'bg-slate-500', 'bg-[#8A7E6B]'),
    (r'text-slate-800', 'text-[#1F1F1F]'),
    (r'text-slate-700', 'text-[#3D352E]'),
    (r'text-slate-600', 'text-[#6B5E4F]'),
    (r'text-slate-500', 'text-[#8A7E6B]'),
    (r'text-slate-400', 'text-[#A89B8C]'),
    (r'text-slate-300', 'text-[#C4B8A8]'),
    (r'border-slate-200', 'border-[rgba(107,62,46,0.12)]'),
    (r'border-slate-100', 'border-[rgba(107,62,46,0.08)]'),
    (r'bg-slate-100', 'bg-[#F2EDE4]'),
    (r'hover:text-slate-500', 'hover:text-[#8A7E6B]'),
    (r'hover:text-slate-700', 'hover:text-[#3D352E]'),
    (r'hover:bg-slate-100', 'hover:bg-[#F2EDE4]'),
    (r'placeholder:text-slate-400', 'placeholder:text-[#A89B8C]'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open('src/components/ChatPanel.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
