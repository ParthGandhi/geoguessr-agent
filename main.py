import base64
import json
import os
import time
from io import BytesIO
from typing import List

from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import Page, sync_playwright

load_dotenv()

all_screenshots: List[str] = []


def take_screenshot(page: Page) -> None:
    print("Taking screenshot")
    screenshot_bytes = page.screenshot(type="jpeg", quality=80)
    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    print("Screenshot taken")
    all_screenshots.append(screenshot_base64)


def pan_right(page: Page) -> None:
    print("Panning right")
    page.keyboard.down("A")
    time.sleep(0.5)
    take_screenshot(page)
    page.keyboard.up("A")


def zoom_in(page: Page, x: int, y: int) -> None:
    print(f"Zooming in to {x}, {y}")
    page.mouse.move(x, y)
    page.mouse.wheel(0, -500)  # Zoom in
    time.sleep(1)
    take_screenshot(page)
    page.mouse.wheel(0, 500)  # Zoom back out
    time.sleep(1)


def _get_cookies_file() -> str:
    cookies_path = os.path.abspath("cookies.json")
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"Cookies file not found at {cookies_path}")
    return cookies_path


def load_cookies() -> List[dict]:
    with open(_get_cookies_file(), "r") as f:
        return json.load(f)


def show_base64_images(images: List[str]) -> None:
    """Opens and displays base64 encoded images using PIL.

    Args:
        images: List of base64 encoded image strings
    """
    print(f"Showing {len(images)} images")
    for img_str in images:
        img_data = base64.b64decode(img_str)
        img = Image.open(BytesIO(img_data))
        img.show()


def explore_location(page: Page) -> None:
    """Simulates the exploration pattern previously handled by the Agent"""
    # Take initial screenshot
    take_screenshot(page)

    for _ in range(4):
        pan_right(page)
        take_screenshot(page)

        # # Simulate zooming in at center of viewport
        # viewport_size = page.viewport_size
        # if viewport_size:
        #     center_x = viewport_size["width"] // 2
        #     center_y = viewport_size["height"] // 2
        #     zoom_in(page, center_x, center_y)


def main():
    game_url = "https://www.geoguessr.com/game/lgabJXZkbXKNKsqM"  # Original URL

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
            viewport={"width": 1024, "height": 1024},
        )

        # Load cookies
        cookies = load_cookies()
        context.add_cookies(cookies)

        # Create new page and navigate
        page = context.new_page()
        page.goto(game_url)

        page.wait_for_selector("text='Place your pin on the map'", timeout=10000)

        # Wait for and click the first element (game start)
        page.mouse.click(512, 512)
        time.sleep(1)

        # Press 'r' to reset to the starting point
        page.keyboard.press("r")
        time.sleep(1)

        explore_location(page)

        show_base64_images(all_screenshots)

        browser.close()


if __name__ == "__main__":
    main()
