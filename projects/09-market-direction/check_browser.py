"""Optional real-browser validation; install playwright and a Chromium browser."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 partial(SimpleHTTPRequestHandler, directory=str(ROOT.parents[1])))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    out = ROOT / "browser-evidence"
    out.mkdir(exist_ok=True)
    records = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            for width in (390, 1440):
                page = browser.new_page(viewport={"width": width, "height": 950}, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                for route in ("index.html", "projects/09-market-direction/report.html"):
                    response = page.goto(f"http://127.0.0.1:{server.server_port}/{route}", wait_until="networkidle")
                    assert response.status == 200
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), route
                    if route.endswith("report.html"):
                        assert page.locator("h1").inner_text().replace("\n", " ").startswith("When the")
                        assert page.locator("img").evaluate_all("(imgs) => imgs.every(i => i.complete && i.naturalWidth > 0)")
                        page.locator("summary").last.click()
                        assert page.locator("details").last.get_attribute("open") is not None
                    else:
                        assert page.locator("#project-09").count() == 1
                        page.get_by_role("button", name="Data Science Track").click()
                        assert "highlighted" in page.locator("#project-09").get_attribute("class")
                    assert not errors, errors
                    name = ("report" if route.endswith("report.html") else "home") + f"-{width}"
                    page.screenshot(path=str(out / f"{name}.png"), full_page=True)
                    records.append({"page": route, "width": width, "http": response.status,
                                    "overflow": False, "javascript_errors": errors.copy()})
                page.close()
            browser.close()
    finally:
        server.shutdown()
    (out / "checks.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
