import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "../artifacts/coach-screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

async def screenshot_variant(page, variant: str, url: str):
    await page.goto(url)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(1.0)
    # scroll to trigger whileInView animations, then back to top
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(0.6)
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.4)
    path = f"{OUT_DIR}/coach-result-{variant}.png"
    await page.screenshot(path=path, full_page=True)
    print(f"saved {path}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept APIs to avoid 401
        await page.route("**/api/coach/results/**", lambda route: route.fulfill(
            status=200, content_type="application/json", body="{}"
        ))

        # mock auth on real origin
        await page.goto("http://localhost:5174/")
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')

        await screenshot_variant(page, "jd", "http://localhost:5174/coach/result/999?mock=1&type=jd")
        await screenshot_variant(page, "narrative", "http://localhost:5174/coach/result/999?mock=1&type=narrative")
        await screenshot_variant(page, "review", "http://localhost:5174/coach/result/999?mock=1&type=review")

        await browser.close()
        print("all screenshots done")

asyncio.run(main())
