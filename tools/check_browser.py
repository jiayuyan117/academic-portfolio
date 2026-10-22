"""Render the homepage and standalone charts with all HTTP(S) requests blocked."""
from __future__ import annotations

from pathlib import Path
import argparse
import re

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".runtime" / "browser-checks"
CHARTS = ROOT / "projects" / "04-bike-sharing-interactive-visualization" / "charts"


def main() -> None:
    """Check desktop/mobile and offline rendering; save screenshots or raise on failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="Optional installed Chromium/Chrome executable")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser)
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
        assert page.locator("section.card").count() == 8
        assert page.title() == "Jiayu Yan — Data Analytics Portfolio"
        for width in (1280, 375):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"Homepage overflows at {width}px"
            for image in page.locator(".research-image img").all():
                image.scroll_into_view_if_needed()
                assert image.evaluate("(img) => img.complete && img.naturalWidth > 0")
            assert page.locator(".research-image img").count() >= 3
            page.screenshot(path=str(OUTPUT / f"homepage-{width}.png"), full_page=True)
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.screenshot(path=str(OUTPUT / f"homepage-{width}-viewport.png"))
        assert not errors, errors
        page.goto((ROOT / "projects/08-nlp-job-postings/report.html").as_uri())
        assert page.title() == "Does the Skill Signal Help? | Jiayu Yan"
        assert page.locator("figure img").count() == 3
        page.wait_for_function(
            "() => [...document.querySelectorAll('figure img')].every(img => img.complete && img.naturalWidth > 0)"
        )
        for width in (1280, 375):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"NLP report overflows at {width}px"
            page.screenshot(path=str(OUTPUT / f"nlp-report-{width}.png"), full_page=True)
        assert not errors, errors
        assert not blocked, f"Research brief requested the network: {blocked}"
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
            if path.name == "03_calendar_heatmap.html":
                page.wait_for_selector(".heatmaplayer image")
                assert page.evaluate(
                    "document.querySelector('.js-plotly-plot')._fullData[0].z.length"
                ) == 7
                page.get_by_text("2012", exact=True).click()
                page.wait_for_function(
                    "document.querySelector('.js-plotly-plot').data[1].visible === true"
                )
            assert not blocked, f"Offline page requested the network: {blocked}"
            page.screenshot(path=str(OUTPUT / f"{path.stem}.png"), full_page=True)
            print(f"{path.name}: rendered with HTTP(S) blocked")
        context.close()
        browser.close()
    print("Homepage and NLP brief desktop/mobile, plus four offline charts passed.")


if __name__ == "__main__":
    main()
