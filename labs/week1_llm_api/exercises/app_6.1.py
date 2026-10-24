from openai import OpenAI
from pydantic import BaseModel
from typing import Literal

client = OpenAI()

class CoffeeChatIntent(BaseModel):
    intent: Literal[
        "career_advice",
        "networking",
        "skill_learning",
        "other"
    ]
    topic: str
    looking_for: str
    is_asking_for_connection: bool

response = client.responses.parse(
    model="gpt-5.4-mini",

    instructions=(
        "Analyze Coffee Chat requests. "
        "Extract the user's intent and requirements. "
        "Do not invent information."
    ),

    input=(
        "I'm a software engineer transitioning into "
        "AI product management. I'd love to meet someone "
        "who has already made this transition and learn "
        "about their experience."
    ),

    text_format=CoffeeChatIntent
)

result = response.output_parsed

if result is None:
    raise RuntimeError("No parsed result returned.")

print(result.model_dump_json(indent=2))
print("Intent:", result.intent)
