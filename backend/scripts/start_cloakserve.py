import asyncio
import contextlib
import os
import signal
import sys
from urllib.request import urlopen
from urllib.error import URLError
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

    # Rewrite the Host header to 'localhost' before forwarding to Chromium.
    # Chromium's DNS-rebinding protection rejects WebSocket and HTTP requests
    # whose Host header is not localhost or an IP address.  The Railway internal
    # hostname (cloakbrowser.railway.internal) fails that check with HTTP 500.
    try:
        request_line = await asyncio.wait_for(client_reader.readline(), timeout=10.0)
        if request_line:
            rewritten: list[bytes] = []
            while True:
                line = await asyncio.wait_for(client_reader.readline(), timeout=10.0)
                if not line or line in (b"\r\n", b"\n"):
                    rewritten.append(b"\r\n")
                    break
                if line.lower().startswith(b"host:"):
                    rewritten.append(b"Host: localhost\r\n")
                else:
                    rewritten.append(line)
            target_writer.write(request_line)
            for h in rewritten:
                target_writer.write(h)
            await target_writer.drain()
    except Exception:
        pass  # fall through to bidirectional pipe for non-HTTP or on timeout

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


def _stealth_enabled() -> bool:
    """CloakBrowser stealth is on by default. Set CLOAKSERVE_STEALTH=0 to launch
    vanilla Chromium instead — used to capture the detection_blocked baseline for
    before/after measurement (see evals/blocked_rate.py)."""
    return os.getenv("CLOAKSERVE_STEALTH", "1").strip().lower() not in {"0", "false", "no"}


def _resolve_chromium(playwright, *, browser_port: int) -> tuple[str, list[str], str]:
    """Return (executable, chromium_args, mode_label) for the configured browser.

    Stealth mode launches CloakBrowser's patched Chromium binary, whose
    source-level fingerprint patches are activated by the --fingerprint* flags.
    Vanilla mode launches Playwright's stock Chromium (the previous behavior),
    kept only as a measurement baseline.
    """
    common_args = [
        "--headless=new",
        f"--remote-debugging-port={browser_port}",
        "--remote-allow-origins=*",
        "--disable-dev-shm-usage",
    ]
    proxy_server = os.getenv("PROXY_URL")
    if proxy_server:
        # Phase 1 wires the proxy path (DEC-010). Authenticated HTTP proxies are
        # handled in Phase 2's in-process CloakBrowser launch; a bare
        # --proxy-server here covers no-auth and inline-credential SOCKS5.
        common_args.append(f"--proxy-server={proxy_server}")

    if _stealth_enabled():
        from cloakbrowser.config import get_default_stealth_args
        from cloakbrowser.download import ensure_binary

        executable = ensure_binary()
        # get_default_stealth_args() already includes --no-sandbox and the
        # --fingerprint / --fingerprint-platform flags. Do NOT add --disable-gpu
        # here: the patched binary synthesizes a coherent GPU profile from the
        # seed, and disabling the GPU would break that fingerprint.
        args = [executable, *common_args, *get_default_stealth_args()]
        return executable, args, "CloakBrowser stealth"

    executable = playwright.chromium.executable_path
    args = [
        executable,
        *common_args,
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
    ]
    return executable, args, "vanilla"


async def main():
    print("Starting CloakBrowser CDP server...", flush=True)

    port = int(os.getenv("PORT", "9222"))
    browser_port = port + 1

    async with async_playwright() as p:
        executable, args, mode = _resolve_chromium(p, browser_port=browser_port)

        print(f"Launching {mode} Chromium on 127.0.0.1:{browser_port}...", flush=True)

        # Launch Chromium locally and expose it through a TCP proxy for Railway.
        process = await asyncio.create_subprocess_exec(*args)

        # Wait for Chromium's /json/version HTTP endpoint to return 200.
        # TCP-only check is insufficient — Chromium can accept the socket before
        # its HTTP server is ready, causing /json/version to return 500.
        version_url = f"http://127.0.0.1:{browser_port}/json/version"
        for _attempt in range(120):
            try:
                with urlopen(version_url, timeout=1.0) as resp:
                    if resp.status == 200:
                        print(f"Chromium HTTP ready on port {browser_port} (attempt {_attempt + 1})", flush=True)
                        break
            except (URLError, OSError):
                pass
            await asyncio.sleep(0.5)
        else:
            print("Chromium did not become HTTP-ready in time; proceeding anyway", flush=True)

        async def handle_proxy_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _handle_proxy_client(
                reader,
                writer,
                target_host="127.0.0.1",
                target_port=browser_port,
            )

        proxy_server = await asyncio.start_server(
            handle_proxy_client,
            host="0.0.0.0",
            port=port,
        )
        sockets = ", ".join(str(sock.getsockname()) for sock in proxy_server.sockets or [])
        print(f"Proxying CDP on {sockets} -> 127.0.0.1:{browser_port}", flush=True)

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
