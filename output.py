"""Output formatting utilities for GeoGuessr game results."""

from typing import List
from tabulate import tabulate

from scorer import GameResults, RoundResult


def print_round_results(round_result: RoundResult) -> None:
    """Print the results of a single round."""
    lines = [
        "\n=== Round Results ===",
        f"Round {round_result.round_number}",
        "",
        "Actual Location:",
        f"Location: {round_result.actual_location.lat:.4f}, {round_result.actual_location.lng:.4f}",
        "",
        "GPT-4O Guess:",
        f"Location: {round_result.gpt4o_guess.latitude:.4f}, {round_result.gpt4o_guess.longitude:.4f}",
        f"Score: {round_result.gpt4o_guess.score} points",
        f"Distance: {round_result.gpt4o_guess.distance_km:.1f} km",
        f"Explanation: {round_result.gpt4o_guess.explanation}",
        "",
        "O1 Guess:",
        f"Location: {round_result.o1_guess.latitude:.4f}, {round_result.o1_guess.longitude:.4f}",
        f"Score: {round_result.o1_guess.score} points",
        f"Distance: {round_result.o1_guess.distance_km:.1f} km",
        f"Explanation: {round_result.o1_guess.explanation}",
        "==================\n",
    ]
    print("\n".join(lines))


def print_game_results(game_results: GameResults) -> None:
    """Print the final scores and statistics for both models in a table format."""
    gpt4o_distances = [r.gpt4o_guess.distance_km for r in game_results.rounds]
    o1_distances = [r.o1_guess.distance_km for r in game_results.rounds]

    gpt4o_total = sum(r.gpt4o_guess.score for r in game_results.rounds)
    o1_total = sum(r.o1_guess.score for r in game_results.rounds)
    max_possible = len(game_results.rounds) * 5000

    data = [
        [
            "Model",
            "Score %",
            "Avg Score/Game (/25,000)",
            "Median Distance (km)",
            "Best Guess (km)",
            "Worst Guess (km)",
        ],
        [
            "GPT-4o",
            f"{(gpt4o_total/(max_possible)*100):.1f}%",
            f"{gpt4o_total:,d}",
            f"{sorted(gpt4o_distances)[len(gpt4o_distances)//2]:,.1f}",
            f"{min(gpt4o_distances):,.1f}",
            f"{max(gpt4o_distances):,.1f}",
        ],
        [
            "o1",
            f"{(o1_total/(max_possible)*100):.1f}%",
            f"{o1_total:,d}",
            f"{sorted(o1_distances)[len(o1_distances)//2]:,.1f}",
            f"{min(o1_distances):,.1f}",
            f"{max(o1_distances):,.1f}",
        ],
    ]

    print("\n=== Final Results ===\n")
    print(tabulate(data, headers="firstrow", tablefmt="github"))
    print("\n==================\n")


def print_aggregate_results(all_games: List[GameResults]) -> None:
    """Print aggregate statistics across all games."""
    total_games = len(all_games)
    total_rounds = sum(len(game.rounds) for game in all_games)

    # Collect all rounds for statistics
    gpt4o_scores = [r.gpt4o_guess.score for game in all_games for r in game.rounds]
    o1_scores = [r.o1_guess.score for game in all_games for r in game.rounds]
    gpt4o_distances = [
        r.gpt4o_guess.distance_km for game in all_games for r in game.rounds
    ]
    o1_distances = [r.o1_guess.distance_km for game in all_games for r in game.rounds]

    # Calculate game totals
    gpt4o_game_scores = [
        sum(r.gpt4o_guess.score for r in game.rounds) for game in all_games
    ]
    o1_game_scores = [sum(r.o1_guess.score for r in game.rounds) for game in all_games]

    # Calculate totals and averages
    gpt4o_total = sum(gpt4o_scores)
    o1_total = sum(o1_scores)

    data = [
        [
            "Model",
            "Score %",
            "Avg Score/Game (/25,000)",
            "Best Game (/25,000)",
            "Worst Game (/25,000)",
            "Median Distance (km)",
            "Best Guess (km)",
            "Worst Guess (km)",
        ],
        [
            "GPT-4o",
            f"{(gpt4o_total/(total_rounds*5000)*100):.1f}%",
            f"{gpt4o_total/total_games:,.1f}",
            f"{max(gpt4o_game_scores):,d}",
            f"{min(gpt4o_game_scores):,d}",
            f"{sorted(gpt4o_distances)[len(gpt4o_distances)//2]:,.1f}",
            f"{min(gpt4o_distances):,.1f}",
            f"{max(gpt4o_distances):,.1f}",
        ],
        [
            "o1",
            f"{(o1_total/(total_rounds*5000)*100):.1f}%",
            f"{o1_total/total_games:,.1f}",
            f"{max(o1_game_scores):,d}",
            f"{min(o1_game_scores):,d}",
            f"{sorted(o1_distances)[len(o1_distances)//2]:,.1f}",
            f"{min(o1_distances):,.1f}",
            f"{max(o1_distances):,.1f}",
        ],
    ]

    print(
        f"\n=== Aggregate Results ({total_games:,d} games, {total_rounds:,d} rounds) ===\n"
    )
    print(tabulate(data, headers="firstrow", tablefmt="github"))
    print("\n==================\n")
