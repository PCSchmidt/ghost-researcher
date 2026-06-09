"""Measure the bot-detection block rate of the configured CloakBrowser CDP server.

This is the before/after instrument for v1.2.1 (CloakBrowser stealth integration,
DEC-009). Point it at a running cloakserve via ``CLOAK_CDP_URL`` and it navigates a
set of real-world, frequently-protected targets, reporting how many came back
blocked (Cloudflare/Turnstile interstitial, access denied, or empty navigation).

Run the same set against a vanilla baseline and the stealth browser to prove the
unblock:

    # Baseline (vanilla Chromium)
    CLOAKSERVE_STEALTH=0 python backend/scripts/start_cloakserve.py   # terminal 1
    CLOAK_CDP_URL=http://localhost:9222 python -m evals.blocked_rate --label vanilla

    # Stealth (CloakBrowser patched binary)
    CLOAKSERVE_STEALTH=1 python backend/scripts/start_cloakserve.py   # terminal 1
    CLOAK_CDP_URL=http://localhost:9222 python -m evals.blocked_rate --label stealth

Note: from a residential IP both may pass — the block is IP/ASN-driven, so the
decisive run is from the Railway datacenter IP.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.config import Settings
from backend.executor.navigate import navigate_to_url
from evals.eval_runner import DEFAULT_RESULTS_DIR, load_env_file

# Real-world targets that returned Cloudflare/security-verification walls in the
# first production run. These are the honest before/after benchmark.
DEFAULT_TARGETS: list[str] = [
    "https://www.energy.gov/oe/clean-energy-resources-meet-data-center-electricity-demand",
    "https://www.pewresearch.org/short-reads/2025/10/24/what-we-know-about-energy-use-at-us-data-centers-amid-the-ai-boom/",
    "https://www.belfercenter.org/research-analysis/ai-data-centers-us-electric-grid",
    "https://www.goldmansachs.com/insights/articles/fuel-cells-could-help-meet-the-power-demand-from-data-centers",
    "https://www.coresite.com/blog/fuel-cells-onsite-power-generation-solution-for-data-centers",
    "https://www.iea.org/news/data-centre-electricity-use-surged-in-2025-even-with-tightening-bottlenecks-driving-a-scramble-for-solutions",
    "https://www.bloomenergy.com/industries/data-center-power/",
    "https://www.datacenterknowledge.com/energy-power-supply/how-data-centers-redefined-energy-and-power-in-2025",
]


async def measure_block_rate(
    targets: list[str],
    *,
    settings: Settings,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Navigate each target and classify the outcome."""
    cases: list[dict[str, Any]] = []
    for url in targets:
        case: dict[str, Any] = {"url": url}
        try:
            result = await navigate_to_url(settings, url=url, timeout_seconds=timeout_seconds)
            case.update(
                {
                    "status_code": result.status_code,
                    "page_type": result.page_type,
                    "detection_blocked": result.detection_blocked,
                    "blocked_reason": result.blocked_reason,
                    "title": result.title,
                    "excerpt_len": len(result.content_excerpt or ""),
                    "outcome": _classify(result.detection_blocked, result.status_code, result.content_excerpt or ""),
                }
            )
        except Exception as exc:  # noqa: BLE001 — a nav error counts as a failed fetch
            case.update({"outcome": "error", "error": f"{type(exc).__name__}: {exc}"})
        cases.append(case)

    blocked = sum(1 for c in cases if c["outcome"] == "blocked")
    errored = sum(1 for c in cases if c["outcome"] == "error")
    ok = sum(1 for c in cases if c["outcome"] == "ok")
    total = len(cases)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "cloak_cdp_url": settings.cloak_cdp_url,
        "target_count": total,
        "blocked": blocked,
        "errored": errored,
        "ok": ok,
        "block_rate": round(blocked / total, 3) if total else 0.0,
        "usable_rate": round(ok / total, 3) if total else 0.0,
        "cases": cases,
    }


def _classify(detection_blocked: bool, status_code: int, excerpt: str) -> str:
    """A target is 'blocked' if flagged, non-2xx, or returned no usable content."""
    if detection_blocked:
        return "blocked"
    if status_code >= 400:
        return "blocked"
    if len(excerpt.strip()) < 120:
        return "blocked"
    return "ok"


def _load_targets(urls_file: Path | None) -> list[str]:
    if urls_file is None:
        return list(DEFAULT_TARGETS)
    lines = urls_file.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure CloakBrowser block rate against protected targets.")
    parser.add_argument("--label", default="unlabeled", help="Run label, e.g. 'vanilla' or 'stealth'.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of targets (0 = all).")
    parser.add_argument("--urls-file", type=Path, default=None, help="Newline-delimited URL list (overrides defaults).")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--no-write", action="store_true", help="Print results without writing an artifact.")
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    settings = Settings.from_env(load_env_file())
    targets = _load_targets(args.urls_file)
    if args.limit > 0:
        targets = targets[: args.limit]

    payload = await measure_block_rate(targets, settings=settings)
    payload["label"] = args.label

    if not args.no_write:
        args.results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = args.results_dir / f"blocked_rate_{args.label}_{timestamp}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        payload["artifact_path"] = str(path)

    print(
        f"[{args.label}] block_rate={payload['block_rate']} "
        f"usable_rate={payload['usable_rate']} "
        f"(blocked={payload['blocked']} ok={payload['ok']} errored={payload['errored']} of {payload['target_count']})"
    )
    for case in payload["cases"]:
        print(f"  {case['outcome']:>7}  {case['url']}")


if __name__ == "__main__":
    asyncio.run(_main())
