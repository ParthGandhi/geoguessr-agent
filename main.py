import base64
import os
from io import BytesIO
from typing import List

from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import Page, sync_playwright

import browser_ops
import geoguessr
import scorer
import vlm

load_dotenv()


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
        browser_ops.pan_right(page)
        full_screenshot = browser_ops.take_screenshot(page)
        screenshots.append(full_screenshot)

        interesting_objects = vlm.identify_objects(full_screenshot)
        interesting_objects = vlm.deduplicate_interesting_objects(interesting_objects)
        for obj in interesting_objects:
            zoomed_screenshot = browser_ops.zoom_in_screenshot(page, obj)
            screenshots.append(zoomed_screenshot)

    return screenshots


def main():
    with sync_playwright() as p:
        page = browser_ops.get_page(p)
        game_token = geoguessr.start_new_game(page)
        page.goto(f"https://www.geoguessr.com/game/{game_token}")

        game_results = scorer.GameResults(
            game_token=game_token,
            rounds=[],
        )

        # each game has 5 rounds
        for round_number in range(1, 6):
            print(f"\nStarting round {round_number}")
            browser_ops.start_round(page)

            all_screenshots = explore_location(page)
            save_base64_images(all_screenshots, game_token, round_number)

            # Get predictions from both models
            gpt4o_location = vlm.identify_location_gpt4o(all_screenshots)
            o1_location = vlm.identify_location_o1(all_screenshots)

            # Submit GPT-4O guess and get actual score
            game_state = geoguessr.submit_guess(
                page,
                game_token,
                gpt4o_location["latitude"],
                gpt4o_location["longitude"],
            )

            # Save round results and print
            game_results.save_round_results(
                game_state,
                round_number,
                gpt4o_location,
                o1_location,
                game_state.player.guesses[-1].roundScoreInPoints,
            )
            game_results.print_last_round()

            page.wait_for_timeout(1000)

        game_results.print_final_score()


if __name__ == "__main__":
    main()
