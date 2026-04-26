import re

with open('../frontend/src/pages/InterviewPage.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace slate colors
content = content.replace('text-slate-900', 'text-[var(--ink-1)]')
content = content.replace('text-slate-800', 'text-[var(--ink-1)]')
content = content.replace('text-slate-700', 'text-[var(--ink-1)]')
content = content.replace('text-slate-600', 'text-[var(--ink-2)]')
content = content.replace('text-slate-500', 'text-[var(--ink-2)]')
content = content.replace('text-slate-400', 'text-[var(--ink-3)]')
content = content.replace('text-slate-300', 'text-[var(--ink-3)]')

content = content.replace('bg-slate-50', 'bg-[var(--bg-card)]')
content = content.replace('bg-slate-100', 'bg-[var(--bg-card)]')
content = content.replace('bg-slate-200', 'bg-[var(--line)]')
content = content.replace('bg-slate-300', 'bg-[var(--line)]')

content = content.replace('border-slate-200', 'border-[var(--line)]')
content = content.replace('border-slate-100', 'border-[var(--line)]')

# Replace glass / glass-static with solid card style
content = content.replace('glass-static', 'rounded-xl')
content = content.replace(' glass ', ' rounded-xl p-5 ')
content = content.replace('"glass"', '"rounded-xl p-5"')
content = content.replace("className=\"glass\"", "className=\"rounded-xl p-5\"")

# Add Navbar import
content = content.replace("import { rawFetch } from '@/api/client'", "import { rawFetch } from '@/api/client'\nimport Navbar from '@/components/shared/Navbar'")

# Wrap default export with main+Navbar
# Find the export default function line and wrap its outer return
content = content.replace(
    'export default function InterviewPage() {',
    'export default function InterviewPage() {\n  return (\n    <main className="min-h-screen pt-[64px]" style={{ background: "var(--bg-paper)", color: "var(--ink-1)" }}>\n      <Navbar />\n      <_InterviewPage />\n    </main>\n  )\n}\n\nfunction _InterviewPage() {'
)

with open('src/pages/InterviewPage.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Migrated InterviewPage.tsx')
