import base64
import json
import math
import os
from io import BytesIO
from typing import List

from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import Page, sync_playwright

import geoguessr
import vlm

load_dotenv()


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
    """
    print(f"Zooming in to see object {obj['name']} at {obj['x']}, {obj['y']}")
    page.mouse.move(obj["x"], obj["y"])

    page.mouse.wheel(0, -1000)
    page.wait_for_timeout(1000)

    screenshot = take_screenshot(page)

    page.mouse.wheel(0, 1000)
    page.wait_for_timeout(1000)
    return screenshot


def deduplicate_interesting_objects(
    objects: List[vlm.InterestingObject],
) -> List[vlm.InterestingObject]:
    """
    Sometimes the object detection returns multiple items for the same object or objects very close to each other.
    In either case, we need to only zoom in once to see what we need.
    """
    picked_objects: List[vlm.InterestingObject] = []
    for obj in objects:
        # Check if this object is too close to any already kept object
        is_duplicate = False
        for picked_obj in picked_objects:
            distance = math.dist(
                (obj["x"], obj["y"]), (picked_obj["x"], picked_obj["y"])
            )
            if distance < 250:
                is_duplicate = True
                break

        if not is_duplicate:
            picked_objects.append(obj)

    print(f"Deduplicated {len(objects)} objects to {len(picked_objects)}")
    return picked_objects


def _get_cookies_file() -> str:
    cookies_path = os.path.abspath("cookies.json")
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"Cookies file not found at {cookies_path}")
    return cookies_path


def load_cookies() -> List[dict]:
    with open(_get_cookies_file(), "r") as f:
        return json.load(f)


def save_base64_images(images: List[str], game_token: str, round_number: int) -> None:
    """
    Saves all the images to the data directory for this game and round.
    """
    output_path = os.path.join("data", game_token, str(round_number))
    os.makedirs(output_path, exist_ok=True)
    print(f"Saving {len(images)} images to {output_path}")
    for i, img_str in enumerate(images):
        img_data = base64.b64decode(img_str)
        img = Image.open(BytesIO(img_data))
        img_path = os.path.join(output_path, f"image_{i}.png")
        img.save(img_path)


def explore_location(page: Page) -> List[str]:
    screenshots = []
    for _ in range(5):
        pan_right(page)
        full_screenshot = take_screenshot(page)
        screenshots.append(full_screenshot)

        interesting_objects = vlm.identify_objects(full_screenshot)
        interesting_objects = deduplicate_interesting_objects(interesting_objects)

        for obj in interesting_objects:
            zoomed_screenshot = zoom_in_screenshot(page, obj)
            screenshots.append(zoomed_screenshot)

    return screenshots


def _print_final_score(page: Page, game_token: str) -> None:
    game_state = geoguessr.get_game_state(page, game_token)

    total_score = game_state.totalScore.amount
    total_percentage = game_state.totalScore.percentage
    total_distance_km = float(game_state.totalDistance.meters["amount"])

    # Find best and worst guesses
    distances = [g.distanceInMeters for g in game_state.guesses]
    best_distance = min(distances) / 1000
    worst_distance = max(distances) / 1000

    print("\n=== Final Results ===")
    print(f"Total Score: {total_score}, ({total_percentage:.1f}%)")
    print(f"Total Distance: {total_distance_km:.1f} km")
    print(f"Best Guess: {best_distance:.1f} km")
    print(f"Worst Guess: {worst_distance:.1f} km")
    print("==================\n")


def _print_round_score(
    player: geoguessr.Player,
    round_number: int,
    identified_location: vlm.IdentifiedLocation,
) -> None:
    guess = player.guesses[round_number - 1]
    distance_km = float(guess.distance.meters["amount"])
    print("\n=== Round Results ===")
    print(f"Round {round_number}")
    print(
        f"Guessed: {identified_location['latitude']:.4f}, {identified_location['longitude']:.4f}"
    )
    print(f"Explanation: {identified_location['explanation']}")
    print(f"Score: {guess.roundScoreInPoints}, ({guess.roundScoreInPercentage:.1f}%)")
    print(f"Distance: {distance_km:.1f} km")
    print("==================\n")


def _get_page(p) -> Page:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        locale="en-US",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36",
        viewport={"width": 1024, "height": 1024},
    )
    cookies = load_cookies()
    context.add_cookies(cookies)
    return context.new_page()


def _start_round(page: Page) -> None:
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


def main():
    with sync_playwright() as p:
        page = _get_page(p)
        game_token = geoguessr.start_new_game(page)
        page.goto(f"https://www.geoguessr.com/game/{game_token}")

        # each game has 5 rounds
        for round_number in range(1, 2):
            print(f"\nStarting round {round_number}")
            _start_round(page)

            all_screenshots = explore_location(page)
            save_base64_images(all_screenshots, game_token, round_number)

            identified_location = vlm.identify_location(all_screenshots)

            player = geoguessr.submit_guess(
                page,
                game_token,
                identified_location["latitude"],
                identified_location["longitude"],
            )

            _print_round_score(player, round_number, identified_location)
            page.wait_for_timeout(1000)

        _print_final_score(page, game_token)


if __name__ == "__main__":
    main()
