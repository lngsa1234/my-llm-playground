# Week 1 · LLM Fundamentals — Lab: Build Your First LLM Application

**A quick note: This is a voluntary, self-paced learning circle. There's no pressure to complete every exercise or keep up with everyone else. Do what you can, learn at your own pace, and most importantly, have fun exploring AI together! 😊**

In Week 1, we will build a simple LLM application and use it to understand how an application communicates with a language model. We will experiment with API parameters, messages, tokens, structured output, latency, and cost.

The goal is not just to make an API call. It's to understand what happens during that call and how application design affects the model's behavior.

## Week 1 learning objectives: understand the LLM API lifecycle

By the end of the lab, participants will be able to:

- Send API requests and interpret responses.
- Model parameters and their effects
- Distinguish system instructions from user messages.
- Generate and validate structured JSON output.
- Experiment with supported model parameters.
- Measure latency, track token usage, and estimate API cost.

**Recommended duration**: 90–120 minutes for the core lab, plus optional web UI development.

**Prerequisites**: Basic Python or JavaScript, a local development environment, Git, a GitHub account, and an OpenAI API key.

## 1. What you will build

A simple LLM Playground with configurable inputs and measurable outputs.

> 🖼️ *Illustrative application mockup* — [view in Notion](https://app.notion.com/p/3e0dbc95f92c80a18bb0d7c6040fcf57)

Interface mockup with illustrative metrics, not a live API connection.

The basic version will display these results in the terminal. Participants who want an additional challenge can build the web version ([Lab extension: Build a web demo](lab-web-demo.md)).

## Part 1 — Understand the architecture

Before writing code, understand where the LLM sits in your application.

> 🖼️ *Diagram: application → API → model* — [view in Notion](https://app.notion.com/p/3e0dbc95f92c80a18bb0d7c6040fcf57)

The application calls an API that exposes the model. It does not directly execute the model's neural-network weights.

# Part A — Core lab (Python or JavaScript)

## Step 1. Set up your project

Participants can choose either language. Both implementations should produce equivalent results.

### Python track

Create your project:

```bash
mkdir my-llm-python
cd my-llm-python

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade openai pydantic
```

On Windows, use the appropriate virtual-environment activation command.

Create a file named `app.py`.

### JavaScript track

Create your project:

```bash
mkdir my-llm-js
cd my-llm-js

npm init -y
npm install openai zod
```

Create a file named `app.mjs`.

Create an API key at [OpenAI Platform](https://platform.openai.com/api-keys), and set it in your terminal:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Remember to add credit to your account. API use is billed separately from a monthly subscription plan.

Use a model available to your API project. The examples below use `gpt-5.4-mini`; replace that model ID if necessary. Check the [OpenAI model documentation](https://platform.openai.com/docs/models) for availability and supported parameters.

## Step 2. Send your first API request

Objective 1: API requests and responses

The first experiment should send a prompt and print the full API response, not just the generated text.

Python

```python
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
```

Run using `python3 app.py`.

JavaScript

```javascript
import OpenAI from "openai";

const client = new OpenAI();

const response = await client.responses.create({
  model: "gpt-5.4-mini",
  instructions: "You are a helpful AI assistant.",
  input: "Explain what an LLM is in two sentences.",
});

console.log("Generated text:");
console.log(response.output_text);

console.log("\nFull API response:");
console.log(JSON.stringify(response, null, 2));
```

Run using `node app.mjs`.

Inspect the response and find the following fields:

| Field | Meaning |
| --- | --- |
| `id` | Unique identifier for the response. |
| `model` | Model used to generate the response. |
| `status` | Processing status of the response. |
| `output` | Structured list of generated output items. |
| `output_text` | SDK convenience property for the generated text. |
| `usage` | Token usage information. |

Discussion: Why does the API return a structured response object rather than only a string?

# Step 3 — Understand model parameters

Objective: Configure an LLM API request

An API request contains configuration parameters and the content you want the model to process.

## 3.1 Anatomy of a request

```python
response = client.responses.create(
    model="gpt-5.4-mini",
    instructions="You are a helpful assistant.",
    input="Explain what an LLM is.",
    max_output_tokens=500
)
```

| Parameter | Purpose |
| --- | --- |
| `model` | Selects the model |
| `instructions` | Defines higher-priority behavior |
| `input` | Supplies the user request and optional history |
| `max_output_tokens` | Limits generated tokens, including reasoning tokens where applicable |
| `temperature` | Controls sampling randomness, if supported |
| `top_p` | Controls nucleus sampling, if supported |
| `reasoning.effort` | Configures reasoning effort on supported models |

Not every model supports every parameter. For example, some reasoning models do not accept custom temperature or top-p settings.

## 3.2 Experiment A — Output-token limit

Run the same prompt with different output-token limits.

```python
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
```

Observe whether the response is complete. An output limit is a ceiling, not a request to generate exactly that many tokens.

Think about:

1. **The model can generate up to the maximum number of output tokens, but that does not guarantee a complete answer.**
2. **Can you ask the model to finish within 100 tokens?**

# Step 4 — System, user, and assistant messages

Objective: Understand conversation structure

Now we will examine how an API request represents a conversation.

## 4.1 Message roles

| Role | Meaning |
| --- | --- |
| `system` | High-priority instructions |
| `developer` | Application-level instructions |
| `user` | User-provided request or content |
| `assistant` | Previous assistant output |

The API infrastructure encodes these roles into the model's input representation. The model has been trained to interpret the role markers and content.

## 4.2 Experiment A — System instructions versus user input

Use the same user prompt with different instructions.

Python

```python
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
```

JavaScript

```javascript
const instructionsList = [
  "You are a helpful assistant.",
  "You are a patient teacher. Use simple analogies.",
  "You are an ML engineer. Use technical terminology."
];

for (const instructions of instructionsList) {
  const response = await client.responses.create({
    model: "gpt-5.4-mini",
    instructions,
    input: "Explain what an LLM is."
  });

  console.log("\nInstructions:", instructions);
  console.log(response.output_text);
}
```

Observe how the answer changes even though the user request stays the same.

## 4.3 Experiment B — Add conversation history

Python

```python
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
```

JavaScript

```javascript
const response = await client.responses.create({
  model: "gpt-5.4-mini",

  instructions:
    "You are a career advisor. " +
    "Provide concise, practical advice.",

  input: [
    {
      role: "user",
      content:
        "I am a software engineer interested in " +
        "transitioning into AI product management."
    },
    {
      role: "assistant",
      content:
        "Your engineering background could help. " +
        "What type of AI products interest you?"
    },
    {
      role: "user",
      content:
        "Enterprise AI products. " +
        "What skills should I develop?"
    }
  ]
});

console.log(response.output_text);
```

Now remove the first two messages and run the final user prompt alone.

Discussion: How does the response change when the model no longer receives the user's professional background?

### Does the LLM remember previous API calls?

Not inherently. In this experiment, the application explicitly supplies the conversation history in the current request.

The Responses API also supports managed conversation state, such as `previous_response_id`. That can link requests without manually resending every message, but it does not give the model unlimited memory.

# Step 5 — Tokens and context windows

Objective: Understand token usage and context limits

A token is a unit of text or other content represented in the model's input or output. Tokens are not equivalent to words.

## 5.1 Measure token usage

Python

```python
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
```

```python
response = client.responses.create(
    model="gpt-5.4-mini",
    input="Explain what an LLM is."
)

print("Input tokens:", response.usage.input_tokens)
print("Output tokens:", response.usage.output_tokens)
print("Total tokens:", response.usage.total_tokens)
```

Run three prompts:

| Test | Prompt |
| --- | --- |
| A | What is an LLM? |
| B | Explain what an LLM is in 200 words. |
| C | Explain what an LLM is in 1,000 words, including examples. |

Record the actual input and output token counts.

## 5.2 Understand the context window

A context window limits the amount of tokenized information a model can process in an inference.

It may include system instructions, user messages, previous assistant messages, retrieved documents, and other supplied context. The output budget also needs to be considered.

> 🖼️ *Diagram: what fills a context window* — [view in Notion](https://app.notion.com/p/3e0dbc95f92c80a18bb0d7c6040fcf57)

Discussion: What happens if an application keeps appending conversation history? How could it reduce the amount of context without losing important information?

This question leads directly into Week 2: Context Engineering.

# Step 6 — Generate structured output

Objective: Convert natural language into structured JSON

For this experiment, we will build a Coffee Chat Intent Analyzer.

A user submits:

> I'm a software engineer transitioning into AI product management. I'd love to meet someone who has already made this transition and learn about their experience.

The application should extract predictable fields.

```json
{
  "intent": "career_advice",
  "topic": "Transitioning to AI product management",
  "looking_for": "Someone who has made a similar transition",
  "is_asking_for_connection": true
}
```

## 6.1 Define the schema and call the API

Python

```python
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
```

JavaScript

```javascript
import OpenAI from "openai";
import { z } from "zod";
import { zodTextFormat } from "openai/helpers/zod";

const client = new OpenAI();

const CoffeeChatIntent = z.object({
  intent: z.enum([
    "career_advice",
    "networking",
    "skill_learning",
    "other"
  ]),
  topic: z.string(),
  looking_for: z.string(),
  is_asking_for_connection: z.boolean()
});

const response = await client.responses.parse({
  model: "gpt-5.4-mini",

  instructions:
    "Analyze Coffee Chat requests. " +
    "Extract the user's intent and requirements. " +
    "Do not invent information.",

  input:
    "I'm a software engineer transitioning into " +
    "AI product management. I'd love to meet someone " +
    "who has already made this transition and learn " +
    "about their experience.",

  text: {
    format: zodTextFormat(
      CoffeeChatIntent,
      "coffee_chat_intent"
    )
  }
});

const result = response.output_parsed;

if (!result) {
  throw new Error("No parsed result returned.");
}

console.log(JSON.stringify(result, null, 2));
console.log("Intent:", result.intent);
```

## 6.2 Test different inputs

### Structured output exercises

> 🖼️ *Table: structured output test inputs* — [view in Notion](https://app.notion.com/p/3e0dbc95f92c80a18bb0d7c6040fcf57)

Observe how the model classifies each request. Pay particular attention to the ambiguous case: does the schema force the model to invent information, or can it represent uncertainty?

Discussion: Why is structured output useful when an LLM needs to communicate with another software component? Does valid JSON guarantee correct information?

# Step 7 — Measure latency and cost

Objective: Understand LLM performance and economics

An LLM API call consumes time and billable resources. We will measure both.

## 7.1 Measure request latency

Python

```python
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
```

JavaScript

```javascript
import OpenAI from "openai";
import { performance } from "node:perf_hooks";

const client = new OpenAI();

const start = performance.now();

const response = await client.responses.create({
  model: "gpt-5.4-mini",
  input: "Explain what an LLM is."
});

const latency = (performance.now() - start) / 1000;

const inputTokens = response.usage.input_tokens;
const outputTokens = response.usage.output_tokens;

console.log("Response:", response.output_text);
console.log("Latency:", latency.toFixed(2), "seconds");
console.log("Input tokens:", inputTokens);
console.log("Output tokens:", outputTokens);
```

This measures end-to-end request latency, including network and API processing time, rather than pure neural-network inference time.

## 7.2 Estimate API cost

Look up the current input and output prices for your selected model on the [OpenAI API pricing page](https://openai.com/api/pricing/).

For standard uncached token pricing:

```text
cost = (T_input × P_input + T_output × P_output) / 1,000,000
```

Where T is the token count and P is the corresponding price per million tokens.

For this exercise, record the estimated cost of three requests. Actual billing may differ when cached tokens, tools, or other pricing categories apply.

## 7.3 Record your observations

| Test | Input tokens | Output tokens | Latency | Estimated cost |
| --- | --- | --- | --- | --- |
| Short prompt | — | — | — | — |
| Long prompt | — | — | — | — |
| Different model | — | — | — | — |

Discussion: Why can two requests with similar token counts have different latency? How would cost change if an application handled 10,000 requests per day?

## Week 1 deliverables

### Completion checklist

> 🖼️ *Week 1 completion checklist* — [view in Notion](https://app.notion.com/p/3e0dbc95f92c80a18bb0d7c6040fcf57)

## Final discussion

Each participant should be able to explain the following sequence in their own words:

Application → API request → Model input and tokens → LLM inference → API response → Application output

They should also understand that the application controls the request configuration and constructs the context, while the LLM processes the supplied information to generate a response.

In Week 2, we will build on this foundation by adding context construction, conversation-history management, and persistent application state.


## 🧩 This week's Mini Muse step

🧠 Understand: turn a request into structured fields. To try it, switch this week's page in the app to **🧩 Build Mini Muse**. The code, what to try and questions to check yourself are in the [Mini Muse guide](../mini-muse.md#week-1---understand--structured-output).
