# 语音面试模块实现文档

> 审核人：John（PM）、Winston（架构师）、Sally（UX）  
> 日期：2026-04-05  
> 状态：待实现

---

## 一、背景与定位

在现有文字面试（`mock_service.py`）基础上增加语音 I/O 通道。

**核心原则：语音 = 现有文字面试的 I/O 替换，不是重写。**

- `POST /mock/start` — 不变，创建 session
- `WS /ws/mock/{session_id}` — 新增，语音通道
- `POST /mock/finish` — 不变，生成报告
- 语音模式与文字模式共享同一 session，可随时切换

---

## 二、技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| STT | OpenAI Whisper (`whisper-1`) | 项目已有 openai 包，中文支持好，language="zh" |
| TTS | MiniMax T2A v2 HTTP API | 中文语音质量优，直接 HTTP 调用无需额外框架 |
| Transport | FastAPI 原生 WebSocket | 无第三方框架依赖，push-to-talk 场景不需要 Pipecat Pipeline |
| 前端录音 | MediaRecorder API（webm/opus） | 浏览器原生，无需额外依赖 |

> **为什么不用 Pipecat Pipeline：**  
> Pipecat 为实时连续语音设计（VAD 自动检测），我们是 push-to-talk（用户手动控制）。
> 直接写 WebSocket handler 复用现有逻辑，零重构成本。

---

## 三、WebSocket 消息协议

### 前端 → 后端
```json
{ "type": "audio", "data": "<base64 encoded webm>" }   // push-to-talk 音频
{ "type": "ping" }                                       // 心跳保活
```

### 后端 → 前端
```json
{ "type": "transcript", "text": "识别出的文字" }                     // STT 结果，供用户确认
{ "type": "interviewer_text", "content": "...", "done": false }      // 面试官文字（流式多帧）
{ "type": "tts_audio", "data": "<base64 mp3>" }                      // TTS 音频
{ "type": "progress", "current_q": 2, "total_q": 5, "status": "active" }
{ "type": "interview_end" }                                           // 面试结束，前端触发 finish
{ "type": "error", "message": "..." }
```

---

## 四、后端实现

### 4.1 新增 `backend/services/tts_minimax.py`

```python
"""MiniMax T2A v2 TTS service."""
import aiohttp
import base64
import os

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")


async def synthesize_minimax(text: str, voice_id: str = "male-qn-jingying") -> bytes:
    """Call MiniMax T2A v2, return MP3 bytes."""
    if not MINIMAX_API_KEY or not MINIMAX_GROUP_ID:
        raise ValueError("MINIMAX_API_KEY / MINIMAX_GROUP_ID 未配置")

    url = f"https://api.minimax.io/v1/t2a_v2?GroupId={MINIMAX_GROUP_ID}"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "speech-02-turbo",
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "format": "mp3",
            "sample_rate": 32000,
            "bitrate": 128000,
        },
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise ValueError(f"MiniMax TTS 失败: HTTP {resp.status}")
            data = await resp.json()

    if data.get("base_resp", {}).get("status_code", 0) != 0:
        raise ValueError(f"MiniMax TTS 错误: {data['base_resp'].get('status_msg')}")

    audio_b64 = data["data"]["audio"]
    return base64.b64decode(audio_b64)
```

---

### 4.2 新增 `backend/routers/voice.py`

