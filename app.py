import os
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from groq import Groq
from system_prompt import SYSTEM_PROMPT

# --------------------------------------------------
# Arize Enterprise Tracing Setup (arize-otel)
# --------------------------------------------------
from arize.otel import register
from openinference.instrumentation.groq import GroqInstrumentor

# Load environment keys securely from Streamlit secrets
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

# Check if Arize credentials exist before registering the tracer provider
if "ARIZE_SPACE_ID" in st.secrets and "ARIZE_API_KEY" in st.secrets:
    tracer_provider = register(
        space_id=st.secrets["ARIZE_SPACE_ID"],
        api_key=st.secrets["ARIZE_API_KEY"],
        project_name="xyz-bank-live-chatbot"  # Becomes your Model ID inside Arize AX
    )
    # Bind the auto-instrumentation to catch all Groq client calls (Chat & Audio)
    GroqInstrumentor().instrument(tracer_provider=tracer_provider)
else:
    st.warning("Telemetry Warning: Arize credentials missing from st.secrets. Operating without live tracing.")

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(page_title="XYZ Bank Chatbot", page_icon="🏦", layout="centered")

# Initialize Groq Client securely
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def get_llm_response(messages):
    # Strip internal keys before sending to Groq
    clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    # This specific call will be automatically tracked by the OpenInference SDK
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=clean_messages,
        temperature=0.2,
        max_tokens=500
    )
    return response.choices[0].message.content

def transcribe_audio(audio_bytes):
    """Transcribes raw audio bytes into text using Groq's Whisper API"""
    try:
        # Save audio bytes temporarily to pass to the API
        temp_filename = "temp_audio.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
        
        # Call Groq Audio Transcription API
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(temp_filename, audio_file.read()),
                model="distil-whisper-large-v3-en",  # High-speed Whisper model on Groq
                response_format="text"
            )
        
        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return transcription.strip()
    except Exception as e:
        st.error(f"Transcription Error: {str(e)}")
        return None

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

# Keep track of processed audio chunks to prevent dynamic rerun processing loops
if "last_audio_md5" not in st.session_state:
    st.session_state.last_audio_md5 = None

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
# User Input (Text & Voice Processing)
# --------------------------------------------------
st.markdown("---")
col_text, col_voice = st.columns([5, 1])

with col_voice:
    # Browser-based voice input
    audio_bytes = audio_recorder(text="", icon_size="2x")

user_input = col_text.chat_input("Type or use voice...")

# Check if a NEW voice message has been recorded
if audio_bytes:
    current_audio_hash = hash(audio_bytes)
    if st.session_state.last_audio_md5 != current_audio_hash:
        st.session_state.last_audio_md5 = current_audio_hash
        
        with st.spinner("Transcribing audio..."):
            transcribed_text = transcribe_audio(audio_bytes)
            
        if transcribed_text:
            user_input = transcribed_text  # Route the voice transcript into the processing block

# Process User Input (Whether it came via text box or voice transcription)
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Assistant is typing..."):
        reply = get_llm_response(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# Trim history
if len(st.session_state.messages) > 9:
    st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-8:]
