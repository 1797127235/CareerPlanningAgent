import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        
        await page.goto('http://localhost:4173/login')
        await page.wait_for_load_state('networkidle')
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')
        
        for path, name in [('/profile', 'profile'), ('/growth-log', 'growth'), ('/graph', 'graph')]:
            await page.goto(f'http://localhost:4173{path}')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1.5)
            await page.screenshot(path=f'../{name}-screenshot.png', full_page=True)
            print(f'{name} done')
        
        await browser.close()

asyncio.run(main())
