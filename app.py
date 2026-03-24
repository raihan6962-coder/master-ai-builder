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
st.set_page_config(page_title="Master AI Pro Max", page_icon="🧠", layout="wide")

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
                try:
                    data = json.load(f)
                    chats.append({
                        "id": data["id"],
                        "title": data["title"],
                        "updated_at": data.get("updated_at", "")
                    })
                except: pass
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

def delete_chat_file(chat_id):
    filepath = os.path.join(CHAT_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)

# ==========================================
# 3. SESSION STATE & CALLBACKS
# ==========================================
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.chat_title = "New Chat"
    st.session_state.messages = []

if "editing_index" not in st.session_state:
    st.session_state.editing_index = None

if "pending_generation" not in st.session_state:
    st.session_state.pending_generation = False

def delete_msg(index):
    st.session_state.messages.pop(index)
    save_chat(st.session_state.current_chat_id, st.session_state.chat_title, st.session_state.messages)

def set_edit(index):
    st.session_state.editing_index = index

def submit_edit(index, new_text):
    st.session_state.messages[index]["content"] = new_text
    st.session_state.messages = st.session_state.messages[:index+1]
    st.session_state.editing_index = None
    st.session_state.pending_generation = True
    save_chat(st.session_state.current_chat_id, st.session_state.chat_title, st.session_state.messages)

def retry_last():
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
    st.session_state.pending_generation = True
    save_chat(st.session_state.current_chat_id, st.session_state.chat_title, st.session_state.messages)

SYSTEM_PROMPT = {
    "role": "system", 
    "content": "You are an Elite AI Architect and Senior Python Developer. Help the user build highly complex, production-ready AI agents. Never break code. Provide complete, copy-pasteable Python scripts."
}

# ==========================================
# 4. SIDEBAR (History, Settings, Vision)
# ==========================================
with st.sidebar:
    st.title("🧠 Master AI Pro Max")
    
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.session_state.chat_title = "New Chat"
        st.session_state.messages = []
        st.session_state.editing_index = None
        st.rerun()
    
    st.markdown("---")
    st.subheader("📚 Chat History")
    
    all_chats = get_all_chats()
    for chat in all_chats:
        col1, col2 = st.columns([8, 2])
        with col1:
            btn_label = f"💬 {chat['title'][:15]}..." if len(chat['title']) > 15 else f"💬 {chat['title']}"
            if chat['id'] == st.session_state.current_chat_id:
                btn_label = f"👉 {chat['title'][:15]}..."
            
            if st.button(btn_label, key=f"load_{chat['id']}", use_container_width=True):
                st.session_state.current_chat_id = chat['id']
                st.session_state.chat_title = chat['title']
                st.session_state.messages = load_chat(chat['id'])
                st.session_state.editing_index = None
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_chat_{chat['id']}", help="Delete Chat"):
                delete_chat_file(chat['id'])
                if chat['id'] == st.session_state.current_chat_id:
                    st.session_state.current_chat_id = str(uuid.uuid4())
                    st.session_state.chat_title = "New Chat"
                    st.session_state.messages = []
                st.rerun()

    st.markdown("---")
    st.subheader("📎 Attach Image")
    uploaded_image = st.file_uploader("Upload UI/Error screenshot", type=["jpg", "jpeg", "png"])
    
    st.markdown("---")
    with st.expander("⚙️ Settings & API Key"):
        current_key = st.session_state.get("USER_API_KEY", os.environ.get("GROQ_API_KEY", ""))
        new_key = st.text_input("Groq API Key", value=current_key, type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save"):
                st.session_state.USER_API_KEY = new_key
                st.success("Saved!")
        with col2:
            if st.button("🗑️ Clear"):
                st.session_state.USER_API_KEY = ""
                st.rerun()

# ==========================================
# 5. MAIN CHAT INTERFACE
# ==========================================
st.header(f"{st.session_state.chat_title}")

active_api_key = st.session_state.get("USER_API_KEY", os.environ.get("GROQ_API_KEY", ""))
if not active_api_key:
    st.warning("⚠️ Please add your Groq API Key in the Settings (Sidebar) to start chatting.")
    st.stop()

client = Groq(api_key=active_api_key)

for i, message in enumerate(st.session_state.messages):
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            if st.session_state.editing_index == i:
                new_text = st.text_area("Edit message:", value=message["content"], height=100)
                col1, col2 = st.columns([1, 10])
                with col1:
                    if st.button("💾 Save & Submit", key=f"save_{i}"):
                        submit_edit(i, new_text)
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key=f"cancel_{i}"):
                        st.session_state.editing_index = None
                        st.rerun()
            else:
                if "image_data" in message:
                    image_bytes = base64.b64decode(message["image_data"])
                    st.image(image_bytes, width=300)
                
                # Handle display of complex content (like image + text)
                if isinstance(message["content"], list):
                    for item in message["content"]:
                        if item["type"] == "text":
                            st.markdown(item["text"])
                else:
                    st.markdown(message["content"])
                
                cols = st.columns([1, 1, 1, 15])
                if message["role"] == "user":
                    if cols[0].button("✏️", key=f"edit_{i}", help="Edit Message"):
                        set_edit(i)
                        st.rerun()
                
                if cols[1].button("🗑️", key=f"del_msg_{i}", help="Delete Message"):
                    delete_msg(i)
                    st.rerun()
                    
                if message["role"] == "assistant" and i == len(st.session_state.messages) - 1:
                    if cols[2].button("🔄", key=f"retry_{i}", help="Regenerate Response"):
                        retry_last()
                        st.rerun()

# ==========================================
# 6. CHAT INPUT & GENERATION LOGIC
# ==========================================
if prompt := st.chat_input("Type your complex project idea here..."):
    if len(st.session_state.messages) == 0:
        st.session_state.chat_title = prompt[:30] + "..."
    
    user_msg_data = {"role": "user", "content": prompt}
    
    if uploaded_image:
        base64_image = base64.b64encode(uploaded_image.getvalue()).decode('utf-8')
        user_msg_data["content"] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
        user_msg_data["image_data"] = base64_image
    
    st.session_state.messages.append(user_msg_data)
    save_chat(st.session_state.current_chat_id, st.session_state.chat_title, st.session_state.messages)
    st.session_state.pending_generation = True
    st.rerun()

if st.session_state.pending_generation:
    st.session_state.pending_generation = False 
    
    last_msg = st.session_state.messages[-1]
    model_name = "llama-3.3-70b-versatile"
    if "image_data" in last_msg:
        model_name = "llama-3.2-11b-vision-preview"

    api_messages = [SYSTEM_PROMPT]
    
    # --- SMART MEMORY (SLIDING WINDOW) ---
    # Keep only the last 10 messages to prevent Token Limit Error (413)
    recent_messages = st.session_state.messages[-10:] 
    
    for msg in recent_messages:
        content = msg["content"]
        
        # FIX: If current model is Text-Only, but history has Image format, extract only text
        if model_name == "llama-3.3-70b-versatile" and isinstance(content, list):
            text_only = ""
            for item in content:
                if item.get("type") == "text":
                    text_only = item.get("text", "")
            content = text_only
            
        api_messages.append({"role": msg["role"], "content": content})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=api_messages,
                temperature=0.7,
                max_tokens=2048, # Reduced to fit Free Tier limits
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_chat(st.session_state.current_chat_id, st.session_state.chat_title, st.session_state.messages)
            
        except Exception as e:
            st.error(f"API Error: {e}")
            if st.button("🔄 Try Again"):
                st.session_state.pending_generation = True
                st.rerun()
