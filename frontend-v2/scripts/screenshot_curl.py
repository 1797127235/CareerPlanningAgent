import asyncio
from playwright.async_api import async_playwright

HTML_PATH = "file:///C:/Users/liu/Desktop/CareerPlanningAgent/frontend-v2/scripts/curl_verify.html"
OUTPUT = "artifacts/report-screenshots/07-curl-200.png"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 800, "height": 200})
        await page.goto(HTML_PATH)
        await asyncio.sleep(0.5)
        await page.screenshot(path=OUTPUT)
        print(f"Saved {OUTPUT}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
