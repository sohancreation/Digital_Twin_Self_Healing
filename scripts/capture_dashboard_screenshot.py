import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

from playwright.async_api import async_playwright

async def capture():
    # Start server as subprocess
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.dashboard.app:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3.0)

    out_path = ROOT_DIR / "plots" / "phase10_dashboard_mission_control.png"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
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
    finally:
        proc.terminate()
        proc.kill()

if __name__ == "__main__":
    asyncio.run(capture())
