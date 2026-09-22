
from openai import OpenAI

client = OpenAI()

model = "gpt-5.4-mini"

# Three prompts with different requested response lengths.
prompts = [
    "What is an LLM?",

    "Explain what an LLM is in 200 words.",

    "Explain what an LLM is in 1,000 words, "
    "including examples."
]

for i, prompt in enumerate(prompts, start=1):

    response = client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=2500
    )

    print(f"\n{'=' * 60}")
    print(f"EXPERIMENT {i}")
    print(f"{'=' * 60}")

    print("\nPrompt:")
    print(prompt)

    print("\nModel response:")
    print(response.output_text or "[No visible text returned]")

    print("\n--- TOKEN USAGE ---")
    print("Input tokens:", response.usage.input_tokens)
    print("Output tokens:", response.usage.output_tokens)
    print("Total tokens:", response.usage.total_tokens)

    print("Status:", response.status)
    print("Incomplete details:", response.incomplete_details)
