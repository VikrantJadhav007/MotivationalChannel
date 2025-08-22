import streamlit as st

# Initialize session state variables for chat messages and username
if "messages" not in st.session_state:
    st.session_state.messages = []
if "username" not in st.session_state:
    st.session_state.username = None

st.set_page_config(page_title="Motivational Speaker Channel", layout="wide")

st.title("Motivational Speaker Communication Channel")

# User login flow
if st.session_state.username is None:
    username = st.text_input("Enter your name to join the session", key="login_input")
    if st.button("Join"):
        if username and username.strip() != "":
            st.session_state.username = username.strip()
            st.rerun()
        else:
            st.warning("Please enter a valid name to join.")
else:
    # Display logout and username info in sidebar
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.username = None
        st.session_state.messages = []
        st.rerun()

    # Layout: Split screen with video chat on the left and text chat on the right
    left_col, right_col = st.columns([3, 2])

    # Left: Video & Audio communication using embedded Jitsi Meet
    with left_col:
        st.header("Video & Audio Chat")
        room_name = "motivational_speaker_room"
        jitsi_url = f"https://meet.jit.si/{room_name}"
        st.markdown(
            f"""
            <iframe 
                src="{jitsi_url}" 
                allow="camera; microphone; fullscreen; display-capture" 
                style="width: 100%; height: 600px; border: 0; border-radius: 10px;"
                allowfullscreen>
            </iframe>
            """,
            unsafe_allow_html=True,
        )

    # Right: Text chat for motivational requests and answers
    with right_col:
        st.header("Text Communication")

        # Display chat messages
        chat_container = st.container()
        with chat_container:
            for user, msg in st.session_state.messages:
                st.markdown(f"**{user}:** {msg}")

        # Input for new message
        def send_message():
            message = st.session_state.new_message.strip()
            if message:
                # Save new message with username
                st.session_state.messages.append((st.session_state.username, message))
                st.session_state.new_message = ""  # Clear input

        st.text_input(
            "Send a motivational request or message",
            key="new_message",
            on_change=send_message,
            placeholder="Type your message here...",
        )
