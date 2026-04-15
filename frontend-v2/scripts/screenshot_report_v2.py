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

        # Chapter I section (second section after Prologue)
        sections = await page.locator("main section").all()
        if len(sections) >= 2:
            chapter_i = sections[1]
            await chapter_i.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await chapter_i.screenshot(path=f"{OUTPUT_DIR}/02-chapter-i.png")
            print(f"Saved {OUTPUT_DIR}/02-chapter-i.png")
        else:
            print("Chapter I not found")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
