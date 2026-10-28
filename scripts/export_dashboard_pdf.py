import asyncio
import subprocess
import sys
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent

async def export_dashboard():
    # Start the server as a subprocess
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.dashboard.app:app", "--host", "127.0.0.1", "--port", "8008", "--log-level", "error"],
        cwd=str(ROOT_DIR)
    )
    print("Dashboard server launched on port 8008...")
    time.sleep(3.0)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # 1750x860 viewport
            page = await browser.new_page(viewport={"width": 1750, "height": 860}, device_scale_factor=2)
            await page.goto("http://127.0.0.1:8008", wait_until="networkidle")
            await page.wait_for_timeout(1000)

            # Click play to let simulation run and populate live telemetry
            btn = page.locator("#btn-play-pause")
            if await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(3500)

            # Save PNG
            png_path = ROOT_DIR / "plots" / "dashboard_mission_control.png"
            await page.screenshot(path=str(png_path))
            print(f"Saved PNG to {png_path}")

            # Save PDF (vector selectable text!)
            pdf_path = ROOT_DIR / "plots" / "dashboard_mission_control.pdf"
            await page.pdf(
                path=str(pdf_path),
                width="1750px",
                height="860px",
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
            )
            print(f"Saved PDF to {pdf_path}")

            await browser.close()
    finally:
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")

if __name__ == "__main__":
    asyncio.run(export_dashboard())
