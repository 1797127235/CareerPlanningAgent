# 文档索引

最后更新：2026-04-15

## 活跃文档（active）

| 文件 | 说明 |
|---|---|
| [PROJECT_GUIDE.md](./PROJECT_GUIDE.md) | 项目指南（新人入口） |
| [upload-ceremony-ux-spec.md](./upload-ceremony-ux-spec.md) | 上传仪式感 UX 增强规范（杂志排版室方向，待实施） |
| [coach-skill-progressive-disclosure.md](./coach-skill-progressive-disclosure.md) | Coach 当前架构：Progressive Disclosure 模式 + 13 skill |
| [backend-slimdown-phase1-profile-service.md](./backend-slimdown-phase1-profile-service.md) | Backend 瘦身 Phase 1：profile_service.py 拆分（Kimi 进行中） |

## 子目录

| 目录 | 说明 |
|---|---|
| `stories/` | 用户故事 / 史诗规划 |
| `superpowers/` | superpowers skill 定义 |
| `archive/` | **历史文档归档**，保留查阅但不再维护 |

## archive/ 归档说明

`archive/` 里的文档**与当前架构可能不一致**。它们代表项目过去的决策，保留作为：
- 设计演化轨迹参考
- 回溯原因："为什么当时这么做"
- 历史 session-handoff 备份

**规则**：
- 活跃文档必须留在 `docs/` 根目录
- 一旦某份活跃文档被新版取代或功能已落地到代码，立即移入 `archive/`
- `archive/` 内文档**不接受修改**（只读）

## 命名规范

- 活跃架构文档：`领域-动作[-阶段].md`
  - `coach-skill-progressive-disclosure.md`
  - `backend-slimdown-phase1-profile-service.md`
- 历史 session 记录：`YYYY-MM-DD-session-handoff[-N].md`（归档后）
- Spec 类文档：`XXX-spec.md` / `XXX-migration.md`（通常迭代完就归档）
