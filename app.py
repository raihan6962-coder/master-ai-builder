import streamlit as st
from groq import Groq
import base64
from PIL import Image
import io
import os

# Page config
st.set_page_config(page_title="Master AI Builder", page_icon="🤖", layout="wide")

# Groq API Setup
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    st.error("⚠️ Groq API Key missing! Render er Environment Variables e GROQ_API_KEY add koro.")
    st.stop()

client = Groq(api_key=api_key)

# App Title
st.title("🤖 Master AI Builder (Lead Gen & Automation Expert)")
st.markdown("Ami tomar personal AI Developer. Amake bolo tumi ki banate chao! (Image o upload korte paro)")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system", 
            "content": "You are an expert Python developer and AI Architect. Your main goal is to help the user build successful AI projects, specifically AI agents for Lead Generation, Web Scraping, and Automated Email Sending. Write clean, production-ready Python code. Be smart, proactive, and explain how to deploy these agents."
        }
    ]

# Display chat history (hiding the system message)
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            if "image" in message:
                st.image(message["image"], width=300)
            st.markdown(message["content"])

# Image to Base64 converter function
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# Sidebar for Image Upload
with st.sidebar:
    st.header("📎 Attachments")
    uploaded_image = st.file_uploader("Upload an image (UI design, error screenshot, etc.)", type=["jpg", "jpeg", "png"])
    st.markdown("---")
    st.markdown("### 💡 Ideas to ask:")
    st.markdown("- 'Make a Python script to scrape emails from a website.'")
    st.markdown("- 'Create an AI agent that generates cold emails.'")
    st.markdown("- 'How to deploy my lead gen script on Render?'")

# Chat Input
if prompt := st.chat_input("Tomar ki code lagbe ba ki banate chao bolo..."):
    
    # Add user message to UI
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_image:
            st.image(uploaded_image, width=300)

    # Prepare message for Groq
    user_msg_data = {"role": "user", "content": prompt}
    
    if uploaded_image:
        # If image is uploaded, use Vision Model
        base64_image = encode_image(uploaded_image)
        user_msg_data["content"] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
        user_msg_data["image"] = uploaded_image # For UI display
        model_name = "llama-3.2-11b-vision-preview" # Groq Vision Model
    else:
        # If only text, use the best coding model
        model_name = "llama-3.3-70b-versatile" # Groq Text Model

    # Save to session state
    st.session_state.messages.append(user_msg_data)

    # Prepare API messages (removing UI specific keys like 'image')
    api_messages = []
    for msg in st.session_state.messages:
        api_msg = {"role": msg["role"], "content": msg["content"]}
        api_messages.append(api_msg)

    # Get Response from Groq
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=api_messages,
                temperature=0.7,
                max_tokens=4000,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # Save assistant response
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error: {e}")
