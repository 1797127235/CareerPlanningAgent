import re

with open('src/components/explorer/Coverflow.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Front card bookmark style
old_front = '''              <div
                className="absolute inset-0 rounded-[20px] bg-[var(--bg-card)] border border-[var(--line)] overflow-hidden p-6 flex flex-col"
                style={{
                  backfaceVisibility: 'hidden',
                  boxShadow: isLocateTarget
                    ? '0 0 40px rgba(184,92,56,0.3), 0 16px 48px rgba(107,62,46,.18)'
                    : isCenter ? '0 16px 48px rgba(107,62,46,.14)' : '0 8px 32px rgba(107,62,46,.08)',
                  borderColor: isLocateTarget ? 'rgba(184,92,56,0.4)' : undefined,
                  transition: 'box-shadow 0.6s ease-out, border-color 0.6s ease-out',
                }}
              >
                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${ZONE_STRIP[node.zone] ?? ZONE_STRIP[DEFAULT_ZONE]}`} />'''

new_front = '''              <div
                className="absolute inset-0 rounded-t-[20px] rounded-b-[4px] bg-[var(--bg-card)] border border-[var(--line)] overflow-hidden p-6 flex flex-col"
                style={{
                  backfaceVisibility: 'hidden',
                  clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), 55% 100%, 50% calc(100% - 6px), 45% 100%, 0 calc(100% - 10px))',
                  boxShadow: isLocateTarget
                    ? '0 0 40px rgba(184,92,56,0.15), 0 16px 48px rgba(107,62,46,.10)'
                    : isCenter ? '0 16px 48px rgba(107,62,46,.08)' : '0 8px 32px rgba(107,62,46,.04)',
                  borderColor: isLocateTarget ? 'rgba(184,92,56,0.3)' : undefined,
                  transition: 'box-shadow 0.6s ease-out, border-color 0.6s ease-out',
                }}
              >
                {/* Bookmark ribbon */}
                <div
                  className="absolute -top-3 left-8 w-8 h-10 flex items-center justify-center text-[9px] font-bold text-white tracking-wider rounded-b-sm"
                  style={{
                    backgroundColor: ZONE_DOT[node.zone] ?? ZONE_DOT[DEFAULT_ZONE],
                    boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
                    clipPath: 'polygon(0 0, 100% 0, 100% 75%, 50% 100%, 0 75%)',
                  }}
                >
                  {ZONE_LABEL[node.zone]?.[0] ?? '?'}
                </div>'''

content = content.replace(old_front, new_front)

# Back card bookmark style
old_back = '''              <div
                className="absolute inset-0 rounded-[20px] bg-[var(--bg-card)] border border-[var(--line)] overflow-y-auto p-6"
                style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)', boxShadow: isCenter ? '0 16px 48px rgba(107,62,46,.14)' : '0 8px 32px rgba(107,62,46,.08)' }}
              >
                <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${ZONE_STRIP[node.zone] ?? ZONE_STRIP[DEFAULT_ZONE]}`} />'''

new_back = '''              <div
                className="absolute inset-0 rounded-t-[20px] rounded-b-[4px] bg-[var(--bg-card)] border border-[var(--line)] overflow-y-auto p-6"
                style={{
                  backfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), 55% 100%, 50% calc(100% - 6px), 45% 100%, 0 calc(100% - 10px))',
                  boxShadow: isCenter ? '0 16px 48px rgba(107,62,46,.08)' : '0 8px 32px rgba(107,62,46,.04)'
                }}
              >
                {/* Bookmark ribbon */}
                <div
                  className="absolute -top-3 left-8 w-8 h-10 flex items-center justify-center text-[9px] font-bold text-white tracking-wider rounded-b-sm"
                  style={{
                    backgroundColor: ZONE_DOT[node.zone] ?? ZONE_DOT[DEFAULT_ZONE],
                    boxShadow: '0 2px 6px rgba(0,0,0,0.12)',
                    clipPath: 'polygon(0 0, 100% 0, 100% 75%, 50% 100%, 0 75%)',
                  }}
                >
                  {ZONE_LABEL[node.zone]?.[0] ?? '?'}
                </div>'''

content = content.replace(old_back, new_back)

with open('src/components/explorer/Coverflow.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
