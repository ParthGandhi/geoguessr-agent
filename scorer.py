"""
Geogussr scoring is exponential and depends on the map size, etc.

https://www.reddit.com/r/geoguessr/comments/1cdelb2/can_somebody_help_me_understand_how_geoguesser/l1csyjc/
https://www.reddit.com/r/geoguessr/comments/15koyd6/how_much_close_you_have_to_be_for_5k_score/jvboz87/
https://www.plonkit.net/beginners-guide#:~:text=Scoring,score%20drop%2Doff%20is%20exponential.
"""

import math
from dataclasses import dataclass
from typing import Dict, List

import geoguessr


@dataclass
class LocationGuess:
    latitude: float
    longitude: float
    score: int
    distance_km: float
    explanation: str


@dataclass
class RoundResult:
    round_number: int
    gpt4o_guess: LocationGuess
    o1_guess: LocationGuess
    actual_location: geoguessr.Round


@dataclass
class GameResults:
    game_token: str
    rounds: List[RoundResult]
    final_score_gpt4o: int
    final_score_o1: int
    total_distance_gpt4o: float = 0
    total_distance_o1: float = 0

    def save_round_results(
        self,
        game_state: geoguessr.GameState,
        round_number: int,
        gpt4o_location: Dict,
        o1_location: Dict,
        actual_score: int,
    ) -> RoundResult:
        """Save the results for a single round, including both models' guesses."""
        actual_coords = game_state.rounds[round_number - 1]

        o1_score = predict_score(
            game_state,
            actual_coords.lat,
            actual_coords.lng,
            o1_location["latitude"],
            o1_location["longitude"],
        )

        # Create location guess objects
        gpt4o_guess = LocationGuess(
            latitude=gpt4o_location["latitude"],
            longitude=gpt4o_location["longitude"],
            score=actual_score,
            distance_km=calculate_distance_km(
                actual_coords.lat,
                actual_coords.lng,
                gpt4o_location["latitude"],
                gpt4o_location["longitude"],
            ),
            explanation=gpt4o_location.get("explanation", ""),
        )

        o1_guess = LocationGuess(
            latitude=o1_location["latitude"],
            longitude=o1_location["longitude"],
            score=o1_score,
            distance_km=calculate_distance_km(
                actual_coords.lat,
                actual_coords.lng,
                o1_location["latitude"],
                o1_location["longitude"],
            ),
            explanation=o1_location.get("explanation", ""),
        )

        round_result = RoundResult(
            round_number=round_number,
            gpt4o_guess=gpt4o_guess,
            o1_guess=o1_guess,
            actual_location=actual_coords,
        )

        self.rounds.append(round_result)
        self.total_distance_gpt4o += gpt4o_guess.distance_km
        self.total_distance_o1 += o1_guess.distance_km

        # Check score prediction
        self._check_score_prediction(
            game_state,
            gpt4o_location["latitude"],
            gpt4o_location["longitude"],
            actual_score,
        )

        return round_result

    def _check_score_prediction(
        self,
        game_state: geoguessr.GameState,
        predicted_lat: float,
        predicted_lng: float,
        actual_score: int,
    ) -> None:
        answer_coords = game_state.rounds[-1]

        predicted_score = predict_score(
            game_state,
            answer_coords.lat,
            answer_coords.lng,
            predicted_lat,
            predicted_lng,
        )

        score_diff = abs(predicted_score - actual_score)

        if score_diff > 1:
            raise ValueError(
                f"Score prediction mismatch! Predicted: {predicted_score}, Actual: {actual_score}"
            )

    def print_last_round(self) -> None:
        """Print the results of the last round."""
        if not self.rounds:
            print("No rounds played yet!")
            return

        last_round = self.rounds[-1]
        print("\n=== Round Results ===")
        print(f"Round {last_round.round_number}")

        print("GPT-4O Guess:")
        print(
            f"Location: {last_round.gpt4o_guess.latitude:.4f}, {last_round.gpt4o_guess.longitude:.4f}"
        )
        print(f"Score: {last_round.gpt4o_guess.score} points")
        print(f"Distance: {last_round.gpt4o_guess.distance_km:.1f} km")
        if last_round.gpt4o_guess.explanation:
            print(f"Explanation: {last_round.gpt4o_guess.explanation}")

        print("\nO1 Guess:")
        print(
            f"Location: {last_round.o1_guess.latitude:.4f}, {last_round.o1_guess.longitude:.4f}"
        )
        print(f"Score: {last_round.o1_guess.score} points")
        print(f"Distance: {last_round.o1_guess.distance_km:.1f} km")
        if last_round.o1_guess.explanation:
            print(f"Explanation: {last_round.o1_guess.explanation}")

        print("==================\n")

    def print_final_score(self) -> None:
        """Print the final scores and statistics for both models."""
        print("\n=== Final Results ===")

        # Print scores
        print("Scores:")
        print(f"GPT-4O: {self.final_score_gpt4o} points")
        print(f"O1: {self.final_score_o1} points")

        # Print total distances
        print("\nTotal Distances:")
        print(f"GPT-4O: {self.total_distance_gpt4o:.1f} km")
        print(f"O1: {self.total_distance_o1:.1f} km")

        # Calculate and print average distances
        gpt4o_avg_dist = self.total_distance_gpt4o / len(self.rounds)
        o1_avg_dist = self.total_distance_o1 / len(self.rounds)
        print("\nAverage Distances:")
        print(f"GPT-4O: {gpt4o_avg_dist:.1f} km")
        print(f"O1: {o1_avg_dist:.1f} km")

        # Find best and worst guesses
        gpt4o_distances = [r.gpt4o_guess.distance_km for r in self.rounds]
        o1_distances = [r.o1_guess.distance_km for r in self.rounds]

        print("\nBest Guesses:")
        print(f"GPT-4O: {min(gpt4o_distances):.1f} km")
        print(f"O1: {min(o1_distances):.1f} km")

        print("\nWorst Guesses:")
        print(f"GPT-4O: {max(gpt4o_distances):.1f} km")
        print(f"O1: {max(o1_distances):.1f} km")
        print("==================\n")


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371.0  # Earth's radius in kilometers

    # Convert to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    # Differences
    dlat = lat2 - lat1
    dlng = lng2 - lng1

    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def predict_score(
    game_state: geoguessr.GameState,
    answer_lat: float,
    answer_lng: float,
    guess_lat: float,
    guess_lng: float,
) -> int:
    """
    Predict the score for a guess at the given coordinates.
    """
    guessed_distance_km = _haversine_distance(
        answer_lat,
        answer_lng,
        guess_lat,
        guess_lng,
    )
    map_size_km = _haversine_distance(
        game_state.bounds.min["lat"],
        game_state.bounds.min["lng"],
        game_state.bounds.max["lat"],
        game_state.bounds.max["lng"],
    )
    score = round(5000 * math.exp(-10 * guessed_distance_km / map_size_km))
    return score


def calculate_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in kilometers."""
    return _haversine_distance(lat1, lng1, lat2, lng2)
