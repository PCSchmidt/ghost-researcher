import asyncio
import os
import signal
import sys
from playwright.async_api import async_playwright

async def main():
    print("Starting CloakBrowser CDP server...", flush=True)
    
    port = os.getenv("PORT", "9222")
    
    async with async_playwright() as p:
        executable = p.chromium.executable_path
        
        args = [
            executable,
            "--headless=new",
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=0.0.0.0",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
        
        print(f"Launching Chromium on 0.0.0.0:{port}...", flush=True)
        
        # Launch Chromium manually so we can bind to 0.0.0.0 explicitly for Railway
        process = await asyncio.create_subprocess_exec(*args)
        
        stop_event = asyncio.Event()
        
        def handle_sigint():
            print("Received stop signal", flush=True)
            stop_event.set()
        
        # Handle graceful shutdown
        loop = asyncio.get_running_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, handle_sigint)
            loop.add_signal_handler(signal.SIGTERM, handle_sigint)
        except NotImplementedError:
            pass  # Windows does not support add_signal_handler fully
            
        await stop_event.wait()
        
        print("Shutting down CDP server...", flush=True)
        await browser_server.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
