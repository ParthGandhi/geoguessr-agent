import base64
import os
from io import BytesIO
from typing import List

from PIL import Image

import geoguessr
import vlm


def print_final_score(game_state: geoguessr.GameState) -> None:
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


def print_round_score(
    game_state: geoguessr.GameState,
    round_number: int,
    identified_location: vlm.IdentifiedLocation,
) -> None:
    guess = game_state.player.guesses[round_number - 1]
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
