import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent

async def capture_full_dashboard():
    out_path = ROOT_DIR / "plots" / "phase10_dashboard_mission_control.png"
    
    # Start server via run_phase10_dashboard.py
    server_process = subprocess.Popen(
        [sys.executable, str(ROOT_DIR / "scripts" / "run_phase10_dashboard.py"), "--port", "8005"],
        cwd=str(ROOT_DIR)
    )
    time.sleep(3.5) # allow server to initialize
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # High-res wide viewport (1750 x 860) to show all 3 columns with retina sharpness
            page = await browser.new_page(viewport={"width": 1750, "height": 860}, device_scale_factor=2)
            await page.goto("http://127.0.0.1:8005", wait_until="networkidle")
            await page.wait_for_timeout(1000)

            # Start simulation to generate live telemetry curves and link flows
            btn_play = page.locator("#btn-play-pause")
            if await btn_play.is_visible():
                await btn_play.click()
                await page.wait_for_timeout(5000) # let 5s of telemetry stream into charts

            # Inject a selective drop attack to show active threat response and highlight node
            btn_atk = page.locator("button:has-text('Selective Drop')")
            if await btn_atk.count() > 0:
                await btn_atk.first.click()
                await page.wait_for_timeout(2000)

            await page.screenshot(path=str(out_path))
            print(f"SUCCESS: Captured full 3-column dashboard at {out_path} ({out_path.stat().st_size} bytes)")
            await browser.close()
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    asyncio.run(capture_full_dashboard())