```python
"""Voice interview WebSocket router.

Protocol:
  Client → Server: {type: "audio", data: "<base64 webm>"}
  Server → Client: transcript / interviewer_text / tts_audio / progress / error
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.auth import get_current_user_ws   # 需新增 WebSocket 版鉴权（见 4.3）
from backend.db import get_db
from backend.db_models import User
from backend.routers.mock import _verify_session_owner
from backend.services.mock_service import MockInterviewService, _sessions
from backend.services.tts_minimax import synthesize_minimax

router = APIRouter()
logger = logging.getLogger(__name__)
_mock_svc = MockInterviewService()


async def _stt_whisper(audio_bytes: bytes) -> str:
    """Transcribe audio via OpenAI Whisper."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI()
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.webm", audio_bytes, "audio/webm"),
        language="zh",
    )
    return transcript.text.strip()


@router.websocket("/ws/mock/{session_id}")
async def voice_interview(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    # Auth via token query param: ws://...?token=xxx
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="未授权")
        return

    try:
        from backend.auth import decode_token
        user = decode_token(token, db)
    except Exception:
        await websocket.close(code=4001, reason="Token 无效")
        return

    try:
        _verify_session_owner(session_id, user, db)
    except Exception:
        await websocket.close(code=4003, reason="无权访问此会话")
        return

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg.get("type") == "audio":
                audio_bytes = base64.b64decode(msg["data"])

                # 1. STT
                try:
                    text = await _stt_whisper(audio_bytes)
                except Exception as e:
                    logger.error("STT error: %s", e)
                    await websocket.send_json({"type": "error", "message": "语音识别失败，请重试"})
                    continue

                await websocket.send_json({"type": "transcript", "text": text})

                # 2. Interview logic (reuse existing chat generator)
                interviewer_text = ""
                try:
                    async for chunk in _mock_svc.chat(session_id, text, db):
                        if "content" in chunk:
                            interviewer_text += chunk["content"]
                            await websocket.send_json({
                                "type": "interviewer_text",
                                "content": chunk["content"],
                                "done": False,
                            })
                        if "progress" in chunk:
                            progress = chunk["progress"]
                            await websocket.send_json({"type": "progress", **progress})
                            if progress.get("status") == "finishing":
                                await websocket.send_json({"type": "interview_end"})
                except ValueError as e:
                    await websocket.send_json({"type": "error", "message": str(e)})
                    continue

                await websocket.send_json({
                    "type": "interviewer_text", "content": "", "done": True
                })

                # 3. TTS
                if interviewer_text:
                    # Truncate to 500 chars for TTS (long responses split naturally)
                    tts_text = interviewer_text[:500]
                    try:
                        mp3_bytes = await synthesize_minimax(tts_text)
                        await websocket.send_json({
                            "type": "tts_audio",
                            "data": base64.b64encode(mp3_bytes).decode(),
                        })
                    except Exception as e:
                        logger.warning("TTS error (non-fatal): %s", e)
                        # TTS failure is non-fatal — text already sent

    except WebSocketDisconnect:
        logger.info("Voice WS disconnected: %s", session_id)
    except Exception as e:
        logger.error("Voice WS error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": "服务异常"})
        except Exception:
            pass
```

---

### 4.3 新增 WebSocket 鉴权辅助

在 `backend/auth.py` 补充：

```python
def decode_token(token: str, db: Session) -> User:
    """Decode JWT token and return User. Used for WebSocket auth."""
    # 复用现有 get_current_user 的 token 验证逻辑
    from backend.auth import verify_token  # 根据现有实现调整
    return verify_token(token, db)
```

---

### 4.4 注册路由 `backend/app.py`

```python
from backend.routers import voice
app.include_router(voice.router, prefix="/api", tags=["语音面试"])
```

---

### 4.5 更新 `requirements.txt`

```
aiohttp>=3.9.0    # MiniMax HTTP 调用
```

---

### 4.6 更新 `.env.example`

```
# ── MiniMax 语音合成（语音面试 TTS）──
# 获取地址: https://platform.minimaxi.com/
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_GROUP_ID=your_minimax_group_id
```

---

## 五、前端实现

### 5.1 新增 `frontend/src/hooks/useVoiceInterview.ts`

**状态机：**
```
IDLE → RECORDING → TRANSCRIBING → CONFIRMING → WAITING → PLAYING → IDLE
```

**核心逻辑：**

