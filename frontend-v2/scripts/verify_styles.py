import asyncio
from playwright.async_api import async_playwright

URL_DEMO = "http://localhost:5174/__demo"
URL_REPORT = "http://localhost:5174/report?mock=1"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        # 1. Check body::before on /__demo
        await page.goto(URL_DEMO, wait_until="networkidle")
        await asyncio.sleep(0.5)
        has_before = await page.evaluate("""
            () => {
              const styles = getComputedStyle(document.body, '::before');
              return styles.content !== 'none' && styles.content !== '';
            }
        """)
        print(f"body::before exists: {has_before}")

        # Check PaperCard shadow on /__demo (if any card uses --shadow-paper)
        shadow_el = page.locator('[class*="shadow-"]').first
        has_shadow = await shadow_el.count() > 0
        print(f"PaperCard/shadow elements found: {has_shadow}")

        # 2. Check report page loads with noise overlay
        await page.goto(URL_REPORT, wait_until="networkidle")
        await asyncio.sleep(0.5)
        has_before_report = await page.evaluate("""
            () => {
              const styles = getComputedStyle(document.body, '::before');
              return styles.content !== 'none' && styles.content !== '';
            }
        """)
        print(f"report body::before exists: {has_before_report}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
