import asyncio
from playwright.async_api import async_playwright

async def screenshot(page, path, url):
    await page.goto(url)
    await page.wait_for_load_state('networkidle')
    await asyncio.sleep(1.5)
    await page.screenshot(path=path, full_page=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        
        # Login
        await page.goto('http://localhost:5175/login')
        await page.wait_for_load_state('networkidle')
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')
        
        await screenshot(page, '../profile-broken.png', 'http://localhost:5175/profile')
        await screenshot(page, '../growth-broken.png', 'http://localhost:5175/growth-log')
        await screenshot(page, '../graph-broken.png', 'http://localhost:5175/graph')
        
        await browser.close()
        print('all screenshots saved')

asyncio.run(main())
