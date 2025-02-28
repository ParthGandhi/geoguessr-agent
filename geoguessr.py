import json
from dataclasses import dataclass
from typing import List

from playwright.sync_api import Page


@dataclass
class Score:
    amount: str
    unit: str
    percentage: float


@dataclass
class Distance:
    meters: dict  # {"amount": "xxx", "unit": "km"}
    miles: dict  # {"amount": "xxx", "unit": "miles"}


@dataclass
class Guess:
    lat: float
    lng: float
    roundScore: Score
    roundScoreInPercentage: float
    roundScoreInPoints: int
    distance: Distance
    distanceInMeters: float


@dataclass
class Player:
    totalScore: Score
    totalDistance: Distance
    totalDistanceInMeters: float
    guesses: List[Guess]


@dataclass
class Round:
    lat: float
    lng: float


@dataclass
class Bounds:
    min: dict  # {"lat": float, "lng": float}
    max: dict  # {"lat": float, "lng": float}


@dataclass
class GameState:
    token: str
    player: Player
    rounds: List[Round]
    bounds: Bounds


def _parse_game_state(response_text: str) -> GameState:
    """
    Parses the game state response into a GameState object.
    Only includes token, player data, and rounds information.
    """
    data = json.loads(response_text)

    # Parse player data
    player_data = data["player"]
    player = Player(
        totalScore=Score(**player_data["totalScore"]),
        totalDistance=Distance(**player_data["totalDistance"]),
        totalDistanceInMeters=player_data["totalDistanceInMeters"],
        guesses=[
            Guess(
                lat=g["lat"],
                lng=g["lng"],
                roundScore=Score(**g["roundScore"]),
                roundScoreInPercentage=g["roundScoreInPercentage"],
                roundScoreInPoints=g["roundScoreInPoints"],
                distance=Distance(**g["distance"]),
                distanceInMeters=g["distanceInMeters"],
            )
            for g in player_data["guesses"]
        ],
    )

    rounds = [Round(lat=r["lat"], lng=r["lng"]) for r in data["rounds"]]
    bounds = Bounds(**data["bounds"])

    return GameState(
        token=data["token"],
        player=player,
        rounds=rounds,
        bounds=bounds,
    )


def submit_guess(page: Page, game_token: str, lat: float, lng: float) -> GameState:
    print(f"Submitting guess for {game_token=} at {lat=}, {lng=}")

    api_context = page.request
    data = {
        "token": game_token,
        "lat": lat,
        "lng": lng,
        "timedOut": False,
        "stepsCount": 0,
    }

    response = api_context.post(
        f"https://www.geoguessr.com/api/v3/games/{game_token}",
        data=data,
    )

    if not response.ok:
        raise Exception(
            f"Failed to get game state. Status: {response.status}, Response: {response.text()}"
        )

    game_state = _parse_game_state(response.text())
    return game_state


def get_game_state(page: Page, game_token: str) -> GameState:
    api_context = page.request
    response = api_context.get(
        f"https://www.geoguessr.com/api/v3/games/{game_token}",
    )
    if not response.ok:
        raise Exception(
            f"Failed to get game state. Status: {response.status}, Response: {response.text()}"
        )

    game_state = _parse_game_state(response.text())
    return game_state


def start_new_game(page: Page) -> str:
    print("Starting new game")

    settings = {
        "map": "world",
        "type": "standard",
        "timeLimit": 0,
        "forbidMoving": True,
        "forbidZooming": False,
        "forbidRotating": False,
    }

    api_context = page.request
    response = api_context.post(
        "https://www.geoguessr.com/api/v3/games",
        data=settings,
    )

    if not response.ok:
        raise Exception(
            f"Failed to start game. Status: {response.status}, Response: {response.text()}"
        )

    game_token = response.json()["token"]
    print(f"Started new game with {game_token=}")
    return game_token
