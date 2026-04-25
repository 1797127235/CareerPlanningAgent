import asyncio
from playwright.async_api import async_playwright

URL = "http://localhost:5174/profile?mock=1"
OUTPUT_DIR = "artifacts/profile-screenshots"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(1)

        import os
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 1. Full page
        await page.screenshot(path=f"{OUTPUT_DIR}/00-full.png", full_page=True)
        print(f"Saved {OUTPUT_DIR}/00-full.png")

        # 2. Prologue hero
        prologue = page.locator("main section").first
        await prologue.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await prologue.screenshot(path=f"{OUTPUT_DIR}/01-prologue.png")
        print(f"Saved {OUTPUT_DIR}/01-prologue.png")

        # 3. Chapter I
        chapter_i = page.locator("#chapter-1")
        await chapter_i.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await chapter_i.screenshot(path=f"{OUTPUT_DIR}/02-chapter-i.png")
        print(f"Saved {OUTPUT_DIR}/02-chapter-i.png")

        # 4. Chapter II (skills chips)
        chapter_ii = page.locator("#chapter-2")
        await chapter_ii.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await chapter_ii.screenshot(path=f"{OUTPUT_DIR}/03-chapter-ii.png")
        print(f"Saved {OUTPUT_DIR}/03-chapter-ii.png")

        # 5. TOC visible alongside content
        toc = page.locator("nav").first
        await toc.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await page.screenshot(path=f"{OUTPUT_DIR}/04-toc.png")
        print(f"Saved {OUTPUT_DIR}/04-toc.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
