# Growth Coach (成长教练) Design Spec

## Core Concept
成长教练是系统的唯一交互入口。不是被动Q&A，而是主动引导用户完成职业规划全流程。

## User Journey (10 layers)

| Layer | Core Question | Coach Behavior |
|-------|--------------|----------------|
| 0. Emotional Support | 焦虑/迷茫/受挫 | 共情倾听 → 正常化 → 锚定已有能力 → 引导 |
| 1. Self-awareness | 我擅长什么/喜欢什么 | 画像分析 + 兴趣价值观引导 |
| 2. Path Exploration | 有什么路/每条路什么样 | 主动讲解方向、前景、日常、AI影响 |
| 3. Fork Decisions | 考研vs就业/转行vs留 | 引导梳理利弊，不替用户选 |
| 4. Goal Lock-in | 我选这条路 | 确认目标 + 匹配度分析 |
| 5. Gap Planning | 差什么/怎么补/多久 | 带时间线的行动计划 |
| 6. Job Execution | 简历/投递/渠道/跟进 | 简历优化、投递策略、渠道建议 |
| 7. Skill Validation | 我准备好了吗 | 面试练习(语音) + 复盘 |
| 8. Offer Decision | 多个offer怎么选 | 多维对比(薪资/成长/城市) |
| 9. Follow-up | 入职后/长期发展 | 定期重评估 |

## Conversation Phase (implicit state machine)
```
idle → emotional → exploring → deciding → planning → executing
        ^__________________________________|
        (any phase can drop back to emotional)
```

Tracked in CareerState.conversation_phase, determined by triage LLM each turn.

## Key Design Decisions

### Emotional Layer (two types)
- Entry anxiety ("什么都不会") → empathize → anchor existing skills → guide to explore
- Execution frustration ("投了50封没回音") → empathize → normalize failure rate → diagnose blockers → adjust strategy

### No Explicit Mode Switching
Coach naturally transitions between coaching/interviewing/teaching/reviewing based on conversation context. No UI mode buttons.

### Decision Convergence (critical)
Every decision-related conversation must end with:
1. Summary of current leaning
2. Concrete next step
3. Check-in point

### Adaptive Style (via prompt, not classifier)
- Emotion-driven users → empathize first, then analyze
- Externally-driven users → separate their own wants from external pressure
- Rational users → structured data comparison

### Coach Memo (natural language, not structured JSON)
After meaningful conversations, LLM generates a memo summarizing user insights.
Injected into next session's triage context. More flexible than structured personality fields.

### Proactive Triggers (P0)
- Panel open (no chat) → stage-aware greeting ✅ done
- Profile updated → suggest direction exploration
- Goal set → suggest JD diagnosis or gap analysis
- JD diagnosed → offer to explain gaps or start practice
- 3+ days idle → re-engagement on next visit

## MVP Scope
- P0: Emotional awareness in triage, path exploration/teaching, fork decision guidance
- P1: Timeline-based action plans, interview practice (voice), job execution advice
- P2: Offer comparison, real-time market data, periodic reassessment

## Technical Implementation
- CareerState: add `conversation_phase`, `coach_memo`
- Triage prompt: complete rewrite as growth coach
- Coach memo: stored in Profile.coach_memo, loaded in _hydrate_state
- No new agents needed — triage prompt enhancement + existing 6 agents
