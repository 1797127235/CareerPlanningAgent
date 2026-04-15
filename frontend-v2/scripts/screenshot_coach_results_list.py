import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "../artifacts/coach-screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept API to avoid 401
        await page.route("**/api/coach/results", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body='[{"id":101,"result_type":"jd_diagnosis","title":"Bytedance · 后端开发工程师","summary":"匹配度 68%，具备 3 项核心技能，还有 4 项缺口待补齐。","metadata":{"match_score":68},"created_at":"2025-01-10T08:00:00Z"},{"id":102,"result_type":"career_report","title":"前端工程师 · 职业发展报告","summary":"基于你的画像和市场需求，整理出未来 1-3 年的职业路径建议。","metadata":{},"created_at":"2025-01-12T10:30:00Z"},{"id":103,"result_type":"interview_review","title":"蚂蚁集团 · 前端一面复盘","summary":"整体表现中等偏上，技术深度足够，但项目叙述的结构性可以更强。","metadata":{},"created_at":"2025-01-14T14:00:00Z"}]'
        ))

        # mock auth on real origin
        await page.goto("http://localhost:5174/")
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')

        await page.goto("http://localhost:5174/coach/results?mock=1")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(0.8)

        # stepwise scroll to trigger any whileInView
        for y in [200, 400, 800, 1200]:
            await page.evaluate(f"window.scrollTo(0, {y})")
            await asyncio.sleep(0.2)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.3)

        path1 = f"{OUT_DIR}/coach-results-list.png"
        await page.screenshot(path=path1, full_page=True)
        print(f"saved {path1}")

        # hover to reveal trash button
        await page.hover("text=JD 诊断")
        await asyncio.sleep(0.4)

        path2 = f"{OUT_DIR}/coach-results-list-hover.png"
        await page.screenshot(path=path2, full_page=True)
        print(f"saved {path2}")

        await browser.close()
        print("all screenshots done")

asyncio.run(main())
