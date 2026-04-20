import json

def el(id, type, x, y, w, h, stroke, bg, sw=1, ss="solid", r=None, extra=None):
    e = {
        "id": id, "type": type, "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": ss,
        "roughness": 0, "opacity": 100, "groupIds": [],
        "roundness": r, "seed": abs(hash(id)) % 9999, "version": 1,
        "versionNonce": 1, "isDeleted": False, "boundElements": None,
        "updated": 1, "link": None, "locked": False
    }
    if extra:
        e.update(extra)
    return e

def rect(id, x, y, w, h, stroke, bg, sw=1, ss="solid", radius=8):
    return el(id, "rectangle", x, y, w, h, stroke, bg, sw, ss, {"type": 3, "value": radius})

def text(id, x, y, w, h, content, color="#0F1E3D", size=14, align="center"):
    return el(id, "text", x, y, w, h, color, "transparent", extra={
        "text": content, "fontSize": size, "fontFamily": 1,
        "textAlign": align, "verticalAlign": "top", "baseline": size + 2
    })

def ellipse(id, x, y, w, h, stroke, bg):
    return el(id, "ellipse", x, y, w, h, stroke, bg, r={"type": 2})

def arrow(id, x, y, pts, stroke="#0F1E3D", sw=2, ss="solid"):
    return {
        "id": id, "type": "arrow", "x": x, "y": y,
        "width": abs(pts[-1][0]), "height": abs(pts[-1][1]),
        "angle": 0, "strokeColor": stroke, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": ss,
        "roughness": 0, "opacity": 100, "groupIds": [],
        "roundness": {"type": 2}, "seed": abs(hash(id)) % 9999, "version": 1,
        "versionNonce": 1, "isDeleted": False, "boundElements": None,
        "updated": 1, "link": None, "locked": False,
        "startBinding": None, "endBinding": None,
        "lastCommittedPoint": None, "startArrowhead": None,
        "endArrowhead": "arrow", "points": [[0, 0]] + pts
    }

elements = []

# ── 左侧区域 ──────────────────────────────────────────────
elements.append(rect("bg-left", 50, 100, 280, 500, "#0F1E3D", "#EFF6FF", sw=2, radius=12))
elements.append(text("t-left", 80, 118, 220, 28, "数据与智能基座", size=18))

dbs = [("百万级招聘语料", 175), ("AEI 公开数据集", 260), ("向量检索索引", 345)]
for i, (label, y) in enumerate(dbs):
    elements.append(rect(f"db{i}", 90, y, 200, 55, "#1E3A8A", "#DBEAFE"))
    elements.append(text(f"db{i}-t", 100, y + 18, 180, 24, label))

# ── 右上区域 ──────────────────────────────────────────────
elements.append(rect("bg-tr", 400, 100, 900, 230, "#0F1E3D", "#F0FFF4", sw=2, radius=12))
elements.append(text("t-tr", 420, 118, 860, 28, "用户交互层 · 七大功能模块", size=18))

funcs = [
    ("能力画像", "#DBEAFE", "#1E3A8A", "#0F1E3D"),
    ("JD 诊断",  "#DBEAFE", "#1E3A8A", "#0F1E3D"),
    ("知识图谱", "#DBEAFE", "#1E3A8A", "#0F1E3D"),
    ("发展报告", "#DBEAFE", "#1E3A8A", "#0F1E3D"),
    ("成长档案", "#DBEAFE", "#1E3A8A", "#0F1E3D"),
    ("模拟面试", "#DBEAFE", "#1E3A8A", "#0F1E3D"),
    ("AI 教练",  "#FF6B3D", "#FF6B3D", "#ffffff"),
]
for i, (label, bg, stroke, tc) in enumerate(funcs):
    x = 420 + i * 120
    sw = 2 if i == 6 else 1
    elements.append(rect(f"f{i}", x, 165, 110, 130, stroke, bg, sw=sw))
    elements.append(text(f"f{i}-t", x + 5, 222, 100, 24, label, color=tc))

# ── 右下区域 ──────────────────────────────────────────────
elements.append(rect("bg-br", 400, 370, 900, 380, "#0F1E3D", "#F5F3FF", sw=2, radius=12))
elements.append(text("t-br", 420, 388, 860, 28, "核心流程层 · 五步闭环", size=18))

steps = [
    ("1. 画像构建", "#86EFAC", 450, 450),
    ("2. 人岗匹配", "#86EFAC", 620, 500),
    ("3. 报告生成", "#FDE68A", 790, 550),
    ("4. 成长档案", "#FCA5A5", 960, 600),
    ("5. 模拟面试", "#FB923C", 1130, 650),
]
for i, (label, bg, x, y) in enumerate(steps):
    elements.append(ellipse(f"s{i}", x, y, 140, 65, "#1E3A8A", bg))
    elements.append(text(f"s{i}-t", x + 10, y + 20, 120, 24, label, size=13))

# 步骤间实线箭头
for i in range(4):
    _, _, x1, y1 = steps[i]
    _, _, x2, y2 = steps[i + 1]
    sx, sy = x1 + 140, y1 + 32
    elements.append(arrow(f"arr{i}", sx, sy, [[x2 - sx, y2 + 32 - sy]]))

# 闭环虚线箭头 step5 -> step1
_, _, x5, y5 = steps[4]
_, _, x1, y1 = steps[0]
elements.append(arrow("arr-loop", x5 + 70, y5 + 65,
                       [[x1 + 70 - (x5 + 70), y1 - (y5 + 65)]],
                       stroke="#FF6B3D", ss="dashed"))
elements.append(text("feedback-lbl", 1290, 660, 120, 24, "能力评估反馈",
                     color="#FF6B3D", size=12, align="left"))

# ── 连接线 ────────────────────────────────────────────────
# 左侧 -> 右上（从左侧区域右边中点到右上区域左边中点）
elements.append(arrow("conn-lr", 330, 230, [[70, 0]], stroke="#1E3A8A", sw=1, ss="dashed"))

# 右上功能模块 -> 右下流程节点
func_to_step = [0, 1, 2, 2, 3, 4, 4]
for fi, si in enumerate(func_to_step):
    fx = 420 + fi * 120 + 55
    fy = 295
    sx, sy = steps[si][2] + 70, steps[si][3]
    elements.append(arrow(f"conn-f{fi}", fx, fy, [[sx - fx, sy - fy]],
                          stroke="#1E3A8A", sw=1, ss="dashed"))

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}
}

out = r"C:\Users\liu\Desktop\CareerPlanningAgent\system-architecture.excalidraw.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
print(f"Written {len(elements)} elements to {out}")
