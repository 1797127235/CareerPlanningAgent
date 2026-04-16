# Spec：报告生成状态跨导航恢复

## 问题

`frontend/src/pages/ReportPage.tsx:101` 的 `generating` 是组件 local state。用户点「开始写」→ 后端同步生成（30-60s）→ 中途切去别的路由 → `ReportPage` 卸载 → 回来时 `generating=false`，看不到"正在生成"界面。

后端没有 in-flight 状态的接口，前端也没办法恢复。

## 目标

**后端单一真相源 + 前端 mount 时恢复**：
- 后端在 `/report/generate` 进入时标记该 user 正在生成，finally 清除
- 新增 `GET /report/status` 返回 `{ generating: bool }`
- 前端 mount 时查询 status；若 true → 进入生成中 UI + 每 3 秒轮询，翻转为 false 时拉最新报告

## 非目标（不要做）

- ❌ 不要把生成改成异步/后台任务 —— 当前同步请求已经能工作，改动面太大
- ❌ 不要上 Redis / 数据库标记 —— 当前单进程 uvicorn 够用，in-memory set 即可
- ❌ 不要用 localStorage / sessionStorage 作为主要依据 —— 客户端标志不可靠
- ❌ 不要动 generate pipeline 本身，不要改 LLM 超时、并行度等
- ❌ 不要重写 ReportPage 的加载/错误/空态渲染结构

---

## 改动 1：后端 `backend/routers/report.py`

### 1.1 加模块级状态

在文件顶部 `router = APIRouter()` **之后**、`# ── Schemas` **之前**插入：

```python
import threading

# In-memory tracker of user_ids with an in-flight /generate request.
# Single-process uvicorn only; if we go multi-worker later, swap for Redis.
_generating_users: set[int] = set()
_generating_lock = threading.Lock()
```

### 1.2 修改 `generate_report` 端点

当前 `generate_report`（第 92-151 行）把整个 body 包进 try/except。要在最外层加 `_generating_users` 的 add/discard，**必须用 try/finally 包住整个函数体，保证任何异常/客户端断连都能清除标记**。

把函数签名后的第一行改成：

```python
@router.post("/generate")
def generate_report(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and persist a new career development report for the current user."""
    from backend.services.report import generate_report as _generate

    with _generating_lock:
        _generating_users.add(user.id)

    try:
        # ── 原有的 try / except / db 写入逻辑整段保持不变 ──
        try:
            data = _generate(user_id=user.id, db=db)
        except ValueError as e:
            msg = str(e)
            if "no_profile" in msg:
                raise HTTPException(400, "请先上传简历完成能力画像")
            if "no_goal" in msg:
                raise HTTPException(400, "请先在岗位图谱中设定职业目标")
            print(f"[report/generate] ValueError for user {user.id}: {msg}")
            traceback.print_exc()
            raise HTTPException(400, f"报告生成失败：{msg}")
        except Exception as e:
            print(f"[report/generate] Exception for user {user.id}: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise HTTPException(500, f"报告生成异常：{e}")

        target_label = data.get("target", {}).get("label", "职业发展报告")
        match_score = data.get("match_score", 0)
        narrative = data.get("narrative", "")
        summary_text = narrative[:80] + "…" if len(narrative) > 80 else narrative

        report_key_str = str(uuid.uuid4())

        report = Report(
            report_key=report_key_str,
            user_id=user.id,
            title=f"{target_label} — 职业发展报告",
            summary=summary_text,
            data_json=json.dumps(data, ensure_ascii=False),
        )
        db.add(report)

        # Write staged action plan to ActionPlanV2
        action_plan = data.get("action_plan", {})
        profile_id = data.get("student", {}).get("profile_id")
        if profile_id:
            for stage_data in action_plan.get("stages", []):
                plan_row = ActionPlanV2(
                    profile_id=profile_id,
                    report_key=report_key_str,
                    stage=stage_data["stage"],
                    status="ready",
                    content=stage_data,
                    time_budget={"duration": stage_data["duration"]},
                    generated_at=datetime.now(timezone.utc),
                )
                db.add(plan_row)

        db.commit()
        db.refresh(report)

        return _to_detail(report)
    finally:
        with _generating_lock:
            _generating_users.discard(user.id)
```

⚠️ **注意**：原有逻辑一个字不改，只是把整段包进外层 `try ... finally`。`HTTPException` 也会走 finally，不会漏清除。

### 1.3 新增 `/report/status` 端点

把它放在 `@router.post("/generate")` 函数**之后**、`@router.get("/")` 之前：

```python
@router.get("/status")
def report_generation_status(
    user: User = Depends(get_current_user),
):
    """Is there an in-flight /generate for this user?

    Used by the frontend to recover the 'generating' UI after a page navigation.
    In-memory only; restarts clear it.
    """
    with _generating_lock:
        is_generating = user.id in _generating_users
    return {"generating": is_generating}
```

⚠️ **路由顺序**：FastAPI 按声明顺序匹配，`/status` 必须放在 `/{report_id}` 之前（原文件里 `/{report_id}` 在第 170 行）。把 `/status` 放在 `/generate` 和 `/`（list_reports）之间就能保证顺序正确。

### 1.4 验证后端

```bash
# 启动后端
python -m uvicorn backend.app:app --reload

# 另起终端，用 curl 或 httpie 测
# 1) 无登录：401
curl http://localhost:8000/report/status

# 2) 带 token，非生成中：{"generating": false}
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/report/status
```

---

## 改动 2：前端 API `frontend/src/api/report.ts`

在文件末尾追加：

