import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "../artifacts/coach-screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Intercept APIs to avoid 401 redirect
        await page.route("**/api/profiles", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body='{"success":true,"data":{"id":1,"name":"test","profile":{},"quality":{},"graph_position":{"from_node_id":"fe-junior","from_node_label":"前端开发实习生","target_node_id":"fe-senior","target_label":"高级前端工程师","target_zone":"leverage","gap_skills":["Performance","Architecture"],"total_hours":1200,"safety_gain":0.35,"salary_p50":32000}}}'
        ))
        await page.route("**/api/graph/map", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body='{"nodes":[{"node_id":"fe-junior","label":"前端开发实习生","role_family":"前端","zone":"safe","replacement_pressure":0.2,"human_ai_leverage":0.3,"salary_p50":8000,"career_level":1,"must_skills":["HTML","CSS","JavaScript"]},{"node_id":"fe-mid","label":"前端开发工程师","role_family":"前端","zone":"safe","replacement_pressure":0.3,"human_ai_leverage":0.4,"salary_p50":18000,"career_level":2,"must_skills":["React","TypeScript","Webpack"]},{"node_id":"fe-senior","label":"高级前端工程师","role_family":"前端","zone":"leverage","replacement_pressure":0.4,"human_ai_leverage":0.7,"salary_p50":32000,"career_level":3,"must_skills":["Performance","Architecture","Leadership"]},{"node_id":"fe-staff","label":"前端架构师","role_family":"前端","zone":"leverage","replacement_pressure":0.5,"human_ai_leverage":0.8,"salary_p50":50000,"career_level":4,"must_skills":["System Design","Cross-team","Strategy"]},{"node_id":"be-junior","label":"后端开发实习生","role_family":"后端","zone":"transition","replacement_pressure":0.4,"human_ai_leverage":0.3,"salary_p50":8500,"career_level":1,"must_skills":["Java","SQL","Spring"]},{"node_id":"be-mid","label":"后端开发工程师","role_family":"后端","zone":"transition","replacement_pressure":0.5,"human_ai_leverage":0.4,"salary_p50":19000,"career_level":2,"must_skills":["Redis","Kafka","Microservices"]},{"node_id":"pm-junior","label":"产品助理","role_family":"产品","zone":"danger","replacement_pressure":0.7,"human_ai_leverage":0.2,"salary_p50":7000,"career_level":1,"must_skills":["Axure","Communication","Documentation"]},{"node_id":"pm-mid","label":"产品经理","role_family":"产品","zone":"danger","replacement_pressure":0.8,"human_ai_leverage":0.3,"salary_p50":16000,"career_level":2,"must_skills":["Data Analysis","User Research","Roadmap"]}],"edges":[],"node_count":8,"edge_count":0}'
        ))

        # mock auth on real origin
        await page.goto("http://localhost:5174/")
        await page.evaluate('''() => {
            localStorage.setItem("token", "mock");
            localStorage.setItem("user", JSON.stringify({"id":1,"username":"test"}));
            window.dispatchEvent(new Event("auth-change"));
        }''')

        await page.goto("http://localhost:5174/graph?mock=1")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1.0)

        # stepwise scroll to trigger whileInView for chapters
        for y in [300, 700, 1200, 1800, 2400]:
            await page.evaluate(f"window.scrollTo(0, {y})")
            await asyncio.sleep(0.3)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.4)

        path = f"{OUT_DIR}/graph-page.png"
        await page.screenshot(path=path, full_page=True)
        print(f"saved {path}")

        await browser.close()
        print("screenshot done")

asyncio.run(main())
