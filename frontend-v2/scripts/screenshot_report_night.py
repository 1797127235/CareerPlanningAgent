import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "../artifacts/theme-preview"
os.makedirs(OUT_DIR, exist_ok=True)

async def capture_report(page, url: str, out_path: str):
    # Intercept APIs — same broad interception as coach script
    await page.route("**/api/profiles", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"success":true,"data":{"id":1,"name":"test","profile":{},"career_goals":[],"created_at":"2024-01-01","updated_at":"2024-01-01"}}'
    ))
    await page.route("**/api/report/", lambda route: route.fulfill(status=200, content_type="application/json", body='[]'))
    await page.route("**/api/growth-log/activity-pulse", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"current_streak_weeks":0,"total_records":0,"weeks":[]}'
    ))

    # mock auth on real origin
    await page.goto("http://localhost:5174/")
    await page.evaluate('''() => {
        localStorage.setItem("token", "mock");
        localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
        window.dispatchEvent(new Event("auth-change"));
    }''')

    await page.goto(url)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(0.8)

    # stepwise scroll to trigger any whileInView
    for y in [200, 400, 800, 1200, 1600]:
        await page.evaluate(f"window.scrollTo(0, {y})")
        await asyncio.sleep(0.2)
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.3)

    await page.screenshot(path=out_path, full_page=True)
    print(f"saved {out_path}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 900})

        day_page = await context.new_page()
        await capture_report(day_page, "http://localhost:5174/report?mock=1", f"{OUT_DIR}/report-day.png")

        night_page = await context.new_page()
        await capture_report(night_page, "http://localhost:5174/report?mock=1&theme=night", f"{OUT_DIR}/report-night.png")

        await browser.close()
        print("all screenshots done")

asyncio.run(main())
