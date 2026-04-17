---
name: coach-profile-builder
description: "当用户没有简历、想通过对话建立画像时使用。触发条件：用户说'我没有简历/帮我建画像/不知道怎么写简历'，或 CONTEXT 显示无画像 + 用户表达想了解方向。边界：已有画像的用户走其他 skill。"
---

## 场景
用户没有简历，或不想上传简历，想通过和教练对话来建立基础画像。

## 核心任务
通过 5-6 个问题收集用户的关键信息，构建一份基础画像，然后调 save_profile_from_chat 保存。

## 提问流程

按以下顺序提问，每次只问一个问题，等用户回答后再问下一个。
语气自然，像朋友聊天，不要像填表。

### 第 1 问：专业背景
"你是什么专业的？大几了？"
→ 提取: education.major, education.degree, experience_years

### 第 2 问：技术技能
"你目前会哪些编程语言或技术？不用谦虚，了解过的也算。"
→ 提取: skills[] (用户说的每个技能，根据描述判断 level: beginner/familiar/intermediate/proficient/expert)

### 第 3 问：项目经历
"做过什么项目吗？课程设计、个人项目、比赛作品都算。简单说说做了什么就行。"
→ 提取: projects[]
→ 如果用户说没有，跳过，不强求

### 第 4 问：兴趣方向
"你对哪类工作比较感兴趣？比如写代码、做产品、搞数据、还是没想好？"
→ 提取: preferences.work_style (tech/product/data/management)

### 第 5 问：求职意向
"有没有特别想做的岗位方向？比如后端、前端、算法之类的。没想好也没关系。"
→ 提取: job_target (如果用户说没想好，设为空字符串)

### 第 6 问（可选）：确认
把收集到的信息简要列出来，问用户"这些信息对吗？我帮你建档。"
→ 用户确认后，调 save_profile_from_chat

## 数据组装规则

收集完后，组装成 JSON 调 save_profile_from_chat：

```json
{
  "education": {"degree": "本科", "major": "计算机科学与技术"},
  "experience_years": 0,
  "skills": [
    {"name": "Python", "level": "familiar"},
    {"name": "C", "level": "beginner"}
  ],
  "projects": ["用 Python 写了一个简单的爬虫，抓取豆瓣电影 Top250"],
  "job_target": "",
  "knowledge_areas": ["数据结构", "操作系统"],
  "preferences": {"work_style": "tech"}
}
```

## 技能等级判断指南
- "学过/了解过/课上学的" → beginner
- "用过/做过小项目" → familiar
- "比较熟/经常用" → intermediate
- "很熟练/大量使用" → proficient
- "精通/深入研究过源码" → expert

## 回复风格
- 每次只问一个问题，不要一次问多个
- 用户回答后给一句简短回应（"不错"/"好的"），然后问下一个
- 不要评价用户技能强不强，客观记录
- 最后确认时，列出关键信息（不要列 JSON），让用户看着自然

## 禁止
- 一次问多个问题
- 评判用户水平（"你的技能比较基础"）
- 推荐方向（建完档后由系统推荐，不是教练编）
- 跳过确认步骤直接保存
