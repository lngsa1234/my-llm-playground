from openai import OpenAI

client = OpenAI()

model = "gpt-5.4-mini"

system_instructions = (
    "You are a career advisor. "
    "Provide concise, practical advice."
)

current_question = (
    "Enterprise AI products. "
    "What skills should I develop?"
)

# --------------------------------------------------
# Experiment 1: WITH conversation history
# --------------------------------------------------

response_with_history = client.responses.create(
    model=model,
    instructions=system_instructions,
    input=[
        {
            "role": "user",
            "content": (
                "I am a software engineer interested in "
                "transitioning into AI product management."
            )
        },
        {
            "role": "assistant",
            "content": (
                "Your engineering background could help. "
                "What type of AI products interest you?"
            )
        },
        {
            "role": "user",
            "content": current_question
        }
    ],
    max_output_tokens=500
)

print("\n" + "=" * 60)
print("EXPERIMENT 1: WITH CONVERSATION HISTORY")
print("=" * 60)

print(response_with_history.output_text)
print("Status:", response_with_history.status)
print("Input tokens:", response_with_history.usage.input_tokens)
print("Output tokens:", response_with_history.usage.output_tokens)


# --------------------------------------------------
# Experiment 2: WITHOUT conversation history
# --------------------------------------------------

response_without_history = client.responses.create(
    model=model,
    instructions=system_instructions,
    input=current_question,
    max_output_tokens=500
)

print("\n" + "=" * 60)
print("EXPERIMENT 2: WITHOUT CONVERSATION HISTORY")
print("=" * 60)

print(response_without_history.output_text)
print("Status:", response_without_history.status)
print("Input tokens:", response_without_history.usage.input_tokens)
print("Output tokens:", response_without_history.usage.output_tokens)
