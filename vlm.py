import json

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
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You will help identify any interesting or unique objects in this image that might help identify it's location.\n\nThe image is 1024x1024 large.\n\nExamples:\n - Any kind of writing on sign boards, vehicles, buildings, road signs, sign posts etc\n - Flags\n- Famous buildings and landmarks\n\nThere can be  0-2 objects in the image.\nThe approximate coordinates should be measured from the top-left of the image.\nReturn an empty list if there are no such objects.",
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
        model="o1",
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
        # temperature=0.30,
    )
    return json.loads(response.choices[0].message.content)  # type: ignore
