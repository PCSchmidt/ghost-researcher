"""Tests for the cloakserve launcher's browser-resolution helpers.

These cover the stealth toggle, vanilla-baseline arg composition, and proxy
wiring without launching a browser or downloading the CloakBrowser binary (the
stealth branch is exercised separately when cloakbrowser + binary are present).
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from backend.scripts import start_cloakserve


class _FakePlaywright:
    class chromium:  # noqa: N801 — mirrors playwright's attribute path
        executable_path = "/fake/path/chrome"


class StealthToggleTests(unittest.TestCase):
    def test_stealth_enabled_by_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(start_cloakserve._stealth_enabled())

    def test_stealth_disabled_by_falsey_values(self) -> None:
        for value in ("0", "false", "FALSE", "no"):
            with mock.patch.dict(os.environ, {"CLOAKSERVE_STEALTH": value}, clear=True):
                self.assertFalse(start_cloakserve._stealth_enabled(), value)


class ResolveChromiumTests(unittest.TestCase):
    def test_vanilla_mode_uses_playwright_executable(self) -> None:
        with mock.patch.dict(os.environ, {"CLOAKSERVE_STEALTH": "0"}, clear=True):
            executable, args, mode = start_cloakserve._resolve_chromium(
                _FakePlaywright, browser_port=9223
            )

        self.assertEqual("vanilla", mode)
        self.assertEqual("/fake/path/chrome", executable)
        self.assertEqual(executable, args[0])
        self.assertIn("--headless=new", args)
        self.assertIn("--remote-debugging-port=9223", args)
        self.assertIn("--no-sandbox", args)
        # Vanilla must NOT carry CloakBrowser fingerprint flags.
        self.assertFalse(any(a.startswith("--fingerprint") for a in args))

    def test_proxy_url_is_wired_into_args(self) -> None:
        env = {"CLOAKSERVE_STEALTH": "0", "PROXY_URL": "http://proxy.example:8080"}
        with mock.patch.dict(os.environ, env, clear=True):
            _executable, args, _mode = start_cloakserve._resolve_chromium(
                _FakePlaywright, browser_port=9223
            )

        self.assertIn("--proxy-server=http://proxy.example:8080", args)


if __name__ == "__main__":
    unittest.main()
