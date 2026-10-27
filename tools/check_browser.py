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
    parser.add_argument("--live-url", help="Also verify the deployed homepage and its same-site links")
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
        expected = [f"{number:02d}" for number in range(1, 9)]
        assert page.locator("section.card h3 .num").all_text_contents() == expected
        assert page.locator(".project-index a").evaluate_all(
            "(links) => links.map(a => a.hash)"
        ) == [f"#project-{number}" for number in expected]
        assert page.title() == "Jiayu Yan — Data Analytics Portfolio"
        for width in (1280, 375, 320):
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
        buttons = page.locator(".route-btn")
        for index, track in enumerate(("all", "ds", "ba", "eng")):
            buttons.nth(index).click()
            assert buttons.nth(index).get_attribute("aria-pressed") == "true"
            assert page.locator('.route-btn[aria-pressed="true"]').count() == 1
            for card in page.locator("section.card").all():
                assert card.evaluate("(el) => getComputedStyle(el).opacity") == "1"
                selected = track != "all" and track in card.get_attribute("data-tracks").split()
                assert ("highlighted" in (card.get_attribute("class") or "")) == selected
        for number in range(3, 8):
            folder = next((ROOT / "projects").glob(f"{number:02d}-*"))
            brief = folder / ("PROJECT.html" if number == 7 else "FIRST_READ.html")
            page.goto(brief.as_uri())
            for width in (1280, 375, 320):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), f"{brief}: overflow at {width}px"
                for image in page.locator("img").all():
                    assert image.evaluate("(img) => img.complete && img.naturalWidth > 0")
                page.screenshot(path=str(OUTPUT / f"brief-{number:02d}-{width}.png"), full_page=True)
            if number == 7:
                for button in page.locator(".sim-controls button").all():
                    button.click()
                    assert page.locator("#avl-svg circle").count() in (3, 4)
                    assert page.locator("#dept-list li").count() == 4
            assert not errors, errors
        page.goto((ROOT / "projects/08-nlp-job-postings/report.html").as_uri())
        assert page.title() == "Does the Skill Signal Help? | Jiayu Yan"
        assert page.locator("figure img").count() == 3
        page.wait_for_function(
            "() => [...document.querySelectorAll('figure img')].every(img => img.complete && img.naturalWidth > 0)"
        )
        for width in (1280, 375, 320):
            page.set_viewport_size({"width": width, "height": 900})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), f"NLP report overflows at {width}px"
            page.screenshot(path=str(OUTPUT / f"nlp-report-{width}.png"), full_page=True)
        assert not errors, errors
        for button in page.locator(".sim-btn").all():
            button.click()
            assert button.get_attribute("aria-pressed") == "true"
            assert page.locator('.sim-btn[aria-pressed="true"]').count() == 1
            assert page.locator("#case-body").inner_text()
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
        if args.live_url:
            live = browser.new_context()
            page = live.new_page()
            response = page.goto(args.live_url, wait_until="networkidle")
            assert response and response.status == 200
            assert page.locator("h1").inner_text() == "Data analytics.\nEvidence for decisions."
            assert page.locator("section.card h3 .num").all_text_contents() == expected
            for width in (1280, 375, 320):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                for image in page.locator(".research-image img").all():
                    image.scroll_into_view_if_needed()
                    page.wait_for_function(
                        "(img) => img.complete && img.naturalWidth > 0",
                        arg=image.element_handle(),
                    )
                    assert image.evaluate("(img) => img.complete && img.naturalWidth > 0")
                page.screenshot(path=str(OUTPUT / f"live-homepage-{width}.png"), full_page=True)
            links = page.locator("a").evaluate_all(
                "(links) => [...new Set(links.map(a => a.href).filter("
                "url => url.startsWith(location.origin) && !url.includes('#')))]"
            )
            for url in links:
                result = live.request.get(url)
                assert result.status == 200, f"{url}: HTTP {result.status}"
            print(f"Live homepage: three viewport widths, images, order and {len(links)} same-site links passed.")
            live.close()
        browser.close()
    print("Homepage, briefs 03–08, route/scenario controls and four offline charts passed.")


if __name__ == "__main__":
    main()
