import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        
        await page.route('**/api/profiles', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body='{"success":true,"data":{"id":1,"name":"林小北","profile":{"education":{"school":"杭州电子科技大学","major":"计算机","degree":"本科"},"experience_years":1,"internships":[{"company":"蚂蚁","role":"前端","duration":"2024.07-2024.09"}],"projects":[{"name":"校园二手平台","description":"小程序"}],"skills":[{"name":"React","level":"proficient"},{"name":"Node.js","level":"familiar"}],"knowledge_areas":["Web开发"],"soft_skills":{"_version":2,"communication":"良好"}},"career_goals":[{"target_label":"前端工程师"}],"created_at":"2024-09-01T10:00:00Z","updated_at":"2025-01-15T08:30:00Z"}}'
        ))
        await page.route('**/api/report/', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body='[{"id":1,"report_key":"v2","title":"报告","summary":"","created_at":"2025-01-10T08:00:00Z"}]'
        ))
        await page.route('**/api/growth-log/activity-pulse', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body='{"current_streak_weeks":2,"total_records":7,"weeks":[]}'
        ))
        
        await page.goto('http://localhost:5175/')
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')
        await page.reload()
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(1.5)
        
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(0.8)
        await page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)
        
        await page.screenshot(path='../homepage-preview.png', full_page=True)
        await browser.close()
        print('screenshot saved')

asyncio.run(main())
