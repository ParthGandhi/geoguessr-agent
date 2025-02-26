import json

from openai import OpenAI
from typing_extensions import TypedDict

client = OpenAI()


class InterestingObject(TypedDict):
    name: str
    x: int
    y: int


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
    return json.loads(response.choices[0].message.content)['objects']  # type: ignore
