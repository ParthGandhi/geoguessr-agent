import asyncio
import base64
import os
from io import BytesIO

from browser_use import (
    ActionResult,
    Agent,
    Browser,
    BrowserContextConfig,
    Controller,
)
from browser_use.browser.context import BrowserContext
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from lmnr import Laminar
from PIL import Image

load_dotenv()

# https://docs.browser-use.com/development/telemetry#opting-out
os.environ["ANONYMIZED_TELEMETRY"] = "false"

Laminar.initialize()

llm = ChatOpenAI(model="gpt-4o")

controller = Controller()

all_screenshots = []


@controller.action("Take a screenshot of the current page")
async def take_screenshot(browser: BrowserContext):
    print("Taking screenshot")
    screenshot_base64 = await browser.take_screenshot()
    print("Screenshot taken")
    all_screenshots.append(screenshot_base64)
    return ActionResult(
        is_done=len(all_screenshots) == 3,
        success=len(all_screenshots) == 3,
    )


@controller.action("Pan right")
async def pan_right(browser: BrowserContext):
    print("Panning right")
    await _pan(browser, "D")


async def _pan(browser: BrowserContext, direction: str):
    page = await browser.get_current_page()
    await page.keyboard.down(direction)
    await asyncio.sleep(1)
    await page.keyboard.up(direction)


def _get_cookies_file():
    cookies_path = os.path.abspath("cookies.json")
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"Cookies file not found at {cookies_path}")
    return cookies_path


def show_base64_images(images: list[str]) -> None:
    """Opens and displays base64 encoded images using PIL.

    Args:
        images: List of base64 encoded image strings
    """
    print(f"Showing {len(images)} images")
    for img_str in images:
        img_data = base64.b64decode(img_str)
        img = Image.open(BytesIO(img_data))
        img.show()


async def main():
    browser_context_config = BrowserContextConfig(
        locale="en-US",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
        viewport_expansion=-1,
        cookies_file=_get_cookies_file(),
    )
    browser = Browser()
    browser_context = BrowserContext(browser=browser, config=browser_context_config)

    game_url = "https://www.geoguessr.com/game/Jf3PT4rBb4oVxjdp"
    agent = Agent(
        task=f"""
        Your task is to explore a Google maps live location and take 3 screenshots of various scenery and interesting objects.

        You take a screenshot by calling the `take_screenshot` action.

        How to explore:
        See a different part of the scene using the `pan_right` action.

        Steps:
        1. Load the Geoguessr game {game_url}.
        2. Click on the map to enable the map controls.
        3. Explore the map
        4. Take screenshots of various scenery and interesting objects.
        """,
        llm=llm,
        browser_context=browser_context,
        controller=controller,
    )
    result = await agent.run()
    print(result)
    show_base64_images(all_screenshots)


if __name__ == "__main__":
    asyncio.run(main())
