"""
Geogussr scoring is exponential and depends on the map size, etc.

https://www.reddit.com/r/geoguessr/comments/1cdelb2/can_somebody_help_me_understand_how_geoguesser/l1csyjc/
https://www.reddit.com/r/geoguessr/comments/15koyd6/how_much_close_you_have_to_be_for_5k_score/jvboz87/
https://www.plonkit.net/beginners-guide#:~:text=Scoring,score%20drop%2Doff%20is%20exponential.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List

import geoguessr
from vlm import IdentifiedLocation


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

    def _create_location_guess(
        self,
        location: IdentifiedLocation,
        game_state: geoguessr.GameState,
        actual_coords: geoguessr.Round,
    ) -> LocationGuess:
        """Create a LocationGuess with score and distance calculations."""
        distance = _haversine_distance(
            actual_coords.lat,
            actual_coords.lng,
            location["latitude"],
            location["longitude"],
        )

        score = _calculate_score(
            game_state,
            actual_coords.lat,
            actual_coords.lng,
            location["latitude"],
            location["longitude"],
        )

        return LocationGuess(
            latitude=location["latitude"],
            longitude=location["longitude"],
            score=score,
            distance_km=distance,
            explanation=str(location.get("explanation", "")),
        )

    def save_round_results(
        self,
        game_state: geoguessr.GameState,
        round_number: int,
        gpt4o_location: IdentifiedLocation,
        o1_location: IdentifiedLocation,
        actual_gpt4o_score: int,
    ) -> RoundResult:
        """Save the results for a single round, including both models' guesses with and without zoom."""
        actual_coords = game_state.rounds[round_number - 1]

        # Create location guesses
        gpt4o_guess = self._create_location_guess(
            gpt4o_location, game_state, actual_coords
        )

        # Validate GPT-4o score matches what we calculate
        if abs(gpt4o_guess.score - actual_gpt4o_score) > 1:
            raise ValueError(
                f"GPT-4o score mismatch! Calculated: {gpt4o_guess.score}, Actual: {actual_gpt4o_score}"
            )

        o1_guess = self._create_location_guess(o1_location, game_state, actual_coords)
        round_result = RoundResult(
            round_number=round_number,
            gpt4o_guess=gpt4o_guess,
            o1_guess=o1_guess,
            actual_location=actual_coords,
        )

        self.rounds.append(round_result)
        return round_result


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