```typescript
type VoiceState = 'idle' | 'recording' | 'transcribing' | 'confirming' | 'waiting' | 'playing'

interface UseVoiceInterviewOptions {
  sessionId: string
  onInterviewEnd: () => void
}

export function useVoiceInterview({ sessionId, onInterviewEnd }: UseVoiceInterviewOptions) {
  const [state, setState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [interviewerText, setInterviewerText] = useState('')
  const [progress, setProgress] = useState<{ current_q: number; total_q: number } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // WebSocket 连接
  useEffect(() => {
    const token = localStorage.getItem('token')
    const ws = new WebSocket(`ws://localhost:8000/api/ws/mock/${sessionId}?token=${token}`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)

      if (msg.type === 'transcript') {
        setTranscript(msg.text)
        setState('confirming')
      }
      if (msg.type === 'interviewer_text') {
        if (!msg.done) setInterviewerText(prev => prev + msg.content)
        else setState('playing')  // text done, wait for tts_audio or play text
      }
      if (msg.type === 'tts_audio') {
        const mp3Bytes = Uint8Array.from(atob(msg.data), c => c.charCodeAt(0))
        const blob = new Blob([mp3Bytes], { type: 'audio/mpeg' })
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audioRef.current = audio
        setState('playing')
        audio.play()
        audio.onended = () => {
          URL.revokeObjectURL(url)
          setState('idle')
          setInterviewerText('')
          setTranscript('')
        }
      }
      if (msg.type === 'progress') {
        setProgress({ current_q: msg.current_q, total_q: msg.total_q })
      }
      if (msg.type === 'interview_end') {
        onInterviewEnd()
      }
    }

    // Heartbeat
    const heartbeat = setInterval(() => ws.send(JSON.stringify({ type: 'ping' })), 20000)
    return () => { clearInterval(heartbeat); ws.close() }
  }, [sessionId])

  const startRecording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    chunksRef.current = []
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.start()
    mediaRecorderRef.current = recorder
    setState('recording')
  }, [])

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current
    if (!recorder) return
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      // Convert to base64 and send
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(',')[1]
        wsRef.current?.send(JSON.stringify({ type: 'audio', data: base64 }))
        setState('transcribing')
      }
      reader.readAsDataURL(blob)
    }
    recorder.stop()
    recorder.stream.getTracks().forEach(t => t.stop())
  }, [])

  // Confirm transcript and trigger (already triggered on server, just for UX)
  const confirmTranscript = useCallback((editedText: string) => {
    setInterviewerText('')
    setState('waiting')
    // If user edited transcript, re-send as text message
    if (editedText !== transcript) {
      wsRef.current?.send(JSON.stringify({ type: 'text', data: editedText }))
    }
  }, [transcript])

  const cancelRecording = useCallback(() => {
    mediaRecorderRef.current?.stop()
    setState('idle')
  }, [])

  return {
    state, transcript, interviewerText, progress,
    startRecording, stopRecording, confirmTranscript, cancelRecording,
  }
}
```

---

### 5.2 新增 `frontend/src/components/mock/MicButton.tsx`

按钮视觉规范：
- `idle`: 麦克风图标，灰色 `bg-white/60 border`
- `recording`: 红色 `bg-red-500` + 波形动画
- `transcribing`: spinner
- `waiting` / `playing`: disabled，面试官动画
- 持续按住录音，松开自动提交

---

### 5.3 新增 `frontend/src/components/mock/VoicePanel.tsx`

组件树：
```
VoicePanel
  ├── ProgressBar          // 第 X 题 / 共 Y 题
  ├── InterviewerBubble    // 面试官文字（流式显示）
  ├── TranscriptConfirm    // CONFIRMING 状态：显示 STT 结果，可编辑，确认/重录
  └── MicButton            // 核心录音按钮
```

---

### 5.4 更新 `frontend/src/pages/PracticePage.tsx`

顶部增加模式切换 Tab：

```tsx
const [mode, setMode] = useState<'text' | 'voice'>('text')

// Tab UI
<div className="flex gap-2 mb-4">
  <button onClick={() => setMode('text')} className={mode === 'text' ? 'pill-tab active' : 'pill-tab'}>文字模式</button>
  <button onClick={() => setMode('voice')} className={mode === 'voice' ? 'pill-tab active' : 'pill-tab'}>语音模式</button>
</div>

{mode === 'text' && <MockView sessionId={sessionId} />}
{mode === 'voice' && <VoicePanel sessionId={sessionId} onEnd={handleEnd} />}
```

---

## 六、验收标准

1. 用户按住麦克风说话 → 松开 → 识别文字显示（可编辑）
2. 确认后面试官文字流式出现 + 语音播放
3. 进度条更新（第 X 题 / 共 Y 题）
4. 语音/文字模式切换，session 不中断
5. 面试结束（NEXT_ACTION=end）→ 自动调 `/mock/finish` → 跳转报告页
6. STT 失败 → 显示错误提示，回到 IDLE，可重录
7. TTS 失败 → 不阻塞，文字已显示，继续面试

---

## 七、实现顺序建议

```
Step 1: backend/services/tts_minimax.py          （独立，可先单测）
Step 2: backend/routers/voice.py                  （依赖 step1 + 现有 mock_service）
Step 3: 后端注册路由 + .env 配置
Step 4: frontend/src/hooks/useVoiceInterview.ts   （纯逻辑，先写 hook）
Step 5: frontend/src/components/mock/MicButton     （UI 组件）
Step 6: frontend/src/components/mock/VoicePanel    （组合）
Step 7: PracticePage 集成 + 模式切换
Step 8: 端到端测试
```

---

## 八、注意事项

- WebSocket 鉴权通过 query param `?token=xxx` 传递 JWT
- TTS 单次上限 500 字（面试官长回复截断，不影响面试逻辑）
- iOS Safari MediaRecorder 输出 `audio/mp4`，文件名写 `recording.mp4`，Whisper 均支持
- 录音超过 55 秒前端自动停止（Whisper 单次上限 25MB / ~60s）
- TTS 失败为非致命错误，不中断面试
