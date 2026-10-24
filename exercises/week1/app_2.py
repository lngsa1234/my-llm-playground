from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.4-mini",
    instructions="You are a helpful AI assistant.",
    input="Explain what an LLM is in two sentences.",
)

print("Generated text:")
print(response.output_text)

print("\nFull API response:")
print(response.model_dump_json(indent=2))
