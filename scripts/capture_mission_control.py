import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 1750x860 viewport
        page = await browser.new_page(viewport={"width": 1750, "height": 860}, device_scale_factor=2)
        print("Navigating to http://127.0.0.1:8015...")
        await page.goto("http://127.0.0.1:8015", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Click play to let simulation run and populate live telemetry
        btn = page.locator("#btn-play-pause")
        if await btn.is_visible():
            await btn.click()
            await page.wait_for_timeout(3500)

        # 1. Save PNG
        png_path = ROOT_DIR / "plots" / "dashboard_mission_control.png"
        await page.screenshot(path=str(png_path))
        print(f"SUCCESS: Saved PNG to {png_path} ({png_path.stat().st_size} bytes)")

        # Also overwrite the old path so existing references work
        old_png = ROOT_DIR / "plots" / "phase10_dashboard_mission_control.png"
        await page.screenshot(path=str(old_png))
        print(f"SUCCESS: Also updated {old_png}")

        # 2. Save PDF with real vector selectable text
        pdf_path = ROOT_DIR / "plots" / "dashboard_mission_control.pdf"
        await page.pdf(
            path=str(pdf_path),
            width="1750px",
            height="860px",
            print_background=True,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
        )
        print(f"SUCCESS: Saved PDF with selectable text to {pdf_path} ({pdf_path.stat().st_size} bytes)")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
