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
    stepsCount: int
    time: int


@dataclass
class Player:
    totalScore: Score
    totalDistance: Distance
    totalDistanceInMeters: float
    totalStepsCount: int
    totalTime: int
    guesses: List[Guess]
    id: str


def parse_guess_response(response_text: str) -> Player:
    """Parse the GeoGuessr API response and return the player data."""
    data = json.loads(response_text)
    player_data = data["player"]

    # Convert the JSON data into our dataclass structure
    player = Player(
        totalScore=Score(**player_data["totalScore"]),
        totalDistance=Distance(**player_data["totalDistance"]),
        totalDistanceInMeters=player_data["totalDistanceInMeters"],
        totalStepsCount=player_data["totalStepsCount"],
        totalTime=player_data["totalTime"],
        guesses=[
            Guess(
                lat=g["lat"],
                lng=g["lng"],
                roundScore=Score(**g["roundScore"]),
                roundScoreInPercentage=g["roundScoreInPercentage"],
                roundScoreInPoints=g["roundScoreInPoints"],
                distance=Distance(**g["distance"]),
                distanceInMeters=g["distanceInMeters"],
                stepsCount=g["stepsCount"],
                time=g["time"],
            )
            for g in player_data["guesses"]
        ],
        id=player_data["id"],
    )
    return player


def submit_guess(page: Page, game_token: str, lat: float, lng: float) -> Player:
    print(f"Submitting guess at coordinates: {lat}, {lng}")

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
        headers={
            "accept": "*/*",
            "content-type": "application/json",
            "x-client": "web",
        },
        data=data,
    )

    if not response.ok:
        print(
            f"Failed to submit guess. Status: {response.status}, Response: {response.text()}"
        )
        raise Exception("Failed to submit guess")

    player = parse_guess_response(response.text())
    print(
        f"Successfully submitted guess. Score: {player.totalScore.amount} {player.totalScore.unit}"
    )
    return player
