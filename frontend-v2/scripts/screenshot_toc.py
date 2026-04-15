import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:5174/report?mock=1"
OUTPUT_DIR = "artifacts/report-screenshots"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(1)

        import os
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Full page
        await page.screenshot(path=f"{OUTPUT_DIR}/00-full.png", full_page=True)
        print(f"Saved {OUTPUT_DIR}/00-full.png")

        # Viewport shot with TOC visible (scroll to top)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        await page.screenshot(path=f"{OUTPUT_DIR}/08-toc-viewport.png")
        print(f"Saved {OUTPUT_DIR}/08-toc-viewport.png")

        # Scroll to chapter 3 to show active state change
        await page.locator("#chapter-3").scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await page.screenshot(path=f"{OUTPUT_DIR}/09-toc-chapter3.png")
        print(f"Saved {OUTPUT_DIR}/09-toc-chapter3.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
