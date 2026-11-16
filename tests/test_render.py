"""The Playwright layer of render-widget, with a fake browser.

One integration test draws a real widget; it runs only when
DEDAUB_RENDER_APP_URL points at a web app (a dev server) with /render/widget,
and Playwright and a browser are installed.
"""

import contextlib
import importlib.util
import json
import os

import pytest

from monitoring_cli import render


class _Error(Exception):
    pass


class _Timeout(_Error):
    pass


class _FakeApi:
    """playwright.sync_api: records what the code asks of the browser."""

    Error = _Error
    TimeoutError = _Timeout

    def __init__(
        self, *, state="1", status=200, fail_channels=(), wait_error=None, message=None
    ):
        self.state = state
        self.message = message
        self.status = status
        self.fail_channels = set(fail_channels)
        self.wait_error = wait_error
        self.calls: list[tuple] = []

    @contextlib.contextmanager
    def sync_playwright(self):
        api = self

        class Response:
            status = api.status

        class Locator:
            def __init__(self, selector):
                self.selector = selector

            def screenshot(self, **options):
                api.calls.append(("screenshot", self.selector, options))
                return b"picture-" + options["type"].encode()

        class Page:
            def add_init_script(self, script):
                api.calls.append(("init", script))

            def goto(self, url, **options):
                api.calls.append(("goto", url, options["wait_until"]))
                return Response()

            def wait_for_selector(self, selector, **options):
                api.calls.append(("wait", selector, options["state"]))
                if api.wait_error is not None:
                    raise api.wait_error

            def get_attribute(self, selector, name):
                if name == render.STATE_ATTR:
                    return "message" if api.message else None
                if name == render.MESSAGE_ATTR:
                    return api.message
                return api.state

            def locator(self, selector):
                return Locator(selector)

        class Context:
            def route(self, pattern, handler):
                api.calls.append(("route", pattern))
                api.handler = handler

            def new_page(self):
                return Page()

            def close(self):
                api.calls.append(("context-closed",))

        class Browser:
            def new_context(self, **options):
                api.calls.append(("context", options))
                return Context()

            def close(self):
                api.calls.append(("browser-closed",))

        class Chromium:
            def launch(self, **options):
                channel = options.get("channel", "chromium")
                api.calls.append(("launch", channel))
                if channel in api.fail_channels:
                    raise _Error(f"{channel} is not installed\ndetails")
                return Browser()

        class Playwright:
            chromium = Chromium()

        yield Playwright()


def _input(**extra):
    return {
        "type": "line",
        "config": {},
        "rows": [],
        "width": 640,
        "height": 360,
        **extra,
    }


def test_init_script_keeps_row_text_as_data():
    script = render.init_script(_input(rows=[{"name": "</script><b>&"}]))
    assert script.startswith("window.__DEDAUB_WIDGET__ = ")
    assert "</script>" not in script and "<b>" not in script
    payload = script.removeprefix("window.__DEDAUB_WIDGET__ = ").removesuffix(";")
    assert json.loads(payload)["rows"] == [{"name": "</script><b>&"}]


def test_render_waits_for_the_page_and_shoots_the_card(monkeypatch):
    api = _FakeApi()
    monkeypatch.setattr(render, "_playwright", lambda: api)
    shots = [
        render.Shot(_input(theme="light"), "png", scale=2.0),
        render.Shot(_input(width=640, height=360), "jpeg", quality=85),
    ]
    pictures = render.render("http://localhost:3000/render/widget", shots)
    assert [p.data for p in pictures] == [b"picture-png", b"picture-jpeg"]
    assert all(p.message is None for p in pictures)
    assert ("launch", "chrome") in api.calls
    contexts = [c[1] for c in api.calls if c[0] == "context"]
    assert contexts[0] == {
        "viewport": {"width": 704, "height": 424},
        "device_scale_factor": 2.0,
        "color_scheme": "light",
    }
    assert (
        "goto",
        "http://localhost:3000/render/widget",
        "domcontentloaded",
    ) in api.calls
    assert ("wait", render.READY_SELECTOR, "attached") in api.calls
    png, jpeg = [c for c in api.calls if c[0] == "screenshot"]
    assert png[1] == jpeg[1] == "[data-widget-render]"
    assert "quality" not in png[2]
    assert jpeg[2]["type"] == "jpeg" and jpeg[2]["quality"] == 85
    assert api.calls.count(("context-closed",)) == 2
    assert api.calls[-1] == ("browser-closed",)


