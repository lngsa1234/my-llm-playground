from openai import OpenAI

client = OpenAI()

# Keep the user prompt unchanged.
user_prompt = "Explain what an LLM is."

# Test three different system instructions.
instructions_list = [
    "You are a helpful AI assistant.",
    "You are a patient teacher. Explain concepts using simple language and everyday analogies.",
    "You are an ML engineer. Explain concepts using precise technical terminology."
]

for i, instructions in enumerate(instructions_list, start=1):
    response = client.responses.create(
        model="gpt-5.4-mini",
        instructions=instructions,
        input=user_prompt,
        max_output_tokens=500
    )

    print(f"\n{'=' * 60}")
    print(f"EXPERIMENT {i}")
    print(f"{'=' * 60}")

    print("\nSystem instructions:")
    print(instructions)

    print("\nUser prompt:")
    print(user_prompt)

    print("\nModel response:")
    print(response.output_text or "[No visible text returned]")

    print("\nStatus:", response.status)
    print("Input tokens:", response.usage.input_tokens)
    print("Output tokens:", response.usage.output_tokens)
