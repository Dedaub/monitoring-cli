"""Draw a widget with the web app's own chart code, in a headless browser.

The web app has a bare page, `/render/widget` (app/render/widget/WidgetRender.tsx).
Before the page loads, an init script sets `window.__DEDAUB_WIDGET__` to
{type, config, rows, columns?, label?, theme?, width?, height?}. The page makes
no API call and reads nothing from the URL. It sets `data-widget-ready` on
<html> to "1" when the chart is drawn, or to "error" when it cannot read the
input; the picture is the element `[data-widget-render]`.

Playwright is an optional dependency (the `render` extra): it is imported only
when a picture is drawn.
"""

from __future__ import annotations

import importlib
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

PAGE_PATH = "/render/widget"
READY_ATTR = "data-widget-ready"
READY_SELECTOR = f'html[{READY_ATTR}="1"], html[{READY_ATTR}="error"]'
# Set with READY_ATTR "1" when the widget shows a message in place of a chart
# (a column left the query, an unsupported type): the text of the message.
STATE_ATTR = "data-widget-state"
MESSAGE_ATTR = "data-widget-message"
TARGET = "[data-widget-render]"
# WidgetRender.tsx readInput: the default size and the limits of the card.
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 360
MIN_SIZE = 200
MAX_SIZE = 2560
# The only hosts other than the app that the page may reach: the fonts of the
# chart text. Every other request (analytics, ads, a tag manager) is blocked,
# because the page holds the rows of the query.
FONT_HOSTS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})


def allowed(url: str, page_url: str) -> bool:
    """Whether the render page may load `url`: the app itself or its fonts."""
    target, app = urlsplit(url), urlsplit(page_url)
    if target.scheme in ("data", "blob"):
        return True
    if (target.scheme, target.netloc) == (app.scheme, app.netloc):
        return True
    return target.scheme == "https" and target.hostname in FONT_HOSTS


# The page puts the card in a 16 px padding (p-4): the viewport has room for it.
_MARGIN = 64

INSTALL_HINT = (
    "Install the render extra and a browser:\n"
    "  uv tool install --force 'monitoring-cli[render] @ git+https://github.com/Dedaub/monitoring-cli'\n"
    "  playwright install chromium\n"
    "Or use an installed Chrome: --browser-channel chrome."
)


class PlaywrightMissing(Exception):
    """Playwright is not installed, or no browser can start."""


class RenderFailed(Exception):
    """The page did not draw the widget: it said "error", it timed out, or the
    web app has no render page."""


@dataclass(frozen=True)
class Picture:
    """One picture, and the message that the widget shows in place of a
    chart (None when it drew a chart)."""

    data: bytes
    message: str | None = None


@dataclass(frozen=True)
class Shot:
    """One picture: the page input, the image type, and the pixel ratio."""

    input: Mapping[str, Any]
    kind: Literal["png", "jpeg"] = "png"
    scale: float = 1.0
    quality: int | None = None


def init_script(data: Mapping[str, Any]) -> str:
    """The init script that hands the input to the page. The input is JSON (a
    JavaScript expression), never text put into code: a row value such as
    "</script>" stays data. `<`, `>` and `&` are escaped too, so the script is
    also safe inside HTML."""
    text = json.dumps(data, ensure_ascii=True, allow_nan=False, default=str)
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f"window.__DEDAUB_WIDGET__ = {text};"


def _playwright() -> Any:
    """playwright.sync_api, imported only now (an optional dependency)."""
    try:
        return importlib.import_module("playwright.sync_api")
    except ImportError as e:
        raise PlaywrightMissing(f"Playwright is not installed. {INSTALL_HINT}") from e


def _launch(pw: Any, channel: str | None, error: type[Exception]) -> Any:
    """A headless Chromium: the given channel, else an installed Chrome, else
    the browser that `playwright install chromium` downloads."""
    channels = [channel] if channel else ["chrome", "chromium"]
    failures = []
    for name in channels:
        options: dict[str, Any] = {"headless": True}
        if name != "chromium":
            options["channel"] = name
        try:
            return pw.chromium.launch(**options)
        except error as e:
            failures.append(f"{name}: {str(e).splitlines()[0] if str(e) else e!r}")
    raise PlaywrightMissing(
        f"No browser could start ({'; '.join(failures)}). {INSTALL_HINT}"
    )


def render(
    page_url: str,
    shots: Sequence[Shot],
    *,
    channel: str | None = None,
    timeout: float = 60.0,
) -> list[Picture]:
    """The pictures of `shots`, one page load each, in one browser. The
    browser gets no token and no cookie: a new context for each picture."""
    api = _playwright()
    with api.sync_playwright() as pw:
        browser = _launch(pw, channel, api.Error)
        try:
            return [_shoot(api, browser, page_url, shot, timeout) for shot in shots]
        finally:
            browser.close()


def _shoot(
    api: Any, browser: Any, page_url: str, shot: Shot, timeout: float
) -> Picture:
    deadline = time.monotonic() + timeout

    def ms() -> float:
        return max(1.0, (deadline - time.monotonic()) * 1000)

    width = int(shot.input.get("width") or DEFAULT_WIDTH)
    height = int(shot.input.get("height") or DEFAULT_HEIGHT)
    context = browser.new_context(
        viewport={"width": width + _MARGIN, "height": height + _MARGIN},
        device_scale_factor=shot.scale,
        color_scheme="light" if shot.input.get("theme") == "light" else "dark",
    )
    try:
        context.route(
            "**/*",
            lambda route: (
                route.continue_()
                if allowed(route.request.url, page_url)
                else route.abort("blockedbyclient")
            ),
        )
        page = context.new_page()
        page.add_init_script(script=init_script(shot.input))
        response = page.goto(page_url, wait_until="domcontentloaded", timeout=ms())
        if response is not None and response.status >= 400:
            raise RenderFailed(
                f"{page_url} answered HTTP {response.status}: this web app has no"
                " render page yet. Give --app-url of a web app that has it."
            )
        page.wait_for_selector(READY_SELECTOR, state="attached", timeout=ms())
        if page.get_attribute("html", READY_ATTR) != "1":
            raise RenderFailed("The render page could not read the widget input.")
        options: dict[str, Any] = {
            "type": shot.kind,
            "timeout": ms(),
            "animations": "disabled",
        }
        if shot.kind == "jpeg" and shot.quality is not None:
            options["quality"] = shot.quality
        message = None
        if page.get_attribute("html", STATE_ATTR) == "message":
            message = page.get_attribute("html", MESSAGE_ATTR) or "(no text)"
        return Picture(page.locator(TARGET).screenshot(**options), message)
    except api.TimeoutError as e:
        raise RenderFailed(f"The chart was not drawn within {timeout:g}s.") from e
    except api.Error as e:
        raise RenderFailed(f"The browser failed: {e}") from e
    finally:
        context.close()
