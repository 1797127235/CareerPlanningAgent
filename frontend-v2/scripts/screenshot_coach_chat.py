import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "../artifacts/coach-screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

async def sse_handler(route):
    async def fulfill():
        await route.fulfill(
            status=200,
            headers={"Content-Type": "text/event-stream"},
            body='data: {"content":"你好"}\n\ndata: {"content":"！"}\n\ndata: {"content":"我是你的职业教练"}\n\ndata: {"content":"，有什么可以帮你的吗？"}\n\ndata: [DONE]\n\n',
        )
    asyncio.create_task(fulfill())

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept APIs to avoid 401 redirect
        await page.route("**/api/chat", sse_handler)
        await page.route("**/api/profiles", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body='{"success":true,"data":{"id":1,"name":"test"}}'
        ))
        await page.route("**/api/report/", lambda route: route.fulfill(
            status=200, content_type="application/json", body='[]'
        ))
        await page.route("**/api/growth-log/activity-pulse", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body='{"current_streak_weeks":0,"total_records":0,"weeks":[]}'
        ))
        await page.route("**/api/coach/results", lambda route: route.fulfill(
            status=200, content_type="application/json", body='[]'
        ))

        # mock auth on real origin
        await page.goto("http://localhost:5174/")
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')

        await page.goto("http://localhost:5174/coach/chat?prompt=你好")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3.0)

        path = f"{OUT_DIR}/coach-chat.png"
        await page.screenshot(path=path, full_page=False)
        print(f"saved {path}")

        await browser.close()
        print("screenshot done")

asyncio.run(main())
