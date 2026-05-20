import streamlit as st
from groq import Groq

# Access the API key from Streamlit secrets
# st.secrets automatically looks for .streamlit/secrets.toml locally
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def sanitize_messages(messages):
    return [
        {
            "role": m["role"],
            "content": m["content"]
        }
        for m in messages
    ]

def get_llm_response(messages):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=sanitize_messages(messages),
        temperature=0.2,
        max_tokens=200
    )
    return response.choices[0].message.content