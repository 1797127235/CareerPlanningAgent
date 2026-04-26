import re

def migrate_page(src, dst):
    with open(src, 'r', encoding='utf-8') as f:
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
    
    if 'PursuitDetailPage' in content:
        content = content.replace("import { sendToCoach } from '@/hooks/useCoachTrigger'", "import { sendToCoach } from '@/hooks/useCoachTrigger'\nimport Navbar from '@/components/shared/Navbar'")
    
    if 'JDDiagnosisPage' in content:
        content = content.replace("import { CoachInsightCard } from '@/components/CoachInsightCard'", "import { CoachInsightCard } from '@/components/CoachInsightCard'\nimport Navbar from '@/components/shared/Navbar'")
    
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Migrated {src} -> {dst}')

migrate_page('../frontend/src/pages/PursuitDetailPage.tsx', 'src/pages/PursuitDetailPage.tsx')
migrate_page('../frontend/src/pages/JDDiagnosisPage.tsx', 'src/pages/JDDiagnosisPage.tsx')
