"""BrowserTools against the bundled demo page in a real headless Chromium."""
import pytest

from tools import BrowserTools

sync_api = pytest.importorskip("playwright.sync_api")

from conftest import ROOT  # noqa: E402

SITE = (ROOT / "examples" / "demo_site" / "index.html").as_uri()


@pytest.fixture(scope="module")
def page():
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"chromium unavailable: {exc}")
        pg = browser.new_page()
        yield pg
        browser.close()


@pytest.fixture
def tools(page, monkeypatch):
    monkeypatch.setenv("BROWSER_TIMEOUT", "3000")
    t = BrowserTools(page)
    assert t.navigate(SITE)["success"]
    return t


def test_fill_press_enter_verify(tools):
    assert tools.fill("input[name='q']", "python")["success"]
    assert tools.press_enter("input[name='q']")["success"]
    assert tools.verify_text("#summary", "4 results")["verified"]


def test_verify_failure(tools):
    r = tools.verify_text("#summary", "999 results")
    assert not r["success"] and r["verified"] is False


def test_missing_selector_times_out(tools):
    r = tools.click("#does-not-exist")
    assert not r["success"] and "Timeout" in r["message"]


def test_screenshot_absolute_path(tools, tmp_path):
    out = tmp_path / "s.png"
    assert tools.screenshot(str(out))["success"]
    assert out.stat().st_size > 0
