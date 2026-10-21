"""Render the homepage and standalone charts with all HTTP(S) requests blocked."""
from __future__ import annotations

from pathlib import Path
import re

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".runtime" / "browser-checks"
CHARTS = ROOT / "projects" / "04-bike-sharing-interactive-visualization" / "charts"


def main() -> None:
    """Check desktop/mobile and offline rendering; save screenshots or raise on failure."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        blocked: list[str] = []

        def block_network(route):
            blocked.append(route.request.url)
            route.abort()

        context.route(re.compile(r"^https?://"), block_network)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "index.html").as_uri())
        assert page.locator("section.card").count() == 7
        assert page.title() == "Jiayu Yan — Data Analytics Portfolio"
        for width in (1280, 375):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"Homepage overflows at {width}px"
            page.screenshot(path=str(OUTPUT / f"homepage-{width}.png"), full_page=True)
        assert not errors, errors
        page.set_viewport_size({"width": 1280, "height": 900})
        paths = sorted(CHARTS.glob("*.html"))
        assert len(paths) == 4, f"Expected four charts, found {len(paths)}"
        for path in paths:
            errors.clear()
            page.goto(path.as_uri(), wait_until="load")
            page.wait_for_function("""() => {
                const plot = document.querySelector('.js-plotly-plot');
                if (plot && plot._fullLayout && plot.data && plot.data.length) {
                    return !!plot.querySelector('svg.main-svg');
                }
                return [...document.querySelectorAll('canvas')].some(
                    canvas => canvas.width > 0 && canvas.height > 0
                );
            }""", timeout=20000)
            assert not errors, f"{path.name}: {errors}"
            assert not blocked, f"Offline page requested the network: {blocked}"
            page.screenshot(path=str(OUTPUT / f"{path.stem}.png"), full_page=True)
            print(f"{path.name}: rendered with HTTP(S) blocked")
        context.close()
        browser.close()
    print("Homepage desktop/mobile and four offline charts passed.")


if __name__ == "__main__":
    main()
