import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:5174/report?mock=1"
OUTPUT_DIR = "artifacts/report-screenshots"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(URL, wait_until="networkidle")
        # Wait for initial animations
        await asyncio.sleep(1)

        import os
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Full page
        await page.screenshot(path=f"{OUTPUT_DIR}/00-full.png", full_page=True)
        print(f"Saved {OUTPUT_DIR}/00-full.png")

        # Screenshot each section (Prologue + 4 Chapters + Epilogue = 6 sections)
        sections = await page.locator("main section").all()
        for i, section in enumerate(sections, start=1):
            await section.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await section.screenshot(path=f"{OUTPUT_DIR}/{i:02d}-section.png")
            print(f"Saved {OUTPUT_DIR}/{i:02d}-section.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
