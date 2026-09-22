
from openai import OpenAI

client = OpenAI()

prompt = (
    "Explain the difference between an LLM and an AI agent "
    "in detail, including examples."
)

# Test different output-token limits.
for limit in [100, 300, 800]:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
        max_output_tokens=limit
    )

    print(f"\n{'=' * 50}")
    print(f"MAX OUTPUT TOKENS: {limit}")
    print(f"{'=' * 50}")

    print("Status:", response.status)
    print("Output tokens:", response.usage.output_tokens)
    print("Incomplete details:", response.incomplete_details)

    print("\nModel response:")
    print(response.output_text or "[No visible text returned]")
