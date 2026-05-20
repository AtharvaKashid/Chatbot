import os
import uuid
from openai import OpenAI
from arize.otel import register, Transport
from openinference.instrumentation.openai import OpenAIInstrumentor

# ---------------------------------------------------
# 1) Validate Arize environment variables
# ---------------------------------------------------
required_env_vars = ["ARIZE_SPACE_ID", "ARIZE_API_KEY"]
missing = [var for var in required_env_vars if not os.getenv(var)]

if missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing)}"
    )

ARIZE_SPACE_ID = "U3BhY2U6NDA3ODg6emJ2Rw=="
ARIZE_API_KEY = "ak-2381bb4d-2e94-43fe-8c89-f6ba2a56b5b4-_DOpF5ewD-97ThCdZ9plMinRX8uGahZ5"
ARIZE_PROJECT_NAME = os.getenv("ARIZE_PROJECT_NAME", "lmstudio-mistral-chatbot")

# ---------------------------------------------------
# 2) Register Arize tracing using HTTPS/HTTP transport
#    (instead of default gRPC)
# ---------------------------------------------------
tracer_provider = register(
    space_id=ARIZE_SPACE_ID,
    api_key=ARIZE_API_KEY,
    project_name=ARIZE_PROJECT_NAME,
    endpoint="https://otlp.arize.com/v1/traces",
    transport=Transport.HTTP,
    batch=False,          # simpler for debugging
    log_to_console=True,  # helps you see spans locally
)

# ---------------------------------------------------
# 3) Instrument OpenAI SDK
#    LM Studio is OpenAI-compatible, so this is correct
# ---------------------------------------------------
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# ---------------------------------------------------
# 4) Connect to LM Studio local server
# ---------------------------------------------------
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"   # dummy key for LM Studio local server
)

# ---------------------------------------------------
# 5) Exact LM Studio model ID
# ---------------------------------------------------
MODEL_NAME = "mistral-7b-instruct-v0.2"

# ---------------------------------------------------
# 6) Instructions for the chatbot
#    IMPORTANT: Do NOT send these as a system role
#    for this Mistral prompt template.
# ---------------------------------------------------
INSTRUCTION_PREFIX = """
You are XYZ Bank Virtual Assistant.

Rules:
- Answer only questions related to XYZ Bank services.
- Do not provide account balances, OTPs, passwords, PINs, CVVs, or other sensitive information.
- If the user asks something unrelated, politely say that you can help only with XYZ Bank services.
- Keep responses clear, concise, and professional.
"""

# ---------------------------------------------------
# 7) Conversation memory
#    No system role here because this model/template
#    only supports user and assistant.
# ---------------------------------------------------
messages = []

local_session_id = str(uuid.uuid4())

print("=" * 70)
print("LM Studio + Mistral Local Chatbot with Arize Tracing")
print(f"Local Session ID : {local_session_id}")
print(f"Arize Project    : {ARIZE_PROJECT_NAME}")
print(f"LM Studio URL    : http://localhost:1234/v1")
print(f"Chat Model       : {MODEL_NAME}")
print("Type 'exit' or 'quit' to stop.")
print("=" * 70)

first_turn = True

# ---------------------------------------------------
# 8) Interactive chat loop
# ---------------------------------------------------
while True:
    user_query = input("\nYou: ").strip()

    if user_query.lower() in {"exit", "quit"}:
        print("Exiting chatbot. Goodbye!")
        break

    if not user_query:
        print("Please enter a valid query.")
        continue

    # For the first turn, merge instructions into the user message
    if first_turn:
        merged_user_query = f"{INSTRUCTION_PREFIX}\n\nUser question: {user_query}"
        first_turn = False
    else:
        merged_user_query = user_query

    messages.append({"role": "user", "content": merged_user_query})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
            max_tokens=512,
            stream=False
        )

        assistant_reply = response.choices[0].message.content or ""
        print(f"Bot: {assistant_reply}")

        messages.append({"role": "assistant", "content": assistant_reply})

    except Exception as e:
        print(f"Error while generating response: {e}")