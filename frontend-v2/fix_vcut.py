with open('src/components/explorer/Coverflow.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Increase card size
content = content.replace('w-[380px] h-[460px]', 'w-[380px] h-[500px]')

# Reduce V-cut depth on front and back cards
old_cut = "clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 10px), 55% 100%, 50% calc(100% - 6px), 45% 100%, 0 calc(100% - 10px))'"
new_cut = "clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 6px), 55% calc(100% - 2px), 50% 100%, 45% calc(100% - 2px), 0 calc(100% - 6px))'"
content = content.replace(old_cut, new_cut)

with open('src/components/explorer/Coverflow.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
