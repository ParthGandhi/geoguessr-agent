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
from pydantic import BaseModel, Field

load_dotenv()

# https://docs.browser-use.com/development/telemetry#opting-out
os.environ["ANONYMIZED_TELEMETRY"] = "false"

Laminar.initialize()

llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

controller = Controller()

all_screenshots = []


async def take_screenshot(browser: BrowserContext):
    print("Taking screenshot")
    screenshot_base64 = await browser.take_screenshot()
    print("Screenshot taken")
    all_screenshots.append(screenshot_base64)


def _return_completed_action():
    return ActionResult(
        is_done=len(all_screenshots) == 8,
        success=len(all_screenshots) == 8,
    )


@controller.action("Pan right")
async def pan_right(browser: BrowserContext):
    print("Panning right")
    page = await browser.get_current_page()
    await page.keyboard.down("A")
    await asyncio.sleep(0.5)
    await take_screenshot(browser)
    await page.keyboard.up("A")
    return _return_completed_action()


class ZoomInParams(BaseModel):
    x: int = Field(description="The x coordinate of the object to zoom in on")
    y: int = Field(description="The y coordinate of the object to zoom in on")


@controller.action("Zoom in", param_model=ZoomInParams)
async def zoom_in(params: ZoomInParams, browser: BrowserContext):
    print(f"Zooming in to {params.x}, {params.y}")
    page = await browser.get_current_page()
    await page.mouse.move(params.x, params.y)
    await page.mouse.wheel(0, -500)
    await asyncio.sleep(1)
    await take_screenshot(browser)
    await page.mouse.wheel(0, 500)
    await asyncio.sleep(1)
    return _return_completed_action()


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

    game_url = "https://www.geoguessr.com/game/lgabJXZkbXKNKsqM"

    initial_actions = [
        {
            "open_tab": {"url": game_url},
        },
        {
            "click_element": {"index": 0},
        },
        {
            "wait": {
                "seconds": 1,
            }
        },
        {
            "send_keys": {
                "keys": "r",
            },
        },
        {
            "wait": {
                "seconds": 1,
            }
        },
    ]
    agent = Agent(
        task="""
Your task is to explore this Google map street-view location.


Repeat these steps in a loop:
1. `pan_right` to see a different part of the scene.
2. If you see an an object that can help identify the location, point at the object with the mouse and run the `zoom_in` action.
    Objects that can be used to identify the location include are:
    - Any kind of writing on sign boards, vehicles, buildings, road signs, sign posts etc
    - Flags
    - Vehicles (brands, models, etc)
    - Distinctive buildings
    - Other landmarks
3. Continue the loop
""",
        llm=llm,
        browser_context=browser_context,
        controller=controller,
        initial_actions=initial_actions,
    )
    result = await agent.run()
    print(result)
    show_base64_images(all_screenshots)


if __name__ == "__main__":
    asyncio.run(main())
