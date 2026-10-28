import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent

async def take_shot():
    out_path = ROOT_DIR / "plots" / "phase10_dashboard_mission_control.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 920}, device_scale_factor=2)
        await page.goto("http://127.0.0.1:8001", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click play to let simulation run and populate live telemetry
        btn = page.locator("#btn-play-pause")
        if await btn.is_visible():
            await btn.click()
            await page.wait_for_timeout(4000)

        await page.screenshot(path=str(out_path))
        print(f"SUCCESS: Captured dashboard screenshot at {out_path} ({out_path.stat().st_size} bytes)")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_shot())
