import base64
import os
from dataclasses import dataclass
from io import BytesIO
from typing import List

from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import Page, sync_playwright

load_dotenv()

import browser_ops  # noqa: E402
import geoguessr  # noqa: E402
import output  # noqa: E402
import scorer  # noqa: E402
import vlm  # noqa: E402


@dataclass
class ExplorationResult:
    regular_screenshots: list[str]
    zoomed_screenshots: list[str]

    @property
    def all_screenshots(self) -> list[str]:
        return self.regular_screenshots + self.zoomed_screenshots


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


def explore_location(page: Page) -> ExplorationResult:
    regular_screenshots = []
    zoomed_screenshots = []
    for _ in range(5):
        browser_ops.pan_right(page)
        full_screenshot = browser_ops.take_screenshot(page)
        regular_screenshots.append(full_screenshot)

        interesting_objects = vlm.identify_objects(full_screenshot)
        interesting_objects = vlm.deduplicate_interesting_objects(interesting_objects)
        for obj in interesting_objects:
            zoomed_screenshot = browser_ops.zoom_in_screenshot(page, obj)
            zoomed_screenshots.append(zoomed_screenshot)

    return ExplorationResult(
        regular_screenshots=regular_screenshots, zoomed_screenshots=zoomed_screenshots
    )


def _play_round(
    page: Page, game_token: str, round_number: int, game_results: scorer.GameResults
) -> None:
    """Play a single round of GeoGuessr and record the results."""
    print(f"\nStarting round {round_number}")
    browser_ops.start_round(page)

    exploration_result = explore_location(page)
    save_base64_images(exploration_result.all_screenshots, game_token, round_number)

    gpt4o_location = vlm.identify_location_gpt4o(exploration_result.all_screenshots)
    o1_location = vlm.identify_location_o1(exploration_result.all_screenshots)

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
    output.print_round_results(game_results.rounds[-1])

    page.wait_for_timeout(1000)


def main():
    NUM_GAMES = 5
    all_games = []

    with sync_playwright() as p:
        page = browser_ops.get_page(p)

        for game_num in range(1, NUM_GAMES + 1):
            print(f"\n=== Starting Game {game_num}/{NUM_GAMES} ===")

            game_token = geoguessr.start_new_game(page)
            page.goto(f"https://www.geoguessr.com/game/{game_token}")

            game_results = scorer.GameResults(
                game_token=game_token,
                rounds=[],
            )

            # each game has 5 rounds
            for round_number in range(1, 6):
                _play_round(page, game_token, round_number, game_results)

            output.print_game_results(game_results)
            all_games.append(game_results)
            # print the aggregate results after each game
            output.print_aggregate_results(all_games)

        output.print_aggregate_results(all_games)


if __name__ == "__main__":
    main()
