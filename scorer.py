"""
Geogussr scoring is exponential and depends on the map size, etc.

https://www.reddit.com/r/geoguessr/comments/1cdelb2/can_somebody_help_me_understand_how_geoguesser/l1csyjc/
https://www.reddit.com/r/geoguessr/comments/15koyd6/how_much_close_you_have_to_be_for_5k_score/jvboz87/
https://www.plonkit.net/beginners-guide#:~:text=Scoring,score%20drop%2Doff%20is%20exponential.
"""

import math
from dataclasses import dataclass
from typing import List

import geoguessr
import vlm


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

    def save_round_results(
        self,
        game_state: geoguessr.GameState,
        round_number: int,
        gpt4o_location: vlm.IdentifiedLocation,
        o1_location: vlm.IdentifiedLocation,
        actual_score: int,
    ) -> RoundResult:
        """Save the results for a single round, including both models' guesses."""
        actual_coords = game_state.rounds[round_number - 1]

        o1_score = _calculate_score(
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
            distance_km=_haversine_distance(
                actual_coords.lat,
                actual_coords.lng,
                gpt4o_location["latitude"],
                gpt4o_location["longitude"],
            ),
            explanation=gpt4o_location.get("explanation") or "",
        )

        o1_guess = LocationGuess(
            latitude=o1_location["latitude"],
            longitude=o1_location["longitude"],
            score=o1_score,
            distance_km=_haversine_distance(
                actual_coords.lat,
                actual_coords.lng,
                o1_location["latitude"],
                o1_location["longitude"],
            ),
            explanation=o1_location.get("explanation") or "",
        )

        round_result = RoundResult(
            round_number=round_number,
            gpt4o_guess=gpt4o_guess,
            o1_guess=o1_guess,
            actual_location=actual_coords,
        )

        self.rounds.append(round_result)

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
        """
        This checks that the score we calculate matches the actual score.
        This validates that the scoring function is correct.
        """
        answer_coords = game_state.rounds[-1]

        predicted_score = _calculate_score(
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


def _calculate_score(
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
