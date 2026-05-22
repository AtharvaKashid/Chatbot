import os
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from groq import Groq
from system_prompt import SYSTEM_PROMPT

# --------------------------------------------------
# Arize Enterprise Tracing Setup (Fixed Initialization)
# --------------------------------------------------
from arize.otel import register
from openinference.instrumentation.groq import GroqInstrumentor

# 1. Safely inject environment variables first
if "GROQ_API_KEY" in st.secrets:
    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

# 2. Use st.cache_resource to ensure tracing initializes EXACTLY ONCE across the entire deployment
@st.cache_resource
def initialize_telemetry():
    if "ARIZE_SPACE_ID" in st.secrets and "ARIZE_API_KEY" in st.secrets:
        try:
            tracer_provider = register(
                space_id=st.secrets["ARIZE_SPACE_ID"],
                api_key=st.secrets["ARIZE_API_KEY"],
                project_name="xyz-bank-live-chatbot"  # This creates your project/Model ID in Arize
            )
            # Instrument the Groq SDK to the global OpenTelemetry tracer provider
            GroqInstrumentor().instrument(tracer_provider=tracer_provider)
            return True
        except Exception as e:
            return f"Telemetry Initialization Error: {str(e)}"
    return "Telemetry Warning: Arize credentials missing from st.secrets."

# Run telemetry setup
telemetry_status = initialize_telemetry()
if telemetry_status is not True:
    st.warning(telemetry_status)

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(page_title="XYZ Bank Chatbot", page_icon="🏦", layout="centered")

# Initialize Groq Client securely (Ensure key exists to prevent initialization crashes)
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("Missing GROQ_API_KEY in Streamlit Secrets!")
    st.stop()

def get_llm_response(messages):
    # Strip internal keys before sending to Groq
    clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    # This specific call will be automatically tracked by Arize via OpenInference
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
        temp_filename = "temp_audio.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
        
        with open(temp_filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(temp_filename, audio_file.read()),
                model="distil-whisper-large-v3-en",
                response_format="text"
            )
        
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
    pass 

# --------------------------------------------------
# Initialize Conversation Memory
# --------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT, "internal": True}
    ]

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
    audio_bytes = audio_recorder(text="", icon_size="2x")

user_input = col_text.chat_input("Type or use voice...")

if audio_bytes:
    current_audio_hash = hash(audio_bytes)
    if st.session_state.last_audio_md5 != current_audio_hash:
        st.session_state.last_audio_md5 = current_audio_hash
        
        with st.spinner("Transcribing audio..."):
            transcribed_text = transcribe_audio(audio_bytes)
            
        if transcribed_text:
            user_input = transcribed_text

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Assistant is typing..."):
        reply = get_llm_response(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# Trim history (Keep system prompt + last 8 entries)
if len(st.session_state.messages) > 9:
    st.session_state.messages = [st.session_state.messages[0]] + st.session_state.messages[-8:]
