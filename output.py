from dataclasses import dataclass
from typing import Callable, List

from tabulate import tabulate

from scorer import GameResults, RoundResult


@dataclass
class ModelStats:
    model_name: str
    total_score: int
    score_percentage: float
    avg_score_per_game: float
    median_distance_km: float
    min_distance_km: float
    max_distance_km: float

    @classmethod
    def from_rounds(
        cls,
        model_name: str,
        rounds: List[RoundResult],
        score_fn: Callable[[RoundResult], int],
        distance_fn: Callable[[RoundResult], float],
        total_games: int,
    ) -> "ModelStats":
        """Create stats from a list of rounds."""
        scores = [score_fn(r) for r in rounds]
        distances = [distance_fn(r) for r in rounds]
        total_score = sum(scores)
        total_possible = len(rounds) * 5000

        return cls(
            model_name=model_name,
            total_score=total_score,
            score_percentage=(total_score / total_possible) * 100,
            avg_score_per_game=total_score / total_games,
            median_distance_km=sorted(distances)[len(distances) // 2],
            min_distance_km=min(distances),
            max_distance_km=max(distances),
        )

    def to_table_row(self) -> List[str]:
        """Convert stats to a table row for printing."""
        return [
            self.model_name,
            f"{self.score_percentage:.1f}%",
            f"{self.total_score:,d}",
            f"{self.median_distance_km:,.1f}",
            f"{self.min_distance_km:,.1f}",
            f"{self.max_distance_km:,.1f}",
        ]


@dataclass
class AggregateModelStats(ModelStats):
    """Statistics for a model's performance across multiple games."""

    max_game_score: int
    min_game_score: int

    @classmethod
    def from_rounds(
        cls,
        model_name: str,
        rounds: List[RoundResult],
        score_fn: Callable[[RoundResult], int],
        distance_fn: Callable[[RoundResult], float],
        total_games: int,
    ) -> "AggregateModelStats":
        """Create aggregate stats from a list of rounds."""
        scores = [score_fn(r) for r in rounds]
        distances = [distance_fn(r) for r in rounds]
        total_score = sum(scores)
        total_possible = len(rounds) * 5000
        game_scores = [sum(scores[i : i + 5]) for i in range(0, len(scores), 5)]

        return cls(
            model_name=model_name,
            total_score=total_score,
            score_percentage=(total_score / total_possible) * 100,
            avg_score_per_game=total_score / total_games,
            median_distance_km=sorted(distances)[len(distances) // 2],
            min_distance_km=min(distances),
            max_distance_km=max(distances),
            max_game_score=max(game_scores),
            min_game_score=min(game_scores),
        )

    def to_table_row(self) -> List[str]:
        """Convert aggregate stats to a table row for printing."""
        return [
            self.model_name,
            f"{self.score_percentage:.1f}%",
            f"{self.avg_score_per_game:,.1f}",
            f"{self.max_game_score:,d}",
            f"{self.min_game_score:,d}",
            f"{self.median_distance_km:,.1f}",
            f"{self.min_distance_km:,.1f}",
            f"{self.max_distance_km:,.1f}",
        ]


def print_round_results(round_result: RoundResult) -> None:
    """Print the results of a single round."""
    lines = [
        f"\n=== Round {round_result.round_number} Results ===\n",
        f"Actual Location: ({round_result.actual_location.lat:.4f}, {round_result.actual_location.lng:.4f})",
        "\nGPT-4o:",
        f"  Score: {round_result.gpt4o_guess.score:,d}",
        f"  Distance: {round_result.gpt4o_guess.distance_km:.1f} km",
        f"  Explanation: {round_result.gpt4o_guess.explanation}",
        "\no1:",
        f"  Score: {round_result.o1_guess.score:,d}",
        f"  Distance: {round_result.o1_guess.distance_km:.1f} km",
        f"  Explanation: {round_result.o1_guess.explanation}",
        "\n==================\n",
    ]
    print("\n".join(lines))


def print_game_results(game_results: GameResults) -> None:
    """Print the results of a complete game."""
    gpt4o = ModelStats.from_rounds(
        "GPT-4o",
        game_results.rounds,
        lambda r: r.gpt4o_guess.score,
        lambda r: r.gpt4o_guess.distance_km,
        total_games=1,
    )
    o1 = ModelStats.from_rounds(
        "o1",
        game_results.rounds,
        lambda r: r.o1_guess.score,
        lambda r: r.o1_guess.distance_km,
        total_games=1,
    )

    data = [
        [
            "Model",
            "Score %",
            "Avg Score/Game (/25,000)",
            "Median Distance (km)",
            "Best Guess (km)",
            "Worst Guess (km)",
        ],
        gpt4o.to_table_row(),
        o1.to_table_row(),
    ]

    print("\n=== Final Results ===\n")
    print(tabulate(data, headers="firstrow", tablefmt="github"))
    print("\n==================\n")


def print_aggregate_results(all_games: List[GameResults]) -> None:
    """Print aggregate statistics across all games."""
    total_games = len(all_games)
    all_rounds = [r for game in all_games for r in game.rounds]

    # Get stats for each model
    gpt4o = AggregateModelStats.from_rounds(
        "GPT-4o",
        all_rounds,
        lambda r: r.gpt4o_guess.score,
        lambda r: r.gpt4o_guess.distance_km,
        total_games=total_games,
    )
    o1 = AggregateModelStats.from_rounds(
        "o1",
        all_rounds,
        lambda r: r.o1_guess.score,
        lambda r: r.o1_guess.distance_km,
        total_games=total_games,
    )
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
        gpt4o.to_table_row(),
        o1.to_table_row(),
    ]

    print("\n=== Aggregate Results ===\n")
    print(tabulate(data, headers="firstrow", tablefmt="github"))
    print("\n==================\n")