```ts
export async function fetchReportStatus(): Promise<{ generating: boolean }> {
  return rawFetch<{ generating: boolean }>('/report/status')
}
```

不要动其它导出。

---

## 改动 3：前端 `frontend/src/pages/ReportPage.tsx`

### 3.1 import 加 `fetchReportStatus`

第 15-24 行的 import block，加一行：

```ts
import {
  generateReportV2,
  fetchReportList,
  fetchReportDetail,
  fetchReportStatus,     // ← 新增
  editReport,
  deleteReport,
  exportReportPdf,
  type ReportV2Data,
  type ReportListItem,
} from '@/api/report'
```

### 3.2 加一个轮询 ref

在 `pendingDeleteRef` 声明（第 111-115 行）**下面**加：

```ts
const pollIntervalRef = useRef<number | null>(null)

const stopPoll = () => {
  if (pollIntervalRef.current != null) {
    window.clearInterval(pollIntervalRef.current)
    pollIntervalRef.current = null
  }
}
```

### 3.3 加 `startStatusPoll` 函数

放在 `generate` 函数（第 157-179 行）**之前**：

```ts
// Poll backend /report/status until it reports generating=false, then
// refetch list + detail so the new report appears. Used on mount to recover
// from the case where the user navigated away mid-generation.
const startStatusPoll = () => {
  if (pollIntervalRef.current != null) return  // 已经在轮询，别重复启
  pollIntervalRef.current = window.setInterval(async () => {
    try {
      const { generating: stillGenerating } = await fetchReportStatus()
      if (!stillGenerating) {
        stopPoll()
        setGenerating(false)
        // 拉最新：列表 + 最新一份 detail
        try {
          const list = await fetchReportList()
          setReportList(list)
          if (list[0]) {
            setCurrentId(list[0].id)
            const detail = await fetchReportDetail(list[0].id)
            const rd = detail.data as unknown as ReportV2Data
            if (rd && rd.target) setData(rd)
          }
        } catch {
          /* non-fatal：下一次 mount 会重试 */
        }
      }
    } catch {
      /* 网络抖动：忽略本次 tick，下一次继续 */
    }
  }, 3000)
}
```

### 3.4 修改 mount effect（第 305-308 行）

原来是：

```ts
useEffect(() => {
  loadInitial()
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])
```

改成：

```ts
useEffect(() => {
  loadInitial()
  // 恢复"生成中"UI：若后端说有 in-flight 生成，立即进入 loading + 开始轮询
  fetchReportStatus()
    .then(({ generating: isGen }) => {
      if (isGen) {
        setGenerating(true)
        startStatusPoll()
      }
    })
    .catch(() => {
      /* 失败就当没在生成，用户可以手动再点一次 */
    })
  return () => {
    stopPoll()
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])
```

### 3.5 不要动 `generate` 函数

原有 `generate()`（第 157-179 行）里的 `setGenerating(true) → await generateReportV2() → setGenerating(false)` 流程**保持不变**。它在"用户留在页面"场景下已经工作得很好。只有"用户切走再回来"场景才依赖新的轮询路径。

### 3.6 不要动 UI 渲染

第 321 行的 `if (generating && !data) return <GeneratingScreen />` 保持不变。新逻辑只是把 `generating` 正确地置为 `true`，已有渲染分支会自然生效。

---

## 验收标准

1. **首次生成**：点「开始写」→ 走旧逻辑，正常出 GeneratingScreen → 完成后正常展示新报告。无退化。

2. **切走再回来（核心场景）**：
   - 在报告页点「开始写」→ 看到 GeneratingScreen
   - 立刻跳去 `/graph` 或 `/growth-log`
   - 等 10-20 秒后跳回 `/report`
   - **期望**：直接落在 GeneratingScreen，不是"这一份还没生成过"或旧报告
   - 等后端完成 → 前端 3s 内自动切到新报告

3. **完成后回来**：
   - 生成开始 → 切走 → 等 >60s 让后端跑完 → 跳回
   - **期望**：不显示 loading，直接看到新报告（`loadInitial` 拉的就是最新那份）

4. **打开多个 tab**：
   - tab A 点生成 → tab B 打开 `/report`
   - **期望**：tab B 也进入 GeneratingScreen 并在完成时刷新

5. **失败场景**：
   - `/report/status` 返回 500 / 网络断：不阻塞 `loadInitial`，用户仍能看到旧数据，不报红
   - 后端异常退出（`ctrl+c`）：`_generating_users` 清空；下次查询返回 `{generating: false}`，不会永久卡住 UI

6. **路由顺序**：`GET /report/status` 和 `GET /report/123` 都能正常路由，status 不会被 `/{report_id}` 吞掉（整数 123 不会匹配字面量 `status`，但 FastAPI 路由匹配依赖声明顺序，仍然要把 `/status` 放在 `/{report_id}` 之前保险）。

---

## 关键提示

- **千万别动 `backend/services/report/pipeline.py`** —— 只改 router。
- **千万别把 `threading.Lock` 换成 `asyncio.Lock`** —— `generate_report` 是 sync 端点。
- **别给 `_generating_users` 加 TTL / 清理线程** —— finally 已经保证释放。
- **别在前端用 `setTimeout` 代替 `setInterval`** —— 轮询需要持续周期触发。
- **别把轮询频率调到 1s** —— 3s 够了，1s 会无谓增加后端压力。
- **别加 sessionStorage 兜底** —— 后端是真相源，加了只会引入两条冲突的判断路径。

完成后 `git status` 应该只有这三个文件被修改：
```
M backend/routers/report.py
M frontend/src/api/report.ts
M frontend/src/pages/ReportPage.tsx
```
