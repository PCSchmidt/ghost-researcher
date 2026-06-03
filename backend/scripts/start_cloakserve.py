import asyncio
import contextlib
import os
import signal
import sys
from playwright.async_api import async_playwright


async def _pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()


async def _handle_proxy_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    *,
    target_host: str,
    target_port: int,
) -> None:
    try:
        target_reader, target_writer = await asyncio.open_connection(target_host, target_port)
    except Exception:
        client_writer.close()
        with contextlib.suppress(Exception):
            await client_writer.wait_closed()
        return

    client_to_target = asyncio.create_task(_pipe_stream(client_reader, target_writer))
    target_to_client = asyncio.create_task(_pipe_stream(target_reader, client_writer))
    done, pending = await asyncio.wait(
        {client_to_target, target_to_client},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    for task in done:
        with contextlib.suppress(Exception):
            await task


async def main():
    print("Starting CloakBrowser CDP server...", flush=True)
    
    port = int(os.getenv("PORT", "9222"))
    browser_port = port + 1
    
    async with async_playwright() as p:
        executable = p.chromium.executable_path
        
        args = [
            executable,
            "--headless=new",
            f"--remote-debugging-port={browser_port}",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
        
        print(f"Launching Chromium on 127.0.0.1:{browser_port}...", flush=True)
        
        # Launch Chromium locally and expose it through a TCP proxy for Railway.
        process = await asyncio.create_subprocess_exec(*args)

        proxy_server = await asyncio.start_server(
            lambda reader, writer: _handle_proxy_client(
                reader,
                writer,
                target_host="127.0.0.1",
                target_port=browser_port,
            ),
            host="::",
            port=port,
        )
        print(f"Proxying CDP on [::]:{port} -> 127.0.0.1:{browser_port}", flush=True)
        
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
        
        print(f"Shutting down CDP server...", flush=True)
        proxy_server.close()
        await proxy_server.wait_closed()
        if process.returncode is None:
            process.terminate()
            await process.wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
