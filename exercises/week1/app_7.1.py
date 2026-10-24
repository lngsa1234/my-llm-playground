import time
from openai import OpenAI

client = OpenAI()

start = time.perf_counter()

response = client.responses.create(
    model="gpt-5.4-mini",
    input="Explain what an LLM is."
)

latency = time.perf_counter() - start

input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens

print("Response:", response.output_text)
print("Latency:", round(latency, 2), "seconds")
print("Input tokens:", input_tokens)
print("Output tokens:", output_tokens)