def test_render_falls_back_to_the_bundled_chromium(monkeypatch):
    api = _FakeApi(fail_channels={"chrome"})
    monkeypatch.setattr(render, "_playwright", lambda: api)
    render.render("https://app/render/widget", [render.Shot(_input())])
    assert [c for c in api.calls if c[0] == "launch"] == [
        ("launch", "chrome"),
        ("launch", "chromium"),
    ]


def test_no_browser_is_playwright_missing(monkeypatch):
    api = _FakeApi(fail_channels={"chrome", "chromium"})
    monkeypatch.setattr(render, "_playwright", lambda: api)
    with pytest.raises(render.PlaywrightMissing, match="playwright install chromium"):
        render.render("https://app/render/widget", [render.Shot(_input())])


@pytest.mark.parametrize(
    ("api", "message"),
    [
        (_FakeApi(state="error"), "could not read the widget input"),
        (_FakeApi(wait_error=_Timeout("t")), "not drawn within 60s"),
        (_FakeApi(status=404), "answered HTTP 404"),
    ],
)
def test_render_failures(monkeypatch, api, message):
    monkeypatch.setattr(render, "_playwright", lambda: api)
    with pytest.raises(render.RenderFailed, match=message):
        render.render("https://app/render/widget", [render.Shot(_input())])
    assert ("context-closed",) in api.calls


def test_missing_playwright_gives_the_install_hint(monkeypatch):
    def missing(name):
        raise ImportError(name)

    monkeypatch.setattr(render.importlib, "import_module", missing)
    with pytest.raises(render.PlaywrightMissing) as e:
        render.render("https://app/render/widget", [render.Shot(_input())])
    assert "monitoring-cli[render]" in str(e.value)
    assert "--browser-channel chrome" in str(e.value)


@pytest.mark.skipif(
    not os.environ.get("DEDAUB_RENDER_APP_URL")
    or importlib.util.find_spec("playwright") is None,
    reason="Set DEDAUB_RENDER_APP_URL to a web app with /render/widget, and install the render extra",
)
def test_render_a_line_chart_on_a_dev_server():
    url = os.environ["DEDAUB_RENDER_APP_URL"].rstrip("/") + render.PAGE_PATH
    rows = [{"day": f"2026-10-{d:02d}", "fee": d * 1.5} for d in range(1, 15)]
    page_input = _input(
        config={"x_axis_name": "day", "y_axis_name": "fee"}, rows=rows, label="Fees"
    )
    [picture] = render.render(url, [render.Shot(page_input, "png")])
    assert picture.startswith(b"\x89PNG")


def test_the_page_reaches_only_the_app_and_its_fonts():
    page = "https://app.dedaub.com/render/widget"
    assert render.allowed("https://app.dedaub.com/_next/static/x.js", page)
    assert render.allowed("https://fonts.gstatic.com/s/x.woff2", page)
    assert render.allowed("data:image/png;base64,AA==", page)
    assert not render.allowed("https://www.googletagmanager.com/gtm.js?id=x", page)
    assert not render.allowed("https://app.dedaub.com.evil.example/x", page)
    assert not render.allowed("http://fonts.gstatic.com/s/x.woff2", page)
    dev = "http://localhost:3000/render/widget"
    assert render.allowed("http://localhost:3000/api/env", dev)
    assert not render.allowed("http://localhost:8000/api/x", dev)


def test_each_context_blocks_the_other_hosts(monkeypatch):
    api = _FakeApi()
    monkeypatch.setattr(render, "_playwright", lambda: api)
    render.render("https://app.dedaub.com/render/widget", [render.Shot(input=_input())])
    assert ("route", "**/*") in api.calls

    class Route:
        def __init__(self, url):
            self.request = type("R", (), {"url": url})()
            self.done = ""

        def continue_(self):
            self.done = "continue"

        def abort(self, reason):
            self.done = "abort:" + reason

    tag, chunk = (
        Route("https://www.googletagmanager.com/gtm.js"),
        Route("https://app.dedaub.com/x.js"),
    )
    api.handler(tag)
    api.handler(chunk)
    assert tag.done == "abort:blockedbyclient"
    assert chunk.done == "continue"


def test_a_widget_message_comes_back_with_the_picture(monkeypatch):
    api = _FakeApi(message="This visualization type is not supported.")
    monkeypatch.setattr(render, "_playwright", lambda: api)
    [picture] = render.render(
        "https://app.dedaub.com/render/widget", [render.Shot(input=_input())]
    )
    assert picture.message == "This visualization type is not supported."
    assert picture.data == b"picture-png"
