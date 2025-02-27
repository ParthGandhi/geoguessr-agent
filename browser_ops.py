import base64
import json
import os
from typing import List

from playwright.sync_api import Page

import vlm


def take_screenshot(page: Page) -> str:
    print("Taking screenshot")
    screenshot_bytes = page.screenshot(type="jpeg")
    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    return screenshot_base64


def pan_right(page: Page) -> None:
    print("Panning right")
    page.keyboard.down("D")
    page.wait_for_timeout(1000)
    page.keyboard.up("D")


def zoom_in_screenshot(page: Page, obj: vlm.InterestingObject) -> str:
    """
    Zooms in on an object, takes a screenshot, and zooms out back to the original view.

    Geoguessr doesn't like a large zoom all at once, so we zoom in in smaller increments.
    """
    print(f"Zooming in to see object {obj['name']} at {obj['x']}, {obj['y']}")
    page.mouse.move(obj["x"], obj["y"])

    zoom_amount = 200
    zoom_steps = 3

    # Zoom in with multiple smaller increments
    for _ in range(zoom_steps):
        page.mouse.wheel(0, -zoom_amount)
        page.wait_for_timeout(200)

    screenshot = take_screenshot(page)

    # Zoom out with matching increments
    for _ in range(zoom_steps):
        page.mouse.wheel(0, zoom_amount)
        page.wait_for_timeout(200)

    return screenshot


def _load_cookies() -> List[dict]:
    cookies_path = os.path.abspath("cookies.json")
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"Cookies file not found at {cookies_path}")

    with open(cookies_path, "r") as f:
        return json.load(f)


def get_page(p) -> Page:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        locale="en-US",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
        viewport={"width": 1024, "height": 1024},
    )
    cookies = _load_cookies()
    context.add_cookies(cookies)
    return context.new_page()


def start_round(page: Page) -> None:
    # reload to get the latest round
    page.reload()
    page.wait_for_selector("text='Place your pin on the map'", timeout=10000)

    # The keyboard controls aren't activated till the first mouse click.
    # So click somewhere randomly on the page (which may move the map around), then go back to the starting point.
    page.mouse.click(512, 512)
    page.wait_for_timeout(1000)
    # Press 'r' to reset to the starting point
    page.keyboard.press("r")
    page.wait_for_timeout(1000)
