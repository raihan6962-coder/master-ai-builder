import streamlit as st
from groq import Groq
import base64
import os
import json
import uuid
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION & UI SETUP
# ==========================================
st.set_page_config(page_title="Master AI Pro", page_icon="🧠", layout="wide")

# Custom CSS for better UI (Claude-like)
st.markdown("""
<style>
    .stChatFloatingInputContainer { padding-bottom: 20px; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FILE STORAGE SYSTEM (For Chat History)
# ==========================================
CHAT_DIR = "chat_history"
if not os.path.exists(CHAT_DIR):
    os.makedirs(CHAT_DIR)

def get_all_chats():
    chats = []
    for filename in os.listdir(CHAT_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(CHAT_DIR, filename), "r") as f:
                data = json.load(f)
                chats.append({
                    "id": data["id"],
                    "title": data["title"],
                    "updated_at": data.get("updated_at", "")
                })
    # Sort by newest first
    return sorted(chats, key=lambda x: x["updated_at"], reverse=True)

def load_chat(chat_id):
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)["messages"]
    return []

def save_chat(chat_id, title, messages):
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    data = {
        "id": chat_id,
        "title": title,
        "updated_at": datetime.now().isoformat(),
        "messages": messages
    }
    with open(filepath, "w") as f:
        json.dump(data, f)

# ==========================================
# 3. SESSION STATE INITIALIZATION
# ==========================================
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.chat_title = "New Chat"

if "messages" not in st.session_state:
    st.session_state.messages = load_chat(st.session_state.current_chat_id)

# System Prompt (The Brain)
SYSTEM_PROMPT = {
    "role": "system", 
    "content": """You are an Elite AI Architect and Senior Python Developer. 
    Your goal is to help the user build highly complex, production-ready AI agents (Lead Gen, Scraping, Automation).
    Rules:
    1. Never break code. Provide complete, copy-pasteable Python scripts.
    2. Use proper markdown for code blocks so the user can copy them easily.
    3. Be proactive: If the user asks for a scraper, also suggest how to bypass anti-bot systems.
    4. Remember previous context in this conversation.
    5. Explain deployment steps (Render, GitHub, etc.) clearly."""
}

# ==========================================
# 4. SIDEBAR (History, Settings, Vision)
# ==========================================
with st.sidebar:
    st.title("🧠 Master AI Pro")
    
    # --- NEW CHAT BUTTON ---
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.session_state.chat_title = "New Chat"
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # --- CHAT HISTORY (TABS) ---
    st.subheader("📚 Chat History")
    all_chats = get_all_chats()
    for chat in all_chats:
        # Highlight current chat
        btn_label = f"💬 {chat['title']}"
        if chat['id'] == st.session_state.current_chat_id:
            btn_label = f"👉 {chat['title']}"
            
        if st.button(btn_label, key=chat['id'], use_container_width=True):
            st.session_state.current_chat_id = chat['id']
            st.session_state.chat_title = chat['title']
            st.session_state.messages = load_chat(chat['id'])
            st.rerun()

    st.markdown("---")
    
    # --- VISION / IMAGE UPLOAD ---
    st.subheader("📎 Attach Image")
    uploaded_image = st.file_uploader("Upload UI/Error screenshot", type=["jpg", "jpeg", "png"])
    
    st.markdown("---")
    
    # --- SETTINGS & API KEY MANAGER ---
    with st.expander("⚙️ Settings & API Key"):
        # Get API key from session, then env var
        current_key = st.session_state.get("USER_API_KEY", os.environ.get("GROQ_API_KEY", ""))
        
        new_key = st.text_input("Groq API Key", value=current_key, type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Key"):
                st.session_state.USER_API_KEY = new_key
                st.success("Saved!")
        with col2:
            if st.button("🗑️ Delete"):
                st.session_state.USER_API_KEY = ""
                st.rerun()

# ==========================================
# 5. MAIN CHAT INTERFACE
# ==========================================
st.header(f"{st.session_state.chat_title}")

# API Key Validation
active_api_key = st.session_state.get("USER_API_KEY", os.environ.get("GROQ_API_KEY", ""))
if not active_api_key:
    st.warning("⚠️ Please add your Groq API Key in the Settings (Sidebar) to start chatting.")
    st.stop()

client = Groq(api_key=active_api_key)

# Display Chat History
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            if "image_data" in message:
                # Decode base64 to display image in history
                image_bytes = base64.b64decode(message["image_data"])
                st.image(image_bytes, width=300)
            st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Type your complex project idea here..."):
    
    # Auto-generate title for new chats
    if len(st.session_state.messages) == 0:
        st.session_state.chat_title = prompt[:30] + "..."
    
    # Display User Message
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_image:
            st.image(uploaded_image, width=300)

    # Prepare Message Data
    user_msg_data = {"role": "user", "content": prompt}
    
    if uploaded_image:
        base64_image = base64.b64encode(uploaded_image.getvalue()).decode('utf-8')
        user_msg_data["content"] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
        user_msg_data["image_data"] = base64_image # Save for UI history
        model_name = "llama-3.2-11b-vision-preview"
    else:
        model_name = "llama-3.3-70b-versatile" # The smartest coding model

    st.session_state.messages.append(user_msg_data)

    # Prepare API Messages (Inject System Prompt + History)
    api_messages = [SYSTEM_PROMPT]
    for msg in st.session_state.messages:
        # Strip UI-specific keys for the API
        api_msg = {"role": msg["role"], "content": msg["content"]}
        api_messages.append(api_msg)

    # Get AI Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=api_messages,
                temperature=0.7,
                max_tokens=6000, # Increased for complex code
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Save Assistant Response
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # Save entire chat to JSON file
            save_chat(st.session_state.current_chat_id, st.session_state.chat_title, st.session_state.messages)
            
        except Exception as e:
            st.error(f"API Error: {e}")
