import streamlit as st
import speech_recognition as sr
from lmstudio_chatbot import get_llm_response
from system_prompt import SYSTEM_PROMPT

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="XYZ Bank Chatbot",
    page_icon="🏦",
    layout="centered"
)

# --------------------------------------------------
# Load External CSS
# --------------------------------------------------
def load_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("styles.css")

# --------------------------------------------------
# Voice Input Function
# --------------------------------------------------
def get_voice_input():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        st.info("🎤 Listening… Please speak clearly")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.listen(
            source,
            timeout=5,
            phrase_time_limit=15
        )

    try:
        return recognizer.recognize_google(audio)
    except (sr.UnknownValueError, sr.RequestError):
        return None

# --------------------------------------------------
# Initialize Conversation Memory (Groq‑Compatible)
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",     # ✅ Groq supports system role
            "content": SYSTEM_PROMPT,
            "internal": True      # hidden from UI
        }
    ]

# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown(
    """
    <div class="chat-container">
        <div class="header">
            <h2>🏦 XYZ Bank Virtual Assistant</h2>
            <p>Secure help for XYZ Bank products and services</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# Chat Messages UI
# --------------------------------------------------
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg.get("internal"):
        continue

    if msg["role"] == "user":
        st.markdown(
            f"""
            <div class="user-msg">
                <div class="role">You</div>
                {msg["content"]}
            </div>
            """,
            unsafe_allow_html=True
        )

    elif msg["role"] == "assistant":
        st.markdown(
            f"""
            <div class="bot-msg">
                <div class="role">XYZ Bank Assistant</div>
                {msg["content"]}
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# User Input
# --------------------------------------------------
st.markdown("---")

col_text, col_voice = st.columns([5, 1])

with col_text:
    user_input = st.chat_input(
        "Type or use voice to ask about XYZ Bank services..."
    )

with col_voice:
    voice_clicked = st.button("🎙️", help="Speak to the assistant")

if voice_clicked:
    voice_text = get_voice_input()
    if voice_text:
        user_input = voice_text
        st.success(f"🗣️ You said: {voice_text}")
    else:
        st.warning("Could not understand audio. Try again.")

# --------------------------------------------------
# Handle User Message
# --------------------------------------------------
if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.spinner("XYZ Bank Assistant is typing..."):
        reply = get_llm_response(st.session_state.messages)

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    # ✅ Trim history safely
    MAX_MESSAGES = 8
    if len(st.session_state.messages) > MAX_MESSAGES:
        st.session_state.messages = (
            st.session_state.messages[:1] +   # keep system prompt
            st.session_state.messages[-7:]
        )

    st.rerun()