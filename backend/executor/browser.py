"""CloakBrowser connectivity primitives for GhostResearcher."""

from __future__ import annotations

from dataclasses import dataclass
from json import loads
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from backend.config import Settings


FetchText = Callable[[str, float], str]


@dataclass(frozen=True, slots=True)
class BrowserHealth:
    """Normalized health snapshot for the CloakBrowser CDP endpoint."""

    status: str
    version_url: str
    browser: str | None = None
    websocket_debugger_url: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "version_url": self.version_url,
            "browser": self.browser,
            "websocket_debugger_url": self.websocket_debugger_url,
            "detail": self.detail,
        }


def _default_fetch_text(url: str, timeout: float) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


class CloakBrowserClient:
    """Thin CDP health client that avoids pulling browser logic into the API layer."""

    def __init__(self, settings: Settings, *, fetch_text: FetchText | None = None) -> None:
        self._settings = settings
        self._fetch_text = fetch_text or _default_fetch_text

    @property
    def version_url(self) -> str:
        """Return the CDP version endpoint derived from the configured base URL."""
        parsed = urlparse(self._settings.cloak_cdp_url)
        scheme = parsed.scheme or "http"
        if scheme == "ws":
            scheme = "http"
        elif scheme == "wss":
            scheme = "https"

        path = parsed.path.rstrip("/")
        if path.endswith("/json/version"):
            version_path = path
        elif path.endswith("/json"):
            version_path = f"{path}/version"
        else:
            version_path = f"{path}/json/version" if path else "/json/version"

        return urlunparse((scheme, parsed.netloc, version_path, "", "", ""))

    def healthcheck(self, *, timeout: float = 2.0) -> BrowserHealth:
        """Probe the CDP server and return a normalized health object."""
        version_url = self.version_url
        if not self._settings.scrape_enabled:
            return BrowserHealth(status="disabled", version_url=version_url, detail="scraping disabled")

        try:
            payload = loads(self._fetch_text(version_url, timeout))
        except URLError as exc:
            return BrowserHealth(status="unreachable", version_url=version_url, detail=str(exc.reason))
        except TimeoutError:
            return BrowserHealth(status="timeout", version_url=version_url, detail="request timed out")
        except ValueError as exc:
            return BrowserHealth(status="invalid_response", version_url=version_url, detail=str(exc))

        return BrowserHealth(
            status="ok",
            version_url=version_url,
            browser=payload.get("Browser"),
            websocket_debugger_url=payload.get("webSocketDebuggerUrl"),
        )
