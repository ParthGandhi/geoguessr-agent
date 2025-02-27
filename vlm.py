import json
import math
from typing import List

from openai import OpenAI
from typing_extensions import TypedDict

client = OpenAI()


class InterestingObject(TypedDict):
    name: str
    x: int
    y: int


class IdentifiedLocation(TypedDict):
    explanation: str
    country: str
    region: str
    latitude: float
    longitude: float


def identify_objects(image_base64: str) -> list[InterestingObject]:
    prompt = """You are an assistant designed to analyze screenshots from the game Geoguessr, which uses Google Maps imagery. Your task is to identify unique or interesting objects in these images that could help determine the location where the screenshot was taken.

Please follow these steps to analyze the image:

1. Carefully examine the 1024x1024 pixel image for any unique or interesting objects.
2. Focus on identifying the following types of objects:
   - Text on signs, vehicles, buildings, road signs, or sign posts
   - Flags
   - Famous buildings or landmarks
   - Other distinctive and unique objects.
3. Determine if there are 0, 1, or 2 such objects in the image. If there are more than 2, select the 2 most distinctive or informative objects.
4. For each identified object (up to 2):
   a. Provide a brief description of the object.
   b. Determine its approximate coordinates, measured from the top-left corner of the image.
5. Format your findings according to the output structure provided below.
6. If no unique or interesting objects are found, return an empty list.

Please proceed with your analysis and provide the final output."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    }
                ],
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "object_list",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "objects": {
                            "type": "array",
                            "description": "A list of objects with names and coordinates.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the object.",
                                    },
                                    "x": {
                                        "type": "number",
                                        "description": "The x coordinate of the object.",
                                    },
                                    "y": {
                                        "type": "number",
                                        "description": "The y coordinate of the object.",
                                    },
                                },
                                "required": ["name", "x", "y"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["objects"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.content)["objects"]  # type: ignore


def identify_location(images_base64: list[str]) -> IdentifiedLocation:
    if len(images_base64) < 3:
        raise ValueError(f"At least 3 images are required, got: {len(images_base64)}")

    prompt = """You will be given images from the game GeoGuessr. Your task is to analyze these images and determine the most likely location where they were taken.

Carefully analyze each image, paying close attention to the following elements:
1. Landscape and scenery
2. Types of plants and animals
3. Architecture and building styles
4. Vehicles, transportation methods, and which side of the road they are on
5. Road signs, street names, and other written information
6. Cultural indicators (clothing, flags, monuments)
7. Climate and weather conditions

Remember to base your analysis solely on the information provided in the images."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    }
                    for image_base64 in images_base64
                ],
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "latitude_longitude",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "explanation": {
                            "type": "string",
                            "description": "A detailed analysis of the images and the facts from there leading to the final answer",
                        },
                        "country": {
                            "type": "string",
                            "description": "The country name",
                        },
                        "region": {"type": "string", "description": "The region name"},
                        "latitude": {
                            "type": "number",
                            "description": "The latitude coordinate, which represents the north-south position on the Earth's surface.",
                        },
                        "longitude": {
                            "type": "number",
                            "description": "The longitude coordinate, which represents the east-west position on the Earth's surface.",
                        },
                    },
                    "required": [
                        "explanation",
                        "country",
                        "region",
                        "latitude",
                        "longitude",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0.30,
    )
    return json.loads(response.choices[0].message.content)  # type: ignore


def deduplicate_interesting_objects(
    objects: List[InterestingObject],
) -> List[InterestingObject]:
    """
    Sometimes the object detection returns multiple items for the same object or objects very close to each other.
    In either case, we need to only zoom in once to see what we need.
    """
    if not objects:
        return objects

    picked_objects: List[InterestingObject] = []
    for obj in objects:
        # Check if this object is too close to any already kept object
        is_duplicate = False
        for picked_obj in picked_objects:
            distance = math.dist(
                (obj["x"], obj["y"]), (picked_obj["x"], picked_obj["y"])
            )
            if distance < 250:
                is_duplicate = True
                break

        if not is_duplicate:
            picked_objects.append(obj)

    print(f"Deduplicated {len(objects)} objects to {len(picked_objects)}")
    return picked_objects
