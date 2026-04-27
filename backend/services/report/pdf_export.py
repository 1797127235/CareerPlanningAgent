import json
import logging
import os

from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


def _render_sync(
    report_id: int,
    token: str,
    user_json: dict,
    frontend_base: str,
) -> bytes:
    """线程内同步 Playwright 渲染。Windows 下 asyncio 子进程不受支持，走 sync API 最稳。"""
    from playwright.sync_api import sync_playwright

    url = f"{frontend_base}/report/print/{report_id}"
    user_str = json.dumps(user_json).replace("'", "\\'")
    init_script = f"""
      localStorage.setItem('token', '{token}');
      localStorage.setItem('user', '{user_str}');
    """

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": 1240, "height": 1754},  # A4 @ 150dpi
            )
            context.add_init_script(init_script)
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)

            # 等打印就绪信号（由 ReportPrintPage 设置）
            page.wait_for_selector(
                '[data-print-ready="true"]',
                timeout=30000,
            )

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            return pdf_bytes
        finally:
            browser.close()


async def render_report_pdf(
    report_id: int,
    token: str,
    user_json: dict,
    frontend_base: str | None = None,
) -> bytes:
    """
    用 Playwright headless 打开报告打印页，渲染成 PDF 字节。

    Windows 的 uvicorn 事件循环不支持 asyncio subprocess，所以用 sync_playwright
    并通过 run_in_threadpool 丢到 Starlette 的工作线程池里跑——线程里自己的
    事件循环归 Playwright 独享，和 FastAPI 主循环互不干扰，跨平台都能跑。

    Args:
        report_id: 报告 ID
        token: 用户的 JWT（从请求 Authorization header 拿）
        user_json: localStorage 里存的 user 对象
        frontend_base: 前端地址，默认读 env FRONTEND_URL 或 http://localhost:5173
    Raises:
        TimeoutError: 渲染超时（默认 30s）
        RuntimeError: 渲染异常
    """
    base = frontend_base or os.getenv("FRONTEND_URL", "http://localhost:5174")
    return await run_in_threadpool(_render_sync, report_id, token, user_json, base)
