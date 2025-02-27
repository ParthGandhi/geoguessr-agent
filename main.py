from typing import List

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

import browser_ops
import geoguessr
import output
import vlm

load_dotenv()


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

        # each game has 5 rounds
        for round_number in range(1, 6):
            print(f"\nStarting round {round_number}")
            browser_ops.start_round(page)

            all_screenshots = explore_location(page)
            output.save_base64_images(all_screenshots, game_token, round_number)

            identified_location = vlm.identify_location(all_screenshots)

            player = geoguessr.submit_guess(
                page,
                game_token,
                identified_location["latitude"],
                identified_location["longitude"],
            )

            output.print_round_score(player, round_number, identified_location)
            page.wait_for_timeout(1000)

        output.print_final_score(page, game_token)


if __name__ == "__main__":
    main()
