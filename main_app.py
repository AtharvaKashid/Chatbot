import streamlit as st
from audio_recorder_streamlit import audio_recorder
from groq import Groq
from system_prompt import SYSTEM_PROMPT

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(page_title="XYZ Bank Chatbot", page_icon="🏦", layout="centered")

# Initialize Groq Client securely
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def get_llm_response(messages):
    # Strip internal keys before sending to Groq
    clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=clean_messages,
        temperature=0.2,
        max_tokens=500
    )
    return response.choices[0].message.content

# --------------------------------------------------
# Load External CSS
# --------------------------------------------------
try:
    with open("styles.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass # Fallback if file missing

# --------------------------------------------------
# Initialize Conversation Memory
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT, "internal": True}
    ]

# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown("""
    <div class="chat-container">
        <div class="header">
            <h2>🏦 XYZ Bank Virtual Assistant</h2>
            <p>Secure help for XYZ Bank products and services</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --------------------------------------------------
# Chat Messages UI
# --------------------------------------------------
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg.get("internal"): continue
    
    role_name = "You" if msg["role"] == "user" else "XYZ Bank Assistant"
    css_class = "user-msg" if msg["role"] == "user" else "bot-msg"
    
    st.markdown(f"""
        <div class="{css_class}">
            <div class="role">{role_name}</div>
            {msg["content"]}
        </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# User Input (Text & Voice)
# --------------------------------------------------
st.markdown("---")
col_text, col_voice = st.columns([5, 1])

with col_voice:
    # Browser-based voice input
    audio_bytes = audio_recorder(text="", icon_size="2x")

user_input = col_text.chat_input("Type or use voice...")

if audio_bytes:
    st.warning("Voice capture requires a backend transcription service (e.g., Whisper). Please use text input for now.")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Assistant is typing..."):
        reply = get_llm_response(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# Trim history
if len(st.session_state.messages) > 9:
    st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-8:]
